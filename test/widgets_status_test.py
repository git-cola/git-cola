"""Tests for selection save/restore in cola.widgets.status.StatusTreeWidget.

The model delivers its about_to_update/updated signals with Qt.QueuedConnection,
so by the time the widget's _save_selection() slot runs the model has already
replaced its file lists. These tests reproduce that ordering deterministically
(without git, background tasks or the command machinery) to pin the behaviour of
_save_selection()/_restore_selection().
"""
import sys
from unittest.mock import MagicMock

import pytest

from cola.models import selection
from cola.widgets import status
from qtpy import QtWidgets


@pytest.fixture(scope='module')
def qapp():
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(sys.argv[:1] if sys.argv else ['test'])
    yield instance


class _FakeModel:
    """The handful of MainModel attributes the status tree reads."""

    def __init__(self):
        self.staged = []
        self.unmerged = []
        self.modified = []
        self.untracked = []
        self.staged_deleted = set()
        self.unstaged_deleted = set()

    def set_contents(self, staged=(), unmerged=(), modified=(), untracked=()):
        self.staged = list(staged)
        self.unmerged = list(unmerged)
        self.modified = list(modified)
        self.untracked = list(untracked)


@pytest.fixture
def widget(qapp):
    tree = status.StatusTreeWidget(MagicMock(), None)
    tree._model = _FakeModel()
    return tree


def _untracked_child_paths(widget):
    parent = widget.topLevelItem(status.UNTRACKED_IDX)
    return [parent.child(i).text(0) for i in range(parent.childCount())]


def _selected_untracked(widget):
    parent = widget.topLevelItem(status.UNTRACKED_IDX)
    return [
        parent.child(i).text(0)
        for i in range(parent.childCount())
        if parent.child(i).isSelected()
    ]


def _select_untracked(widget, names, current):
    parent = widget.topLevelItem(status.UNTRACKED_IDX)
    for i in range(parent.childCount()):
        if parent.child(i).text(0) == current:
            widget.setCurrentItem(parent.child(i))
    for i in range(parent.childCount()):
        if parent.child(i).text(0) in names:
            parent.child(i).setSelected(True)


def _stage_untracked(widget, staged, remaining):
    """Replay the queued signal sequence for staging untracked files.

    In production the model emits previous_contents (old lists) then
    about_to_update, swaps in the new lists, and finally emits updated -- all
    queued, so the slots run after the swap. This mirrors that: capture the old
    lists in previous_contents, swap the model to the post-stage state, run the
    (delayed) _save_selection(), then refresh() as the updated slot would.
    """
    old_untracked = list(widget._model.untracked)
    widget.previous_contents = selection.State([], [], [], old_untracked)
    widget._model.set_contents(staged=staged, untracked=remaining)
    widget._save_selection()
    widget.refresh()


def test_staging_contiguous_untracked_selects_only_the_next_file(widget):
    """Staging a contiguous block leaves only the single following file selected.

    Regression: _save_selection() ran after the model swapped in the new lists,
    so it mapped the still-old selected rows onto the new path list. Staging
    a,b,c recorded d,e as the previous selection and _restore_selection()
    reselected both instead of just d.
    """
    widget._model.set_contents(untracked=['a', 'b', 'c', 'd', 'e'])
    widget.refresh()
    assert _untracked_child_paths(widget) == ['a', 'b', 'c', 'd', 'e']

    _select_untracked(widget, {'a', 'b', 'c'}, current='c')
    _stage_untracked(widget, staged=['a', 'b', 'c'], remaining=['d', 'e'])

    assert _untracked_child_paths(widget) == ['d', 'e']
    assert _selected_untracked(widget) == ['d']


def test_staging_trailing_untracked_selects_the_previous_file(widget):
    """Staging the last files falls back to the nearest preceding survivor."""
    widget._model.set_contents(untracked=['a', 'b', 'c', 'd', 'e'])
    widget.refresh()

    _select_untracked(widget, {'c', 'd', 'e'}, current='e')
    _stage_untracked(widget, staged=['c', 'd', 'e'], remaining=['a', 'b'])

    assert _untracked_child_paths(widget) == ['a', 'b']
    assert _selected_untracked(widget) == ['b']


def test_staging_all_untracked_leaves_nothing_selected(widget):
    """Staging every untracked file clears the section and its selection."""
    widget._model.set_contents(untracked=['a', 'b', 'c'])
    widget.refresh()

    _select_untracked(widget, {'a', 'b', 'c'}, current='b')
    _stage_untracked(widget, staged=['a', 'b', 'c'], remaining=[])

    assert _untracked_child_paths(widget) == []
    assert _selected_untracked(widget) == []
