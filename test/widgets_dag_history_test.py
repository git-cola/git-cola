"""Characterization tests for the existing DAG history widgets."""

import sys

import pytest

from cola.models import dag
from cola.widgets.dag import (
    COMMIT_ROLE,
    GRAPH_PREV_ROW_ROLE,
    GRAPH_ROW_ROLE,
    CommitTreeWidget,
    GitDAG,
    ReaderThread,
)
from cola.widgets.main import MainView
from qtpy import QtCore, QtTest, QtWidgets

from .helper import app_context, commit_files, run_git

# Prevent unused imports lint errors.
assert app_context is not None


# Captured from QMainWindow.saveState(version=2) for MainView's existing v2 dock
# set. Its contract is limited to restoring those existing docks; it deliberately
# says nothing about a future history dock.
LEGACY_MAINVIEW_V2_WINDOWSTATE = (
    "AAAA/wAAAAL9AAAAAgAAAAIAAAKAAAAA7vwBAAAAA/sAAAAMAFMAdABhAHQAdQBz"
    "AQAAAAAAAADRAAAAXAAAAN77AAAADABDAG8AbQBtAGkAdAEAAADXAAAA0gAAAEoA"
    "/////AAAAa8AAADRAAAAggD////6AAAAAAEAAAAE+wAAABAAQgByAGEAbgBjAGgA"
    "ZQBzAQAAAAD/////AAAAggD////7AAAAFABTAHUAYgBtAG8AZAB1AGwAZQBzAQAA"
    "AAD/////AAAAbAD////7AAAAEgBGAGEAdgBvAHIAaQB0AGUAcwAAAAAA/////wAA"
    "AFYA////+wAAAAwAUgBlAGMAZQBuAHQAAAAAAP////8AAABIAP///wAAAAMAAAKA"
    "AAAA2fwBAAAAAvsAAAAIAEQAaQBmAGYBAAAAAAAAAoAAAABGAP////wAAAAA////"
    "/wAAAAAA////+v////8BAAAAAvsAAAAOAEEAYwB0AGkAbwBuAHMAAAAAAP////8A"
    "AABLAP////sAAAAOAEMAbwBuAHMAbwBsAGUAAAAAAP////8AAAATAP///wAAAoAA"
    "AAAAAAAABAAAAAQAAAAIAAAACPwAAAAA"
)


