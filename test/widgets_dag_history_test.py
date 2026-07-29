"""Characterization tests for the existing DAG history widgets."""

import sys
import threading
import time
from typing import ClassVar

import pytest

from cola.models import dag
from cola.models import graph as graph_model
from cola.widgets.dag import (
    COMMIT_ROLE,
    GRAPH_PREV_ROW_ROLE,
    GRAPH_ROW_ROLE,
    CommitTreeWidget,
    GitDAG,
    ReaderThread,
    _HistoryCacheMetadata,
)
from cola.widgets.main import MainView
from qtpy import QtCore, QtGui, QtTest, QtWidgets

from .helper import app_context

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
            obj
            if isinstance(obj, QtCore.QThread)
            else getattr(obj, "active_thread", None)
        )
        if isinstance(thread, QtCore.QThread) and thread.isRunning():
            thread.requestInterruption()
            assert thread.wait(5000)
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


def _commit(context, factory, oid, parents=()):
    commit = dag.Commit(context, factory, oid=oid)
    commit.summary = f"commit {oid}"
    commit.author = "A U Thor"
    commit.authdate = "2026-07-28"
    commit.parents = list(parents)
    commit.generation = max((parent.generation for parent in parents), default=-1) + 1
    for parent in parents:
        parent.children.append(commit)
    return commit


def _graph_result(commits):
    commits = list(commits)
    head_oid = next((commit.oid for commit in commits if "HEAD" in commit.tags), None)
    return graph_model.build_graph(
        [
            (commit.oid, [parent.oid for parent in commit.parents])
            for commit in commits
        ],
        head_oid=head_oid,
    )


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
    factory = dag.CommitFactory()
    root = _commit(app_context, factory, "A")
    middle = _commit(app_context, factory, "B", (root,))
    tip = _commit(app_context, factory, "C", (middle,))
    tree = _tree(app_context, managed_qobject)

    tree.add_commits([root, middle, tip], _graph_result([root, middle, tip]))

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
    factory = dag.CommitFactory()
    root = _commit(app_context, factory, "A")
    left = _commit(app_context, factory, "B", (root,))
    right = _commit(app_context, factory, "C", (root,))
    tree = _tree(app_context, managed_qobject)

    tree.add_commits([root, left, right], _graph_result([root, left, right]))

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
    factory = dag.CommitFactory()
    root = _commit(app_context, factory, "A")
    tip = _commit(app_context, factory, "B", (root,))
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([root, tip], _graph_result([root, tip]))
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


def test_reader_thread_emits_one_final_result_with_exact_repo_error(
    qapp, app_context, managed_qobject, monkeypatch
):
    request = dag.HistoryRequest(9, "bad-ref", 1000, False)
    error = "fatal: exact repository error"
    class FakeReader:
        def __init__(self, _context, _params):
            self.returncode = 128
            self.error = error

        def get(self):
            return iter(())

        def get_worktree_commits(self):
            raise AssertionError("failed reads must not add pseudo-commits")

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", FakeReader)
    thread = managed_qobject(ReaderThread(app_context, request))
    results = QtTest.QSignalSpy(thread.result)

    thread.start()

    assert thread.wait(5000)
    qapp.processEvents()
    assert _spy_count(results) == 1
    result = _spy_payload(results, 0)[0]
    assert result == dag.HistoryResult(9, False, 128, error, (), None)


def test_reader_thread_uses_immutable_request_snapshot(
    qapp, app_context, managed_qobject, monkeypatch
):
    captured = []

    class FakeReader:
        def __init__(self, _context, params):
            captured.append((params.ref, params.count, params.display_status))
            self.returncode = 0
            self.error = ""

        def get(self):
            return iter(())

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", FakeReader)
    request = dag.HistoryRequest(3, "HEAD", 10, False)
    thread = managed_qobject(ReaderThread(app_context, request))
    results = QtTest.QSignalSpy(thread.result)
    # Mutating the live UI parameters after construction cannot affect the request.
    ui_params = dag.DAG("HEAD", 10)
    ui_params.ref = "mutated"
    ui_params.count = 999

    thread.start()

    assert thread.wait(5000)
    qapp.processEvents()
    assert _spy_count(results) == 1
    assert captured == [("HEAD", 10, False)]


