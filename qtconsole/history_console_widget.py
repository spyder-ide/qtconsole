# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import os
import os.path

from qtpy import QtCore, QtGui, QtWidgets

from traitlets import Bool
from .console_widget import ConsoleWidget
from .completion_widget import CompletionWidget


class HistoryListWidget(CompletionWidget):
    """ A widget for GUI list history.
    """
    complete_current = QtCore.Signal(str)

    def _complete_current(self):
        """ Perform the completion with the currently selected item.
        """
        text = self.currentItem().data(QtCore.Qt.UserRole)
        self.complete_current.emit(text)
        self.hide()


class HistoryConsoleWidget(ConsoleWidget):
    """ A ConsoleWidget that keeps a history of the commands that have been
        executed and provides a readline-esque interface to this history.
    """

    #------ Configuration ------------------------------------------------------

    # If enabled, the input buffer will become "locked" to history movement when
    # an edit is made to a multi-line input buffer. To override the lock, use
    # Shift in conjunction with the standard history cycling keys.
    history_lock = Bool(False, config=True)

    #---------------------------------------------------------------------------
    # 'object' interface
    #---------------------------------------------------------------------------

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        # HistoryConsoleWidget protected variables.
        self._history = []
        self._history_edits = {}
        self._history_index = 0
        self._history_prefix = ''
        self.droplist_history = QtWidgets.QAction("Show related history execution entries",
                self,
                shortcut="Ctrl+Shift+R",
                shortcutContext=QtCore.Qt.WidgetWithChildrenShortcut,
                triggered=self._show_history_droplist
        )
        self.addAction(self.droplist_history)
        self._history_list_widget = HistoryListWidget(self, self.gui_completion_height)
        self._history_list_widget.complete_current.connect(self.change_input_buffer)

    #---------------------------------------------------------------------------
    # 'ConsoleWidget' public interface
    #---------------------------------------------------------------------------
    def do_execute(self, source, complete, indent):
        """ Reimplemented to the store history. """
        history = self.input_buffer if source is None else source

        super().do_execute(source, complete, indent)

        if complete:
            # Save the command unless it was an empty string or was identical
            # to the previous command.
            history = history.rstrip()
            if history and (not self._history or self._history[-1] != history):
                self._history.append(history)

            # Emulate readline: reset all history edits.
            self._history_edits = {}

            # Move the history index to the most recent item.
            self._history_index = len(self._history)

    #---------------------------------------------------------------------------
    # 'ConsoleWidget' abstract interface
    #---------------------------------------------------------------------------

    def _up_pressed(self, shift_modifier):
        """ Called when the up key is pressed. Returns whether to continue
            processing the event.
        """
        prompt_cursor = self._get_prompt_cursor()
        if self._get_cursor().blockNumber() == prompt_cursor.blockNumber():
            # Bail out if we're locked.
            if self._history_locked() and not shift_modifier:
                return False

            # Set a search prefix based on the cursor position.
            pos = self._get_input_buffer_cursor_pos()
            input_buffer = self.input_buffer
            # use the *shortest* of the cursor column and the history prefix
            # to determine if the prefix has changed
            n = min(pos, len(self._history_prefix))

            # prefix changed, restart search from the beginning
            if (self._history_prefix[:n] != input_buffer[:n]):
                self._history_index = len(self._history)

            # the only time we shouldn't set the history prefix
            # to the line up to the cursor is if we are already
            # in a simple scroll (no prefix),
            # and the cursor is at the end of the first line

            # check if we are at the end of the first line
            c = self._get_cursor()
            current_pos = c.position()
            c.movePosition(QtGui.QTextCursor.EndOfBlock)
            at_eol = (c.position() == current_pos)

            if self._history_index == len(self._history) or \
                not (self._history_prefix == '' and at_eol) or \
                not (self._get_edited_history(self._history_index)[:pos] == input_buffer[:pos]):
                self._history_prefix = input_buffer[:pos]

            # Perform the search.
            self.history_previous(self._history_prefix,
                                    as_prefix=not shift_modifier)

            # Go to the first line of the prompt for seemless history scrolling.
            # Emulate readline: keep the cursor position fixed for a prefix
            # search.
            cursor = self._get_prompt_cursor()
            if self._history_prefix:
                cursor.movePosition(QtGui.QTextCursor.Right,
                                    n=len(self._history_prefix))
            else:
                cursor.movePosition(QtGui.QTextCursor.EndOfBlock)
            self._set_cursor(cursor)

            return False

        return True

    def _down_pressed(self, shift_modifier):
        """ Called when the down key is pressed. Returns whether to continue
            processing the event.
        """
        end_cursor = self._get_end_cursor()
        if self._get_cursor().blockNumber() == end_cursor.blockNumber():
            # Bail out if we're locked.
            if self._history_locked() and not shift_modifier:
                return False

            # Perform the search.
            replaced = self.history_next(self._history_prefix,
                                            as_prefix=not shift_modifier)

            # Emulate readline: keep the cursor position fixed for a prefix
            # search. (We don't need to move the cursor to the end of the buffer
            # in the other case because this happens automatically when the
            # input buffer is set.)
            if self._history_prefix and replaced:
                cursor = self._get_prompt_cursor()
                cursor.movePosition(QtGui.QTextCursor.Right,
                                    n=len(self._history_prefix))
                self._set_cursor(cursor)

            return False

        return True

    def _show_history_droplist(self):
        # Perform the search.
        prompt_cursor = self._get_prompt_cursor()
        if self._get_cursor().blockNumber() == prompt_cursor.blockNumber():

            # Set a search prefix based on the cursor position.
            pos = self._get_input_buffer_cursor_pos()
            input_buffer = self.input_buffer
            # use the *shortest* of the cursor column and the history prefix
            # to determine if the prefix has changed
            n = min(pos, len(self._history_prefix))

            # prefix changed, restart search from the beginning
            if self._history_prefix[:n] != input_buffer[:n]:
                self._history_index = len(self._history)

            # the only time we shouldn't set the history prefix
            # to the line up to the cursor is if we are already
            # in a simple scroll (no prefix),
            # and the cursor is at the end of the first line

            # check if we are at the end of the first line
            c = self._get_cursor()
            current_pos = c.position()
            c.movePosition(QtGui.QTextCursor.EndOfBlock)
            at_eol = c.position() == current_pos

            if (
                self._history_index == len(self._history)
                or not (self._history_prefix == "" and at_eol)
                or not (
                    self._get_edited_history(self._history_index)[:pos]
                    == input_buffer[:pos]
                )
            ):
                self._history_prefix = input_buffer[:pos]
        items = self._history
        items.reverse()
        if self._history_prefix:
            items = [
                item
                for item in items
                if item.startswith(self._history_prefix)
            ]

        cursor = self._get_cursor()
        pos = len(self._history_prefix)
        cursor_pos = self._get_input_buffer_cursor_pos()
        cursor.movePosition(QtGui.QTextCursor.Left, n=(cursor_pos - pos))
        # This line actually applies the move to control's cursor
        self._control.setTextCursor(cursor)

        self._history_list_widget.cancel_completion()
        if len(items) == 1:
            self._history_list_widget.show_items(
                cursor, items
            )
        elif len(items) > 1:
            current_pos = self._control.textCursor().position()
            prefix = os.path.commonprefix(items)
            self._history_list_widget.show_items(
                cursor, items, prefix_length=len(prefix)
            )

    #---------------------------------------------------------------------------
    # 'HistoryConsoleWidget' public interface
    #---------------------------------------------------------------------------

    def history_previous(self, substring='', as_prefix=True):
        """ If possible, set the input buffer to a previous history item.

        Parameters
        ----------
        substring : str, optional
            If specified, search for an item with this substring.
        as_prefix : bool, optional
            If True, the substring must match at the beginning (default).

        Returns
        -------
        Whether the input buffer was changed.
        """
        index = self._history_index
        replace = False
        while index > 0:
            index -= 1
            history = self._get_edited_history(index)
            if history == self.input_buffer:
                continue
            if (as_prefix and history.startswith(substring)) \
                or (not as_prefix and substring in history):
                replace = True
                break

        if replace:
            self.change_input_buffer(history, index=index)

        return replace

    def history_next(self, substring='', as_prefix=True):
        """ If possible, set the input buffer to a subsequent history item.

        Parameters
        ----------
        substring : str, optional
            If specified, search for an item with this substring.
        as_prefix : bool, optional
            If True, the substring must match at the beginning (default).

        Returns
        -------
        Whether the input buffer was changed.
        """
        index = self._history_index
        replace = False
        while index < len(self._history):
            index += 1
            history = self._get_edited_history(index)
            if history == self.input_buffer:
                continue
            if (as_prefix and history.startswith(substring)) \
                or (not as_prefix and substring in history):
                replace = True
                break

        if replace:
            self.change_input_buffer(history, index=index)

        return replace

    def history_tail(self, n=10):
        """ Get the local history list.

        Parameters
        ----------
        n : int
            The (maximum) number of history items to get.
        """
        return self._history[-n:]

    @QtCore.Slot(str)
    def change_input_buffer(self, buffer, index=None):
        """Change input_buffer value while storing edits and updating history index.

        Parameters
        ----------
        buffer : str
            New value for the inpur buffer.
        index : int, optional
            History index to set. The default is 0.
        """
        if index:
            self._store_edits()
            self._history_index = index
        self.input_buffer = buffer

    #---------------------------------------------------------------------------
    # 'HistoryConsoleWidget' protected interface
    #---------------------------------------------------------------------------

    def _history_locked(self):
        """ Returns whether history movement is locked.
        """
        return (self.history_lock and
                (self._get_edited_history(self._history_index) !=
                 self.input_buffer) and
                (self._get_prompt_cursor().blockNumber() !=
                 self._get_end_cursor().blockNumber()))

    def _get_edited_history(self, index):
        """ Retrieves a history item, possibly with temporary edits.
        """
        if index in self._history_edits:
            return self._history_edits[index]
        elif index == len(self._history):
            return str()
        return self._history[index]

    def _set_history(self, history):
        """ Replace the current history with a sequence of history items.
        """
        self._history = list(history)
        self._history_edits = {}
        self._history_index = len(self._history)

    def _store_edits(self):
        """ If there are edits to the current input buffer, store them.
        """
        current = self.input_buffer
        if self._history_index == len(self._history) or \
                self._history[self._history_index] != current:
            self._history_edits[self._history_index] = current
