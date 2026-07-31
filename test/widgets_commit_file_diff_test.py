# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Tests fuer das eigenstaendige Diff-Fenster der Commit-Dateiliste."""

import sys
from unittest.mock import MagicMock

import pytest

from cola.widgets.diff import CommitFileDiffWindow
from cola.widgets.diff import DiffInfoTask
from cola.widgets.diff import DiffRangeTask
from cola.widgets.diff import show_commit_file_diff
from qtpy import QtCore
from qtpy import QtTest
from qtpy import QtWidgets

from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


@pytest.fixture(scope='module')
def qapp():
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


@pytest.fixture
def managed_qobject(qapp):
    objects = []

    def manage(obj):
        objects.append(obj)
        return obj

    yield manage

    qapp.processEvents()
    for obj in reversed(objects):
        if isinstance(obj, QtWidgets.QWidget):
            obj.close()
    qapp.processEvents()
    for obj in reversed(objects):
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    qapp.processEvents()


def _fake_commit(oid, summary='summary'):
    commit = MagicMock()
    commit.oid = oid
    commit.author = 'A U Thor'
    commit.email = 'author@example.com'
    commit.authdate = '2026-01-01'
    commit.summary = summary
    return commit


def _prepare_context(app_context):
    app_context.runtask = MagicMock()
    app_context.settings.get_gui_state.return_value = {}
    return app_context


def _window(app_context, managed_qobject):
    _prepare_context(app_context)
    return managed_qobject(CommitFileDiffWindow(app_context))


def _last_task(app_context):
    return app_context.runtask.start.call_args[0][0]


def test_window_is_a_top_level_window(qapp, app_context, managed_qobject):
    window = _window(app_context, managed_qobject)

    assert window.isWindow()


def test_set_commit_file_loads_only_that_file(qapp, app_context, managed_qobject):
    window = _window(app_context, managed_qobject)
    commit = _fake_commit('a' * 40)

    window.set_commit_file([commit], 'src/a.py')

    assert app_context.runtask.start.call_count == 1
    task = _last_task(app_context)
    assert isinstance(task, DiffInfoTask)
    assert task.oid == 'a' * 40
    assert task.filename == 'src/a.py'


def test_set_commit_file_survives_the_debounce(qapp, app_context, managed_qobject):
    window = _window(app_context, managed_qobject)

    window.set_commit_file([_fake_commit('a' * 40)], 'src/a.py')
    QtTest.QTest.qWait(3 * window.diffwidget.DIFF_DEBOUNCE_MSEC)
    qapp.processEvents()

    assert app_context.runtask.start.call_count == 1
    assert _last_task(app_context).filename == 'src/a.py'


def test_set_commit_file_uses_a_range_for_multiple_commits(
    qapp, app_context, managed_qobject
):
    window = _window(app_context, managed_qobject)
    first = _fake_commit('a' * 40)
    last = _fake_commit('b' * 40)

    window.set_commit_file([first, last], 'src/a.py')

    task = _last_task(app_context)
    assert isinstance(task, DiffRangeTask)
    assert task.filename == 'src/a.py'


def test_set_commit_file_shows_the_commit_metadata(qapp, app_context, managed_qobject):
    window = _window(app_context, managed_qobject)

    window.set_commit_file([_fake_commit('a' * 40, summary='Titel')], 'src/a.py')

    assert window.diffwidget.summary_label.text() == 'Titel'


def test_set_commit_file_without_commits_does_nothing(
    qapp, app_context, managed_qobject
):
    window = _window(app_context, managed_qobject)

    window.set_commit_file([], 'src/a.py')

    app_context.runtask.start.assert_not_called()


def test_window_title_names_the_file(qapp, app_context, managed_qobject):
    window = _window(app_context, managed_qobject)

    window.set_commit_file([_fake_commit('a' * 40)], 'src/a.py')

    assert 'src/a.py' in window.windowTitle()


def test_window_geometry_survives_a_state_roundtrip(qapp, app_context, managed_qobject):
    window = _window(app_context, managed_qobject)
    window.resize(640, 400)

    state = window.export_state()

    assert state['width'] == 640
    assert state['height'] == 400

    app_context.settings.get_gui_state.return_value = state
    restored = managed_qobject(CommitFileDiffWindow(app_context))

    assert (restored.width(), restored.height()) == (640, 400)


def test_window_saves_its_state_on_close(qapp, app_context, managed_qobject):
    window = _window(app_context, managed_qobject)
    calls = []
    window.save_settings = lambda settings=None: calls.append(settings)

    window.close()

    assert len(calls) == 1


def test_show_creates_a_window_when_none_exists(qapp, app_context, managed_qobject):
    _prepare_context(app_context)

    window = show_commit_file_diff(
        app_context, None, [_fake_commit('a' * 40)], 'src/a.py'
    )
    managed_qobject(window)

    assert isinstance(window, CommitFileDiffWindow)
    assert window.isVisible()


def test_show_reuses_the_given_window(qapp, app_context, managed_qobject):
    _prepare_context(app_context)
    first = show_commit_file_diff(
        app_context, None, [_fake_commit('a' * 40)], 'src/a.py'
    )
    managed_qobject(first)

    second = show_commit_file_diff(
        app_context, None, [_fake_commit('b' * 40)], 'src/b.py', window=first
    )

    assert second is first
    assert 'src/b.py' in first.windowTitle()


def test_show_loads_the_new_file_into_the_reused_window(
    qapp, app_context, managed_qobject
):
    _prepare_context(app_context)
    window = managed_qobject(CommitFileDiffWindow(app_context))

    show_commit_file_diff(
        app_context, None, [_fake_commit('a' * 40)], 'src/b.py', window=window
    )

    assert _last_task(app_context).filename == 'src/b.py'
