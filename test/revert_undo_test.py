"""Tests for the undoable revert commands"""
import os
import sys
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from qtpy import QtWidgets

from cola import cmd
from cola import cmds
from cola import core
from cola import diffparse
from cola import gitcmds
from cola.models import selection

from . import helper
from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for pumping queued command-bus signals"""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


@pytest.fixture
def context(qapp, app_context):
    """Provide a context with a real command bus and selection model"""
    context = app_context
    context.command_bus = cmd.CommandBus()
    context.selection = selection.create()
    helper.write_file('A', 'one\ntwo\nthree\n')
    helper.write_file('B', 'bee\n')
    helper.run_git('add', 'A', 'B')
    helper.run_git('commit', '-m', 'initial commit')
    gitcmds.reset()
    return context


def read_file(path):
    with open(path, 'rb') as f:
        return f.read()


def enable_revert_mode(context):
    """Place the model into a mode that allows reverts"""
    model = context.model
    model.mode = model.mode_worktree
    return model


def bus_undo(bus):
    """Undo through the command bus and pump the queued signal"""
    result = bus.undo()
    QtWidgets.QApplication.instance().processEvents()
    return result


def bus_redo(bus):
    """Redo through the command bus and pump the queued signal"""
    result = bus.redo()
    QtWidgets.QApplication.instance().processEvents()
    return result


def test_command_graph_discard_root():
    """A discarded root command leaves an empty undo history"""
    graph = cmd.CommandGraph()
    first = Mock()
    first.is_undoable.return_value = True

    graph.add(first)
    assert graph.get_current_command() is first

    graph.discard(first)
    assert graph.root is None
    assert graph.cursor is None
    assert graph.get_current_command() is None
    assert not graph.step_backward()


def test_command_graph_discard_nested():
    """Discarding the newest command keeps the older commands undoable"""
    graph = cmd.CommandGraph()
    first = Mock()
    first.is_undoable.return_value = True
    second = Mock()
    second.is_undoable.return_value = True

    graph.add(first)
    graph.add(second)
    assert graph.get_current_command() is second

    graph.discard(second)
    assert graph.get_current_command() is first
    assert graph.step_backward() is first
    assert graph.cursor is None


def test_revert_unstaged_edits_undo_and_redo(context):
    """Reverting unstaged edits is undoable and redoable"""
    model = enable_revert_mode(context)
    helper.write_file('A', 'one\nCHANGED\nthree\n')
    model.update_file_status()
    context.selection.modified = ['A']

    with patch('cola.interaction.Interaction.confirm', return_value=True):
        assert cmds.do(cmds.RevertUnstagedEdits, context)
    assert read_file('A') == b'one\ntwo\nthree\n'

    bus = context.command_bus
    assert bus.can_undo()
    assert bus.get_undo_command_name() == cmds.RevertUnstagedEdits.name()

    assert bus_undo(bus)
    assert read_file('A') == b'one\nCHANGED\nthree\n'

    assert bus_redo(bus)
    assert read_file('A') == b'one\ntwo\nthree\n'


def test_revert_uncommitted_edits_undo_and_redo(context):
    """Reverting uncommitted edits restores both the index and worktree"""
    model = enable_revert_mode(context)
    helper.write_file('A', 'one\nCHANGED\nthree\n')
    helper.run_git('add', 'A')
    helper.write_file('A', 'one\nCHANGED\nEXTRA\nthree\n')
    model.update_file_status()
    context.selection.staged = ['A']

    with patch('cola.interaction.Interaction.confirm', return_value=True):
        assert cmds.do(cmds.RevertUncommittedEdits, context)
    assert read_file('A') == b'one\ntwo\nthree\n'
    assert not helper.run_git('diff', '--cached', '--name-only').strip()

    bus = context.command_bus
    assert bus_undo(bus)

    # The staged edits and the unstaged edits are both restored.
    assert read_file('A') == b'one\nCHANGED\nEXTRA\nthree\n'
    staged = helper.run_git('diff', '--cached', '--', 'A')
    assert '+CHANGED' in staged
    assert '+EXTRA' not in staged
    unstaged = helper.run_git('diff', '--', 'A')
    assert '+EXTRA' in unstaged

    assert bus_redo(bus)
    assert read_file('A') == b'one\ntwo\nthree\n'
    assert not helper.run_git('diff', '--cached', '--name-only').strip()


def test_revert_unstaged_deletion_undo(context):
    """Undoing a revert of a deleted file deletes the file again"""
    model = enable_revert_mode(context)
    os.unlink('A')
    model.update_file_status()
    context.selection.modified = ['A']

    with patch('cola.interaction.Interaction.confirm', return_value=True):
        assert cmds.do(cmds.RevertUnstagedEdits, context)
    assert read_file('A') == b'one\ntwo\nthree\n'

    assert bus_undo(context.command_bus)
    assert not os.path.exists('A')

    assert bus_redo(context.command_bus)
    assert read_file('A') == b'one\ntwo\nthree\n'


def test_revert_canceled_is_not_undoable(context):
    """A canceled revert does not linger in the undo history"""
    model = enable_revert_mode(context)
    helper.write_file('A', 'one\nCHANGED\nthree\n')
    model.update_file_status()
    context.selection.modified = ['A']

    with patch('cola.interaction.Interaction.confirm', return_value=False):
        cmds.do(cmds.RevertUnstagedEdits, context)

    assert read_file('A') == b'one\nCHANGED\nthree\n'
    assert not context.command_bus.can_undo()


def test_revert_undo_falls_back_to_blobs(context):
    """Undo falls back to the saved blobs when the patch no longer applies"""
    model = enable_revert_mode(context)
    helper.write_file('A', 'one\nCHANGED\nthree\n')
    model.update_file_status()
    context.selection.modified = ['A']

    with patch('cola.interaction.Interaction.confirm', return_value=True):
        assert cmds.do(cmds.RevertUnstagedEdits, context)
    assert read_file('A') == b'one\ntwo\nthree\n'

    # Simulate an external edit that invalidates the saved patch.
    helper.write_file('A', 'edited by another process\n')

    # The first prompt asks about restoring the snapshot: answer yes.
    with patch('cola.interaction.Interaction.confirm', return_value=True):
        assert bus_undo(context.command_bus)
    assert read_file('A') == b'one\nCHANGED\nthree\n'


def test_revert_undo_skips_and_keeps_entry(context):
    """Skipping a failed patch undo leaves the files untouched"""
    model = enable_revert_mode(context)
    helper.write_file('A', 'one\nCHANGED\nthree\n')
    model.update_file_status()
    context.selection.modified = ['A']

    with patch('cola.interaction.Interaction.confirm', return_value=True):
        assert cmds.do(cmds.RevertUnstagedEdits, context)

    # Simulate an external edit that invalidates the saved patch.
    helper.write_file('A', 'edited by another process\n')

    # Answer "no" to restoring the snapshot and "no" to retrying.
    bus = context.command_bus
    cmd_instance = bus.cmd_graph.get_current_command()
    with patch('cola.interaction.Interaction.confirm', side_effect=[False, False]):
        assert not cmd_instance.undo()
    assert read_file('A') == b'edited by another process\n'

    # The undo entry is kept so that the revert can be undone later.
    assert bus.can_undo()


def test_apply_patch_worktree_undo_and_redo(context):
    """Line-based worktree reverts are undoable and redoable"""
    enable_revert_mode(context)
    helper.write_file('A', 'one\nCHANGED\nthree\n')

    diff_text = helper.run_git('diff', '--', 'A')
    parsed = diffparse.Patch.parse('A', diff_text)
    assert parsed.has_changes()
    # The diff editor applies the extracted hunk in reverse to revert lines.
    patch = parsed.extract_hunk(4, reverse=True)
    assert patch.has_changes()

    bus = context.command_bus
    cmd_instance = cmds.ApplyPatch(context, patch, 'utf-8', True)
    bus.do(cmd_instance, queued=False)
    assert read_file('A') == b'one\ntwo\nthree\n'

    assert bus_undo(bus)
    assert read_file('A') == b'one\nCHANGED\nthree\n'

    assert bus_redo(bus)
    assert read_file('A') == b'one\ntwo\nthree\n'


def test_apply_patch_index_undo(context):
    """Line-based staging is undoable without touching the worktree"""
    enable_revert_mode(context)
    helper.write_file('A', 'one\nCHANGED\nthree\n')

    diff_text = helper.run_git('diff', '--', 'A')
    patch = diffparse.Patch.parse('A', diff_text)
    assert patch.has_changes()

    bus = context.command_bus
    cmd_instance = cmds.ApplyPatch(context, patch, 'utf-8', False)
    bus.do(cmd_instance, queued=False)
    assert '+CHANGED' in helper.run_git('diff', '--cached', '--', 'A')
    assert read_file('A') == b'one\nCHANGED\nthree\n'

    assert bus_undo(bus)
    assert not helper.run_git('diff', '--cached', '--name-only').strip()
    assert read_file('A') == b'one\nCHANGED\nthree\n'

    assert bus_redo(bus)
    assert '+CHANGED' in helper.run_git('diff', '--cached', '--', 'A')


def test_apply_patch_failure_is_not_undoable(context):
    """A failed patch application leaves no undo entry behind"""
    enable_revert_mode(context)

    # A patch whose pre-image does not match the worktree cannot apply.
    patch_text = '--- a/A\n' '+++ b/A\n' '@@ -1,3 +1,3 @@\n' ' one\n' '-does-not-match\n' '+changed\n' ' three\n'
    bad_patch = diffparse.Patch.parse('A', patch_text)

    bus = context.command_bus
    cmd_instance = cmds.ApplyPatch(context, bad_patch, 'utf-8', True)
    with patch('cola.interaction.Interaction.confirm', return_value=False):
        bus.do(cmd_instance, queued=False)

    assert not bus.can_undo()


def test_undo_without_completed_revert_is_a_noop(context):
    """Undoing a revert that never ran does nothing"""
    model = enable_revert_mode(context)
    helper.write_file('A', 'one\nCHANGED\nthree\n')
    model.update_file_status()
    context.selection.modified = ['A']

    with patch('cola.interaction.Interaction.confirm', return_value=False):
        cmd_instance = cmds.RevertUnstagedEdits(context)
        assert not cmd_instance.undo()
    assert read_file('A') == b'one\nCHANGED\nthree\n'


def test_capture_worktree_blobs_missing_file(context):
    """Missing files are recorded with a None blob id"""
    blobs = cmds.capture_worktree_blobs(context, ['does-not-exist'])
    assert blobs == [('does-not-exist', None)]

    blobs = cmds.capture_worktree_blobs(context, ['A'])
    assert len(blobs) == 1
    path, oid = blobs[0]
    assert path == 'A'
    assert oid
    assert core.decode(oid) == helper.run_git('hash-object', 'A').strip()
