"""Tests for the commit message editor (cola.widgets.commitmsg)."""
import sys
from unittest.mock import MagicMock

import pytest

from cola import core
from cola import git
from cola import gitcfg
from cola import gitcmds
from cola import hotkeys
from cola.models import main as main_model
from cola.widgets.commitmsg import CommitMessageEditor
from qtpy import QtGui
from qtpy import QtWidgets

from . import helper


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for the widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


@pytest.fixture
def commit_editor(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    helper.initialize_repo()

    context = MagicMock()
    context.git = git.create()
    context.git.set_worktree(core.getcwd())
    context.cfg = gitcfg.create(context)
    context.model = main_model.create(context)
    context.cfg.reset()
    gitcmds.reset()

    editor = CommitMessageEditor(context, None)
    try:
        yield editor
    finally:
        editor.close()


def test_commit_button_tooltip_uses_the_native_shortcut(commit_editor):
    """The tooltip shows the platform shortcut, not a hardcoded 'Ctrl+Enter'.

    Qt maps Ctrl to Command on macOS, so the literal string was wrong there
    and, being translated, wrong in every locale.
    """
    tooltip = commit_editor.commit_button.toolTip()
    native = hotkeys.APPLY.toString(QtGui.QKeySequence.NativeText)

    assert 'Commit staged changes' in tooltip
    assert native in tooltip
    assert 'Ctrl+Enter' not in tooltip
