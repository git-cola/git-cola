import sys
from unittest.mock import Mock

import pytest
from qtpy import QtWidgets

from cola.models import prefs
from cola.widgets import prefs as prefs_widgets
from . import helper
from .helper import app_context


def _qapp():
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(sys.argv[:1] if sys.argv else ['git-cola-test'])
    return instance


@pytest.fixture(scope='module')
def qapp():
    yield _qapp()


def test_editor_pref_uses_cola_editor_over_gui_editor(app_context):
    helper.run_git('config', 'cola.editor', 'colaedit')
    helper.run_git('config', 'gui.editor', 'guiedit')
    app_context.cfg.reset()

    assert prefs.editor(app_context) == 'colaedit'


def test_editor_pref_falls_back_to_gui_editor(app_context):
    helper.run_git('config', 'gui.editor', 'guiedit2')
    app_context.cfg.reset()

    assert prefs.editor(app_context) == 'guiedit2'


def test_difftool_pref_uses_cola_difftool_over_diff_tool(app_context):
    helper.run_git('config', 'cola.difftool', 'cola-diff')
    helper.run_git('config', 'diff.tool', 'git-diff')
    app_context.cfg.reset()

    assert prefs.difftool(app_context) == 'cola-diff'


def test_difftool_pref_falls_back_to_diff_tool(app_context):
    helper.run_git('config', 'diff.tool', 'git-diff-2')
    app_context.cfg.reset()

    assert prefs.difftool(app_context) == 'git-diff-2'


def test_mergetool_pref_uses_cola_mergetool_over_merge_tool(app_context):
    helper.run_git('config', 'cola.mergetool', 'cola-merge')
    helper.run_git('config', 'merge.tool', 'git-merge')
    app_context.cfg.reset()

    assert prefs.mergetool(app_context) == 'cola-merge'


def test_mergetool_pref_falls_back_to_merge_tool(app_context):
    helper.run_git('config', 'merge.tool', 'git-merge-2')
    app_context.cfg.reset()

    assert prefs.mergetool(app_context) == 'git-merge-2'


def test_history_browser_pref_uses_cola_historybrowser_over_gui_historybrowser(app_context):
    helper.run_git('config', 'cola.historybrowser', 'cola-hist')
    helper.run_git('config', 'gui.historybrowser', 'gitk-hist')
    app_context.cfg.reset()

    assert prefs.history_browser(app_context) == 'cola-hist'


def test_history_browser_pref_falls_back_to_gui_historybrowser(app_context):
    helper.run_git('config', 'gui.historybrowser', 'gitk-hist-2')
    app_context.cfg.reset()

    assert prefs.history_browser(app_context) == 'gitk-hist-2'


def test_settings_form_widget_uses_cola_config_keys(qapp, app_context):
    widget = prefs_widgets.SettingsFormWidget(app_context, Mock(), None)

    assert prefs.COLA_EDITOR in widget.widget_to_config
    assert prefs.COLA_HISTORY_BROWSER in widget.widget_to_config
    assert prefs.COLA_DIFFTOOL in widget.widget_to_config
    assert prefs.COLA_MERGETOOL in widget.widget_to_config

    assert prefs.EDITOR not in widget.widget_to_config
    assert prefs.HISTORY_BROWSER not in widget.widget_to_config
    assert prefs.DIFFTOOL not in widget.widget_to_config
    assert prefs.MERGETOOL not in widget.widget_to_config
