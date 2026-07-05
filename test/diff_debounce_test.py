"""Tests for the debounced, supersede-guarded diff loading in CommitDiffWidget.

Stepping commit-to-commit in the DAG must not spawn a "git diff" for every
commit passed over, and a slow diff that finishes after the selection has
moved on must not overwrite the diff for the current commit.
"""
import sys
from unittest.mock import MagicMock

import pytest

from cola.widgets.diff import CommitDiffWidget
from qtpy import QtWidgets

from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


def _make_commit(oid):
    commit = MagicMock()
    commit.oid = oid
    commit.author = 'A U Thor'
    commit.email = 'author@example.com'
    commit.authdate = '2026-01-01'
    commit.summary = 'summary'
    return commit


def _make_widget(app_context):
    widget = CommitDiffWidget(app_context, None, is_commit=True)
    # Observe diff task scheduling without running real git.
    app_context.runtask = MagicMock()
    return widget


def test_commits_selected_debounces_diff_load(qapp, app_context):
    """Rapid selection changes only load the diff for the settled-on commit."""
    widget = _make_widget(app_context)

    # Step through three commits faster than the debounce interval.
    for oid in ('a' * 40, 'b' * 40, 'c' * 40):
        widget.commits_selected([_make_commit(oid)])

    # No diff task has been started yet -- only the timer is pending.
    app_context.runtask.start.assert_not_called()
    assert widget._pending_diff == ('oid', 'c' * 40)
    # Metadata still tracks the latest selection for immediate responsiveness.
    assert widget.oid == 'c' * 40

    # Fire the debounce as the event loop eventually would.
    widget._load_pending_diff()
    assert app_context.runtask.start.call_count == 1
    assert widget._pending_diff is None


def test_empty_selection_cancels_pending_diff(qapp, app_context):
    """Clearing the selection drops any pending diff load."""
    widget = _make_widget(app_context)

    widget.commits_selected([_make_commit('a' * 40)])
    assert widget._pending_diff is not None

    widget.commits_selected([])
    assert widget._pending_diff is None
    assert not widget._diff_timer.isActive()
    app_context.runtask.start.assert_not_called()


def test_set_diff_drops_superseded_result(qapp, app_context):
    """A result from a superseded task is discarded; the latest one applies."""
    widget = _make_widget(app_context)
    widget.diff = MagicMock()

    # Two diffs started in sequence: a stale token (1) then the current one (2).
    stale_token = 1
    current_token = 2
    widget._diff_token = current_token

    # The stale result arrives late and must be ignored.
    widget.set_diff('stale diff', stale_token)
    widget.diff.set_diff.assert_not_called()

    # The current result is applied.
    widget.set_diff('current diff', current_token)
    widget.diff.set_diff.assert_called_once_with('current diff')


def test_set_diff_without_token_applies_immediately(qapp, app_context):
    """Direct callers (e.g. graph diff) pass no token and are never dropped."""
    widget = _make_widget(app_context)
    widget.diff = MagicMock()

    widget.set_diff('direct diff')
    widget.diff.set_diff.assert_called_once_with('direct diff')