def test_reader_thread_interruption_after_empty_read_skips_worktree(
    qapp, app_context, managed_qobject, monkeypatch
):
    entered = threading.Event()
    release = threading.Event()
    worktree_called = threading.Event()

    class BlockingEmptyReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            pass

        def get(self):
            entered.set()
            release.wait()
            return iter(())

        def get_worktree_commits(self):
            worktree_called.set()
            return (None, None)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", BlockingEmptyReader)
    request = dag.HistoryRequest(23, "HEAD", 10, False)
    thread = managed_qobject(ReaderThread(app_context, request))
    results = QtTest.QSignalSpy(thread.result)
    thread.start()
    assert entered.wait(2)

    thread.requestInterruption()
    release.set()

    assert thread.wait(5000)
    qapp.processEvents()
    assert not worktree_called.is_set()
    assert _spy_count(results) == 1
    assert _spy_payload(results, 0)[0] == dag.HistoryResult(
        23, False, -1, "", (), None
    )


class ManualReaderThread(QtCore.QObject):
    result = QtCore.Signal(object)
    finished = QtCore.Signal()
    instances: ClassVar[list] = []

    def __init__(self, _context, request):
        super().__init__()
        self.request = request
        self.running = False
        self.interrupted = False
        self.waited = False
        self.__class__.instances.append(self)

    def start(self):
        self.running = True

    def isRunning(self):
        return self.running

    def requestInterruption(self):
        self.interrupted = True

    def wait(self):
        self.waited = True
        return True

    def emit_result(self, result):
        self.result.emit(result)

    def finish(self):
        self.running = False
        self.finished.emit()

    def complete(self, result):
        self.emit_result(result)
        self.finish()


def _gitdag(app_context, managed_qobject, monkeypatch):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = "#ffffff"
    app_context.app.theme.selection_color.return_value = QtGui.QColor("#4488cc")
    ManualReaderThread.instances = []
    monkeypatch.setattr("cola.widgets.dag.ReaderThread", ManualReaderThread)
    return managed_qobject(GitDAG(app_context, dag.DAG("HEAD", 1000)))


