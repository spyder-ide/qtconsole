"""Test QtConsoleApp"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import sys
from subprocess import check_output
from unittest.mock import Mock

from jupyter_core import paths
import pytest
from traitlets.tests.utils import check_help_all_output

from . import no_display


def test_new_frontend_master_uses_configured_kernel_name():
    """New independent kernels use the application's configured kernel."""
    from qtconsole.qtconsoleapp import JupyterQtConsoleApp

    app = JupyterQtConsoleApp()
    app.kernel_name = "configured-kernel"
    app.kernel_manager = None
    app._new_connection_file = Mock(return_value="connection.json")

    manager = Mock()
    manager.ipykernel = False
    app.kernel_manager_class = Mock(return_value=manager)
    widget = Mock()
    app.widget_factory = Mock(return_value=widget)
    app.init_colors = Mock()

    app.new_frontend_master()

    app.kernel_manager_class.assert_called_once_with(
        connection_file="connection.json",
        kernel_name="configured-kernel",
        parent=app,
        autorestart=True,
    )


@pytest.mark.skipif(no_display, reason="Doesn't work without a display")
def test_help_output():
    """jupyter qtconsole --help-all works"""
    check_help_all_output('qtconsole')


@pytest.mark.skipif(no_display, reason="Doesn't work without a display")
@pytest.mark.skipif(os.environ.get('CI', None) is None,
                    reason="Doesn't work outside of our CIs")
def test_generate_config():
    """jupyter qtconsole --generate-config"""
    config_dir = paths.jupyter_config_dir()
    check_output([sys.executable, '-m', 'qtconsole', '--generate-config'])
    assert os.path.isfile(os.path.join(config_dir,
                                       'jupyter_qtconsole_config.py'))