@pytest.fixture(scope="module")
def qapp():
    """Provide a QApplication for offscreen widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ["git-cola-test"]
        )
    yield instance


@pytest.fixture
def managed_qobject(qapp):
    """Delete parentless Qt test objects after stopping any worker thread."""
    objects = []

    def manage(obj):
        objects.append(obj)
        return obj

    yield manage

    # Flush queued signals and short single-shot widget initialization timers
    # before deleting their receivers.
    QtTest.QTest.qWait(5)
    qapp.processEvents()
    for obj in reversed(objects):
        thread = (
            obj if isinstance(obj, QtCore.QThread) else getattr(obj, "thread", None)
        )
        if isinstance(thread, QtCore.QThread) and thread.isRunning():
            thread.requestInterruption()
            assert thread.wait(5000)
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


def _commit(context, oid, parents=()):
    commit = dag.Commit(context, oid=oid)
    commit.summary = f"commit {oid}"
    commit.author = "A U Thor"
    commit.authdate = "2026-07-28"
    commit.parents = list(parents)
    commit.generation = max((parent.generation for parent in parents), default=-1) + 1
    for parent in parents:
        parent.children.append(commit)
    return commit


def _tree(app_context, managed_qobject):
    return managed_qobject(CommitTreeWidget(app_context, None))


def _spy_count(spy):
    if hasattr(spy, "__len__"):
        return len(spy)
    return spy.count()


def _spy_payload(spy, index):
    if hasattr(spy, "__getitem__"):
        return spy[index]
    return spy.at(index)


def test_display_inline_graph_installs_and_removes_delegate(
    qapp, app_context, managed_qobject
):
    tree = _tree(app_context, managed_qobject)

    tree.display_inline_graph(True)
    assert tree.itemDelegateForColumn(0) is tree.graph_delegate

    tree.display_inline_graph(False)
    assert tree.itemDelegateForColumn(0) is None


def test_linear_history_items_expose_graph_and_commit_roles(
    qapp, app_context, managed_qobject
):
    root = _commit(app_context, "A")
    middle = _commit(app_context, "B", (root,))
    tip = _commit(app_context, "C", (middle,))
    tree = _tree(app_context, managed_qobject)

    tree.add_commits([root, middle, tip])

    expected = [("C", None), ("B", "C"), ("A", "B")]
    for index, (oid, previous_oid) in enumerate(expected):
        item = tree.topLevelItem(index)
        graph_row = item.data(0, GRAPH_ROW_ROLE)
        previous_row = item.data(0, GRAPH_PREV_ROW_ROLE)
        commit = item.data(0, COMMIT_ROLE)
        assert graph_row.commit_oid == oid
        assert commit.oid == oid
        assert (previous_row.commit_oid if previous_row else None) == previous_oid


def test_fork_history_items_expose_graph_and_commit_roles(
    qapp, app_context, managed_qobject
):
    root = _commit(app_context, "A")
    left = _commit(app_context, "B", (root,))
    right = _commit(app_context, "C", (root,))
    tree = _tree(app_context, managed_qobject)

    tree.add_commits([root, left, right])

    expected = [("C", 0, None), ("B", 1, "C"), ("A", 0, "B")]
    for index, (oid, column, previous_oid) in enumerate(expected):
        item = tree.topLevelItem(index)
        graph_row = item.data(0, GRAPH_ROW_ROLE)
        previous_row = item.data(0, GRAPH_PREV_ROW_ROLE)
        commit = item.data(0, COMMIT_ROLE)
        assert (graph_row.commit_oid, graph_row.commit_column) == (oid, column)
        assert commit.oid == oid
        assert (previous_row.commit_oid if previous_row else None) == previous_oid


def test_tree_selection_emits_selected_commits(qapp, app_context, managed_qobject):
    root = _commit(app_context, "A")
    tip = _commit(app_context, "B", (root,))
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([root, tip])
    selected = QtTest.QSignalSpy(tree.commits_selected)

    tree.topLevelItem(0).setSelected(True)

    assert selected.wait(1000)
    qapp.processEvents()
    assert _spy_count(selected) == 1
    assert list(_spy_payload(selected, 0)[0]) == [tip]


def test_gitdag_round_trips_legacy_flat_history_state(
    qapp, app_context, managed_qobject
):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = "#ffffff"
    params = dag.DAG("HEAD", 1000)
    widget = managed_qobject(GitDAG(app_context, params))
    state = {
        "count": 321,
        "display_inline_graph": False,
        "display_status": False,
        "log": {"column_widths": [240, 120, 999]},
    }

    widget.apply_state(state)
    exported = widget.export_state()

    assert params.count == 321
    assert params.display_status is False
    assert widget.display_status_action.isChecked() is False
    assert exported["count"] == 321
    assert exported["display_inline_graph"] is False
    assert exported["display_status"] is False
    assert widget.treewidget.itemDelegateForColumn(0) is None
    assert exported["log"]["column_widths"][:2] == [240, 120]


def test_mainview_accepts_legacy_version_2_dock_state(
    qapp, app_context, managed_qobject
):
    app_context.settings.get_gui_state.return_value = {}
    app_context.settings.bookmarks = []
    app_context.settings.recent = []
    app_context.app.theme.background_color_rgb.return_value = "#ffffff"
    widget = managed_qobject(MainView(app_context))
    legacy_state = widget.export_state()
    legacy_state["windowstate"] = LEGACY_MAINVIEW_V2_WINDOWSTATE
    legacy_state.pop("history", None)
    legacy_state.pop("show_history", None)

    assert widget.widget_version == 2
    assert widget.apply_state(legacy_state)
    widget.show()
    qapp.processEvents()

    assert widget.dockWidgetArea(widget.statusdock) == QtCore.Qt.TopDockWidgetArea
    assert widget.dockWidgetArea(widget.diffdock) == QtCore.Qt.BottomDockWidgetArea
    assert widget.statusdock.isVisible()
    assert widget.diffdock.isVisible()
    assert widget.actionsdock.isVisible() is False
    assert widget.logdock.isVisible() is False
    assert widget.submodulesdock in widget.tabifiedDockWidgets(widget.branchdock)


def test_reader_thread_emits_begin_add_status_end(qapp, app_context, managed_qobject):
    commit_files()
    expected_oid = run_git("rev-parse", "HEAD").strip()
    app_context.model.update_status()
    params = dag.DAG("HEAD", 1000)
    params.set_display_status(False)
    thread = managed_qobject(ReaderThread(app_context, params))
    events = []
    begin_spy = QtTest.QSignalSpy(thread.begin)
    add_spy = QtTest.QSignalSpy(thread.add)
    status_spy = QtTest.QSignalSpy(thread.status)
    end_spy = QtTest.QSignalSpy(thread.end)
    thread.begin.connect(lambda: events.append(("begin", None)))
    thread.add.connect(
        lambda commits: events.append(("add", [commit.oid for commit in commits]))
    )
    thread.status.connect(lambda successful: events.append(("status", successful)))
    thread.end.connect(lambda: events.append(("end", None)))

    thread.start()

    if not end_spy:
        assert end_spy.wait(5000)
    assert thread.wait(5000)
    qapp.processEvents()
    assert (
        _spy_count(begin_spy)
        == _spy_count(add_spy)
        == _spy_count(status_spy)
        == _spy_count(end_spy)
        == 1
    )
    assert [name for name, _value in events] == ["begin", "add", "status", "end"]
    assert events[1] == ("add", [expected_oid])
    assert [commit.oid for commit in _spy_payload(add_spy, 0)[0]] == [expected_oid]
    assert events[2] == ("status", True)