def test_active_same_key_with_new_metadata_schedules_followup(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    old_metadata = _HistoryCacheMetadata(
        ("old-oid",), frozenset({"old-ref"}), 10, False
    )
    new_metadata = _HistoryCacheMetadata(
        ("new-oid",), frozenset({"new-ref"}), 10, False
    )
    assert widget.request_history("same", 10, False, old_metadata)
    active = ManualReaderThread.instances[-1]

    assert widget.request_history("same", 10, False, new_metadata)
    assert widget.pending_request is not None

    active.complete(
        dag.HistoryResult(active.request.run_id, True, 0, "", (), None)
    )
    qapp.processEvents()
    followup = ManualReaderThread.instances[-1]
    assert followup is not active
    assert widget.last_successful_cache_key is None

    followup.complete(
        dag.HistoryResult(followup.request.run_id, True, 0, "", (), None)
    )
    qapp.processEvents()
    assert widget.old_oids == ["new-oid"]
    assert widget.old_refs == {"new-ref"}


def test_history_requests_deduplicate_and_coalesce_last_different_request(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)

    assert widget.request_history("HEAD", 10, False)
    first = ManualReaderThread.instances[-1]
    assert not widget.request_history("HEAD", 10, False)
    assert widget.request_history("main", 20, False)
    assert not widget.request_history("main", 20, False)
    assert widget.request_history("topic", 30, True)

    assert len(ManualReaderThread.instances) == 1
    assert widget.pending_request.cache_key == ("topic", 30, True)

    first.complete(dag.HistoryResult(first.request.run_id, True, 0, "", (), None))
    qapp.processEvents()

    assert len(ManualReaderThread.instances) == 2
    assert ManualReaderThread.instances[-1].request.cache_key == ("topic", 30, True)


def test_pending_same_key_uses_latest_non_none_cache_metadata(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    old_metadata = _HistoryCacheMetadata(
        ("old-oid",), frozenset({"old-ref"}), 10, False
    )
    new_metadata = _HistoryCacheMetadata(
        ("new-oid",), frozenset({"new-ref"}), 10, False
    )
    widget.request_history("blocker", 1, False)
    blocker = ManualReaderThread.instances[-1]
    assert widget.request_history("same", 10, False, old_metadata)

    assert not widget.request_history("same", 10, False, new_metadata)

    blocker.complete(
        dag.HistoryResult(blocker.request.run_id, True, 0, "", (), None)
    )
    qapp.processEvents()
    pending = ManualReaderThread.instances[-1]
    pending.complete(
        dag.HistoryResult(pending.request.run_id, True, 0, "", (), None)
    )
    qapp.processEvents()
    assert widget.old_oids == ["new-oid"]
    assert widget.old_refs == {"new-ref"}


def test_successful_empty_result_clears_items_graph_maps_and_selection(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    widget.restore_selection = lambda: None
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "A")
    widget.request_history("HEAD", 10, False)
    first = ManualReaderThread.instances[-1]
    first.complete(dag.HistoryResult(first.request.run_id, True, 0, "", (commit,), _graph_result((commit,))))
    qapp.processEvents()
    QtTest.QTest.qWait(1)
    qapp.processEvents()
    widget.selection = [commit]
    widget.old_selection = [commit]
    assert widget.treewidget.topLevelItemCount() == 1
    assert widget.graphview.items

    widget.request_history("empty", 10, False)
    empty = ManualReaderThread.instances[-1]
    empty.complete(dag.HistoryResult(empty.request.run_id, True, 0, "", (), None))
    qapp.processEvents()

    assert widget.treewidget.topLevelItemCount() == 0
    assert widget.graphview.items == {}
    assert widget.graphview.commits == []
    assert widget.commits == {}
    assert widget.commit_list == []
    assert widget.selection == []
    assert widget.old_selection == []


def test_failure_preserves_view_sets_error_and_pending_success_clears_it(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    widget.restore_selection = lambda: None
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "A")
    widget.request_history("HEAD", 10, False)
    first = ManualReaderThread.instances[-1]
    first.complete(dag.HistoryResult(first.request.run_id, True, 0, "", (commit,), _graph_result((commit,))))
    qapp.processEvents()

    widget.request_history("bad", 10, False)
    failed = ManualReaderThread.instances[-1]
    widget.request_history("next", 10, False)
    failed.emit_result(
        dag.HistoryResult(failed.request.run_id, False, 128, "fatal: exact", (), None)
    )
    qapp.processEvents()

    assert widget.treewidget.topLevelItemCount() == 1
    assert widget.commit_list == [commit]
    assert widget.loading is True
    assert widget.error_status is None
    assert ManualReaderThread.instances[-1] is failed

    failed.finish()
    qapp.processEvents()
    pending = ManualReaderThread.instances[-1]
    assert pending is not failed
    assert pending.request.ref == "next"
    assert widget.loading is True

    pending.complete(dag.HistoryResult(pending.request.run_id, True, 0, "", (), None))
    qapp.processEvents()
    assert widget.error_status is None
    assert widget.loading is False


def test_stale_result_does_not_change_view(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "A")
    widget.request_history("HEAD", 10, False)
    active = ManualReaderThread.instances[-1]

    widget.thread_result(dag.HistoryResult(active.request.run_id + 99, True, 0, "", (commit,), _graph_result((commit,))))

    assert widget.treewidget.topLevelItemCount() == 0
    assert widget.commits == {}


def test_stop_discards_pending_and_prevents_scheduled_or_late_updates(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    widget.request_history("HEAD", 10, False)
    active = ManualReaderThread.instances[-1]
    widget.request_history("pending", 20, True)
    QtCore.QTimer.singleShot(0, widget.display)

    widget.stop_and_wait()
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "late")
    active.result.emit(
        dag.HistoryResult(active.request.run_id, True, 0, "", (commit,), _graph_result((commit,)))
    )
    qapp.processEvents()

    assert active.interrupted
    assert active.waited
    assert widget.pending_request is None
    assert len(ManualReaderThread.instances) == 1
    assert widget.treewidget.topLevelItemCount() == 0
    assert not widget.request_history("after", 1, False)


# Task 3 review regressions (RED -> GREEN slices).
def test_active_pending_active_discards_pending_and_accepts_active_result(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "A")

    assert widget.request_history("A", 10, False)
    active = ManualReaderThread.instances[-1]
    assert widget.request_history("B", 10, False)
    assert not widget.request_history("A", 10, False)
    assert widget.pending_request is None

    active.emit_result(
        dag.HistoryResult(active.request.run_id, True, 0, "", (commit,), _graph_result((commit,)))
    )
    qapp.processEvents()

    assert widget.commit_list == [commit]
    active.finish()
    qapp.processEvents()
    assert len(ManualReaderThread.instances) == 1
    assert widget.loading is False


def test_active_result_can_apply_when_pending_is_later_discarded(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "A")
    widget.request_history("A", 10, False)
    active = ManualReaderThread.instances[-1]
    widget.request_history("B", 10, False)
    active.emit_result(
        dag.HistoryResult(active.request.run_id, True, 0, "", (commit,), _graph_result((commit,)))
    )
    qapp.processEvents()
    assert widget.commit_list == []

    assert not widget.request_history("A", 10, False)
    qapp.processEvents()

    assert widget.pending_request is None
    assert widget.commit_list == [commit]


def test_active_result_is_invisible_until_pending_finishes(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    old = _commit(app_context, factory, "old")
    active_commit = _commit(app_context, factory, "active")
    pending_commit = _commit(app_context, factory, "pending")
    widget._apply_history_result((old,), _graph_result((old,)))
    widget.last_successful_cache_key = ("old", 1, False)
    widget.error_status = "existing"
    widget.revtext.setToolTip("existing")
    widget.selection = widget.old_selection = [old]

    widget.request_history("A", 10, False)
    active = ManualReaderThread.instances[-1]
    widget.request_history("B", 20, True)
    active.emit_result(
        dag.HistoryResult(active.request.run_id, True, 0, "", (active_commit,), _graph_result((active_commit,)))
    )
    qapp.processEvents()

    assert widget.commit_list == [old]
    assert widget.selection == [old]
    assert widget.error_status == "existing"
    assert widget.last_successful_cache_key == ("old", 1, False)
    assert widget.loading is True
    assert len(ManualReaderThread.instances) == 1

    active.finish()
    qapp.processEvents()
    assert len(ManualReaderThread.instances) == 2
    pending = ManualReaderThread.instances[-1]
    assert widget.loading is True
    pending.emit_result(
        dag.HistoryResult(pending.request.run_id, True, 0, "", (pending_commit,), _graph_result((pending_commit,)))
    )
    qapp.processEvents()
    assert widget.commit_list == [pending_commit]
    pending.finish()
    qapp.processEvents()
    assert widget.loading is False


def test_failure_without_pending_stops_loading_and_shows_visible_exact_error(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    error_label = widget.findChild(QtWidgets.QLabel, "HistoryErrorStatus")
    assert error_label is not None
    assert error_label.isHidden()
    widget.show()
    qapp.processEvents()
    widget.request_history("bad", 10, False)
    active = ManualReaderThread.instances[-1]
    active.emit_result(
        dag.HistoryResult(active.request.run_id, False, 128, "fatal: exact", (), None)
    )
    qapp.processEvents()

    expected = "returncode 128: fatal: exact"
    assert widget.loading is False
    assert widget.error_status == expected
    assert error_label.text() == expected
    assert error_label.isVisible()
    assert widget.revtext.toolTip() == expected
    assert widget.revtext.styleSheet()

    active.finish()
    qapp.processEvents()
    assert widget.loading is False


def test_success_clears_visible_error_tooltip_and_red_hint(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    error_label = widget.findChild(QtWidgets.QLabel, "HistoryErrorStatus")
    assert error_label is not None
    widget.show()
    qapp.processEvents()
    widget.request_history("bad", 10, False)
    failed = ManualReaderThread.instances[-1]
    failed.complete(
        dag.HistoryResult(failed.request.run_id, False, 7, "exact", (), None)
    )
    qapp.processEvents()
    widget.request_history("good", 10, False)
    success = ManualReaderThread.instances[-1]
    success.emit_result(
        dag.HistoryResult(success.request.run_id, True, 0, "", (), None)
    )
    qapp.processEvents()

    assert widget.error_status is None
    assert error_label.text() == ""
    assert error_label.isHidden()
    assert error_label.toolTip() == ""
    assert widget.revtext.toolTip() == ""
    assert widget.revtext.styleSheet() == ""


def test_success_replaces_selection_with_new_commit_objects_synchronously(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    old_factory = dag.CommitFactory()
    old_a = _commit(app_context, old_factory, "A")
    old_b = _commit(app_context, old_factory, "B", (old_a,))
    widget._apply_history_result((old_a, old_b), _graph_result((old_a, old_b)))
    widget.selection = widget.old_selection = [old_a]
    new_factory = dag.CommitFactory()
    new_a = _commit(app_context, new_factory, "A")
    new_b = _commit(app_context, new_factory, "B", (new_a,))
    selected = QtTest.QSignalSpy(widget.commits_selected)

    widget._apply_history_result((new_a, new_b), _graph_result((new_a, new_b)))

    assert widget.selection == [new_a]
    assert widget.old_selection == [new_a]
    assert widget.selection[0] is not old_a
    assert _spy_count(selected) == 1
    assert list(_spy_payload(selected, 0)[0]) == [new_a]


def test_empty_success_clears_downstream_and_emits_once(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "A")
    widget._apply_history_result((commit,), _graph_result((commit,)))
    qapp.processEvents()
    widget.selection = widget.old_selection = [commit]
    widget.diffwidget_copy_commit.setEnabled(True)
    selected = QtTest.QSignalSpy(widget.commits_selected)

    widget._apply_history_result((), graph_model.GraphResult([], 0))
    qapp.processEvents()

    assert widget.selection == widget.old_selection == []
    assert not widget.diffwidget_copy_commit.isEnabled()
    assert _spy_count(selected) == 1
    assert list(_spy_payload(selected, 0)[0]) == []
    assert widget.treewidget.selected_items() == []
    assert widget.graphview.selected_items() == []
    assert widget.filewidget.topLevelItemCount() == 0
    assert widget.diffwidget.oid is None


def test_display_cache_changes_only_after_current_success_and_failure_retries(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    monkeypatch.setattr("cola.widgets.dag.gitcmds.parse_refs", lambda *_args: ["oid-A"])
    widget.model.local_branches = ["main"]
    widget.model.remote_branches = []
    widget.model.tags = []

    widget.display()
    first = ManualReaderThread.instances[-1]
    assert widget.old_oids is None
    assert widget.old_refs == set()
    assert widget.old_count == 0
    assert widget.old_display_status is None
    assert widget.last_successful_cache_key is None

    first.emit_result(
        dag.HistoryResult(first.request.run_id, False, 1, "failed", (), None)
    )
    first.finish()
    qapp.processEvents()
    assert widget.old_oids is None
    assert widget.last_successful_cache_key is None

    widget.model_updated()
    retry = ManualReaderThread.instances[-1]
    assert retry is not first
    retry.emit_result(
        dag.HistoryResult(retry.request.run_id, True, 0, "", (), None)
    )
    qapp.processEvents()
    assert widget.old_oids == ["oid-A"]
    assert widget.old_refs == {"main"}
    assert widget.old_count == widget.maxresults.value()
    assert widget.old_display_status == widget.display_status_action.isChecked()
    assert widget.last_successful_cache_key == retry.request.cache_key


@pytest.mark.parametrize(
    ("phase", "repo_error", "exception_text", "expected_error"),
    [
        ("construct", "", "constructor exploded", "constructor exploded"),
        ("get", "fatal: reader exact", "iteration exploded", "fatal: reader exact"),
        ("worktree", "", "worktree exploded", "worktree exploded"),
    ],
)
def test_reader_thread_converts_exceptions_to_one_exact_failed_result(
    qapp,
    app_context,
    managed_qobject,
    monkeypatch,
    phase,
    repo_error,
    exception_text,
    expected_error,
):
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "A")

    class FakeReader:
        def __init__(self, _context, _params):
            if phase == "construct":
                raise RuntimeError(exception_text)
            self.returncode = 0
            self.error = repo_error

        def get(self):
            yield commit
            if phase == "get":
                raise RuntimeError(exception_text)

        def get_worktree_commits(self):
            if phase == "worktree":
                raise RuntimeError(exception_text)
            return (None, None)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", FakeReader)
    request = dag.HistoryRequest(17, "HEAD", 10, False)
    thread = managed_qobject(ReaderThread(app_context, request))
    results = QtTest.QSignalSpy(thread.result)
    finished = QtTest.QSignalSpy(thread.finished)

    thread.start()
    assert thread.wait(5000)
    qapp.processEvents()

    assert _spy_count(results) == 1
    assert _spy_payload(results, 0)[0] == dag.HistoryResult(
        17, False, -1, expected_error, (), None
    )
    assert _spy_count(finished) == 1


def test_reader_thread_builds_empty_graph_once_in_worker(
    qapp, app_context, managed_qobject, monkeypatch
):
    class EmptyReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            pass

        def get(self):
            return iter(())

        def get_worktree_commits(self):
            return (None, None)

    calls = []
    real_build_graph = graph_model.build_graph

    def recording_build_graph(graph_input, head_oid=None):
        calls.append((threading.get_ident(), list(graph_input), head_oid))
        return real_build_graph(graph_input, head_oid=head_oid)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", EmptyReader)
    monkeypatch.setattr(graph_model, "build_graph", recording_build_graph)
    thread = managed_qobject(
        ReaderThread(app_context, dag.HistoryRequest(20, "HEAD", 10, False))
    )
    results = QtTest.QSignalSpy(thread.result)
    gui_thread_id = threading.get_ident()

    thread.start()
    assert thread.wait(5000)
    qapp.processEvents()

    assert calls == [(calls[0][0], [], None)]
    assert calls[0][0] != gui_thread_id
    result = _spy_payload(results, 0)[0]
    assert result.successful
    assert result.commits == ()
    assert result.graph == graph_model.GraphResult([], 0)


def test_reader_thread_interruption_after_worktree_skips_graph(
    qapp, app_context, managed_qobject, monkeypatch
):
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "A")
    worktree_entered = threading.Event()
    release_worktree = threading.Event()
    build_called = threading.Event()

    class WorktreeBlockingReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            pass

        def get(self):
            return iter((commit,))

        def get_worktree_commits(self):
            worktree_entered.set()
            release_worktree.wait()
            return (None, None)

    def forbidden_build_graph(_graph_input, head_oid=None):
        build_called.set()
        raise AssertionError((head_oid, "graph phase must be skipped"))

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", WorktreeBlockingReader)
    monkeypatch.setattr(graph_model, "build_graph", forbidden_build_graph)
    thread = managed_qobject(
        ReaderThread(app_context, dag.HistoryRequest(22, "HEAD", 10, True))
    )
    results = QtTest.QSignalSpy(thread.result)
    thread.start()
    assert worktree_entered.wait(2)

    thread.requestInterruption()
    release_worktree.set()

    assert thread.wait(5000)
    qapp.processEvents()
    assert not build_called.is_set()
    assert _spy_payload(results, 0)[0] == dag.HistoryResult(
        22, False, -1, "", (), None
    )


def test_reader_thread_builds_graph_from_commits_and_status_pseudo_commits(
    qapp, app_context, managed_qobject, monkeypatch
):
    factory = dag.CommitFactory()
    root = _commit(app_context, factory, "root")
    root.tags = ["HEAD"]
    stage = _commit(app_context, factory, dag.STAGE, (root,))
    worktree = _commit(app_context, factory, dag.WORKTREE, (stage,))

    class StatusReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            pass

        def get(self):
            return iter((root,))

        def get_worktree_commits(self):
            return (stage, worktree)

    calls = []
    real_build_graph = graph_model.build_graph

    def recording_build_graph(graph_input, head_oid=None):
        graph_input = list(graph_input)
        calls.append((threading.get_ident(), graph_input, head_oid))
        return real_build_graph(graph_input, head_oid=head_oid)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", StatusReader)
    monkeypatch.setattr(graph_model, "build_graph", recording_build_graph)
    thread = managed_qobject(
        ReaderThread(app_context, dag.HistoryRequest(24, "HEAD", 10, True))
    )
    results = QtTest.QSignalSpy(thread.result)
    gui_thread_id = threading.get_ident()

    thread.start()
    assert thread.wait(5000)
    qapp.processEvents()

    assert len(calls) == 1
    assert calls[0] == (
        calls[0][0],
        [
            ("root", []),
            (dag.STAGE, ["root"]),
            (dag.WORKTREE, [dag.STAGE]),
        ],
        "root",
    )
    assert calls[0][0] != gui_thread_id
    result = _spy_payload(results, 0)[0]
    assert result.commits == (root, stage, worktree)
    assert {row.commit_oid for row in result.graph.rows} == {
        "root",
        dag.STAGE,
        dag.WORKTREE,
    }


def test_reader_thread_emits_complete_multi_commit_tuple_and_has_no_add_signal(
    qapp, app_context, managed_qobject, monkeypatch
):
    factory = dag.CommitFactory()
    commits = tuple(_commit(app_context, factory, oid) for oid in ("A", "B", "C"))

    class FakeReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            pass

        def get(self):
            return iter(commits)

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", FakeReader)
    thread = managed_qobject(
        ReaderThread(app_context, dag.HistoryRequest(21, "HEAD", 10, False))
    )
    results = QtTest.QSignalSpy(thread.result)

    assert not hasattr(thread, "add")
    thread.start()
    assert thread.wait(5000)
    qapp.processEvents()

    assert _spy_count(results) == 1
    assert _spy_payload(results, 0)[0].commits == commits
    result = _spy_payload(results, 0)[0]
    assert result.graph == _graph_result(commits)


def test_large_history_graph_is_built_once_in_worker_and_applied_atomically(
    qapp, app_context, managed_qobject, monkeypatch
):
    factory = dag.CommitFactory()
    commits = []
    parent = None
    for index in range(2050):
        commit = _commit(
            app_context,
            factory,
            f"{index:040x}",
            (parent,) if parent is not None else (),
        )
        commits.append(commit)
        parent = commit
    commits[-1].tags = ["HEAD"]
    boundary_parent = commits[2047]
    boundary_child = commits[2048]
    partial_read = threading.Event()
    release = threading.Event()

    class LargeReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            pass

        def get(self):
            for index, commit in enumerate(commits):
                yield commit
                if index == 2047:
                    partial_read.set()
                    release.wait()

        def get_worktree_commits(self):
            return (None, None)

    build_calls = []
    real_build_graph = graph_model.build_graph

    def recording_build_graph(graph_input, head_oid=None):
        build_calls.append((threading.get_ident(), list(graph_input), head_oid))
        return real_build_graph(graph_input, head_oid=head_oid)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", LargeReader)
    monkeypatch.setattr(graph_model, "build_graph", recording_build_graph)
    widget = _real_gitdag(app_context, managed_qobject)
    existing_factory = dag.CommitFactory()
    existing = _commit(app_context, existing_factory, "existing")
    existing_graph = real_build_graph([("existing", [])])
    widget._apply_history_result((existing,), existing_graph)
    widget.selection = widget.old_selection = [existing]
    before = (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
        list(widget.selection),
    )
    graph_add_calls = []
    real_graph_add_commits = widget.graphview.add_commits

    def recording_graph_add_commits(added_commits):
        graph_add_calls.append((threading.get_ident(), list(added_commits)))
        return real_graph_add_commits(added_commits)

    monkeypatch.setattr(widget.graphview, "add_commits", recording_graph_add_commits)
    gui_thread_id = threading.get_ident()

    assert widget.request_history("large", len(commits), False)
    thread = widget.active_thread
    assert partial_read.wait(2)
    assert (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
        list(widget.selection),
    ) == before

    release.set()
    assert thread.wait(5000)
    assert len(build_calls) == 1
    assert build_calls[0][0] != gui_thread_id
    assert len(build_calls[0][1]) == len(commits)
    assert build_calls[0][2] == commits[-1].oid
    # The queued final result has not reached the GUI thread yet.
    assert (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
        list(widget.selection),
    ) == before

    qapp.processEvents()

    assert widget.commit_list == commits
    assert set(widget.treewidget.oidmap) >= {commit.oid for commit in commits}
    rows = {
        item.data(0, GRAPH_ROW_ROLE).commit_oid: item.data(0, GRAPH_ROW_ROLE)
        for item in (
            widget.treewidget.topLevelItem(index)
            for index in range(widget.treewidget.topLevelItemCount())
        )
    }
    assert set(rows) == {commit.oid for commit in commits}
    child_row = rows[boundary_child.oid]
    parent_row = rows[boundary_parent.oid]
    assert any(
        edge.from_column == child_row.commit_column
        and edge.to_column == parent_row.commit_column
        for edge in child_row.edges_to_parent
    )
    assert len(graph_add_calls) == 1
    assert graph_add_calls[0] == (gui_thread_id, commits)
    assert widget.graphview.commits == commits


def test_successful_nonempty_result_without_graph_is_rejected(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    existing = _commit(app_context, factory, "existing")
    widget._apply_history_result((existing,), _graph_result((existing,)))
    before = (
        list(widget.commit_list),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
    )
    widget.request_history("missing-graph", 10, False)
    active = ManualReaderThread.instances[-1]

    active.emit_result(
        dag.HistoryResult(active.request.run_id, True, 0, "", (existing,), None)
    )
    qapp.processEvents()

    assert (
        list(widget.commit_list),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
    ) == before
    assert widget.last_successful_cache_key is None
    assert widget.error_status == "successful history result is missing graph data"


def test_stale_result_preserves_loading_error_cache_and_selection(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    existing = _commit(app_context, factory, "existing")
    stale = _commit(app_context, factory, "stale")
    widget._apply_history_result((existing,), _graph_result((existing,)))
    qapp.processEvents()
    widget.selection = widget.old_selection = [existing]
    widget._set_error_status("existing error")
    widget.last_successful_cache_key = ("existing", 1, False)
    widget.old_oids = ["existing"]
    old_items = dict(widget.graphview.items)
    old_oidmap = dict(widget.treewidget.oidmap)
    widget.request_history("active", 10, False)
    active = ManualReaderThread.instances[-1]

    widget.thread_result(
        dag.HistoryResult(active.request.run_id + 1, True, 0, "", (stale,), _graph_result((stale,)))
    )

    assert widget.loading is True
    assert widget.error_status == "existing error"
    assert widget.last_successful_cache_key == ("existing", 1, False)
    assert widget.old_oids == ["existing"]
    assert widget.selection == [existing]
    assert widget.commit_list == [existing]
    assert widget.graphview.items == old_items
    assert widget.treewidget.oidmap == old_oidmap


def test_failure_preserves_all_applied_state_and_cache(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, "A")
    widget._apply_history_result((commit,), _graph_result((commit,)))
    qapp.processEvents()
    widget.selection = widget.old_selection = [commit]
    widget.last_successful_cache_key = ("old", 1, False)
    widget.old_oids = ["A"]
    before = (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
        list(widget.selection),
        widget.last_successful_cache_key,
        list(widget.old_oids),
    )
    widget.request_history("bad", 10, False)
    active = ManualReaderThread.instances[-1]

    active.emit_result(
        dag.HistoryResult(active.request.run_id, False, 128, "fatal", (), None)
    )

    after = (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
        list(widget.selection),
        widget.last_successful_cache_key,
        list(widget.old_oids),
    )
    assert after == before


@pytest.mark.parametrize("outcome", ["failure", "stale", "stop"])
def test_partial_real_reader_outcomes_preserve_last_successful_view(
    outcome, qapp, app_context, managed_qobject, monkeypatch
):
    factory = dag.CommitFactory()
    replacement = _commit(app_context, factory, "replacement")
    partial_read = threading.Event()
    release = threading.Event()

    class PartialReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            pass

        def get(self):
            yield replacement
            partial_read.set()
            release.wait()
            if outcome == "failure":
                self.returncode = 128
                self.error = "fatal after partial read"

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", PartialReader)
    widget = _real_gitdag(app_context, managed_qobject)
    existing_factory = dag.CommitFactory()
    existing = _commit(app_context, existing_factory, "existing")
    widget._apply_history_result((existing,), _graph_result((existing,)))
    widget.selection = widget.old_selection = [existing]
    widget.last_successful_cache_key = ("existing", 1, False)
    before = (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
        list(widget.selection),
        widget.last_successful_cache_key,
    )

    assert widget.request_history(outcome, 10, False)
    thread = widget.active_thread
    assert partial_read.wait(2)
    assert (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
        list(widget.selection),
        widget.last_successful_cache_key,
    ) == before

    if outcome == "stale":
        widget.active_run_id += 1
        release.set()
        assert thread.wait(5000)
    elif outcome == "stop":
        helper = threading.Thread(target=lambda: (time.sleep(0.05), release.set()))
        helper.start()
        widget.stop_and_wait()
        helper.join(2)
    else:
        release.set()
        assert thread.wait(5000)
    qapp.processEvents()

    assert (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(widget.graphview.items),
        list(widget.selection),
        widget.last_successful_cache_key,
    ) == before


def _real_gitdag(app_context, managed_qobject):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = "#ffffff"
    app_context.app.theme.selection_color.return_value = QtGui.QColor("#4488cc")
    return managed_qobject(GitDAG(app_context, dag.DAG("HEAD", 1000)))


def test_close_waits_for_real_blocked_reader_and_discards_pending(
    qapp, app_context, managed_qobject, monkeypatch
):
    entered = threading.Event()
    release = threading.Event()
    exited = threading.Event()
    constructed = []

    class BlockingReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            constructed.append(self)

        def get(self):
            entered.set()
            release.wait()
            exited.set()
            return iter(())

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", BlockingReader)
    widget = _real_gitdag(app_context, managed_qobject)
    assert widget.request_history("active", 10, False)
    assert entered.wait(2)
    assert widget.request_history("pending", 20, True)
    active_thread = widget.active_thread

    helper = threading.Thread(target=lambda: (time.sleep(0.1), release.set()))
    helper.start()
    assert widget.close()
    # Freeze the state at the instant close() returns.  Cleanup happens before
    # asserting it so a deliberate missing-wait mutation reports cleanly
    # instead of aborting Qt while a QThread is still running.
    exited_at_close = exited.is_set()
    release.set()
    helper.join(2)
    if active_thread.isRunning():
        assert active_thread.wait(2000)
    qapp.processEvents()

    assert exited_at_close
    assert len(constructed) == 1
    assert widget.pending_request is None
    assert widget.active_thread is None
    assert widget.commit_list == []
    assert not widget.request_history("after-close", 1, False)


def test_close_before_scheduled_display_prevents_reader_start(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _gitdag(app_context, managed_qobject, monkeypatch)
    QtCore.QTimer.singleShot(0, widget.display)

    assert widget.close()
    qapp.processEvents()

    assert ManualReaderThread.instances == []
    assert widget.stopping


def test_real_thread_stop_finalizes_once_and_queued_finished_is_noop(
    qapp, app_context, managed_qobject, monkeypatch
):
    entered = threading.Event()
    release = threading.Event()

    class BlockingReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            pass

        def get(self):
            entered.set()
            release.wait()
            return iter(())

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", BlockingReader)
    widget = _real_gitdag(app_context, managed_qobject)
    widget.request_history("active", 10, False)
    thread = widget.active_thread
    destroyed = QtTest.QSignalSpy(thread.destroyed)
    assert entered.wait(2)
    helper = threading.Thread(target=lambda: (time.sleep(0.05), release.set()))
    helper.start()

    widget.stop_and_wait()
    helper.join(2)
    assert widget.active_thread is None
    widget._thread_finished(thread)
    qapp.processEvents()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    qapp.processEvents()

    assert _spy_count(destroyed) == 1
    assert widget.active_thread is None
