"""Main-window history dock integration and v2 layout migration tests."""

import sys
import threading
import time

import pytest

from cola.widgets import standard
from cola.widgets.dag import CommitHistoryWidget
from cola.widgets.main import MainView
from qtpy import QtCore, QtGui, QtTest, QtWidgets

from .helper import app_context

assert app_context is not None

HISTORY_KEYS = {
    "ref",
    "count",
    "display_inline_graph",
    "display_status",
    "log",
}

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
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ["git-cola-test"]
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
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    qapp.processEvents()


@pytest.fixture
def main_context(app_context):
    app_context.settings.get_gui_state.return_value = {}
    app_context.settings.bookmarks = []
    app_context.settings.recent = []
    app_context.app.theme.background_color_rgb.return_value = "#ffffff"
    app_context.app.theme.selection_color.return_value = QtGui.QColor("#4488cc")
    return app_context


def _show(qapp, window):
    window.resize(1000, 800)
    window.show()
    QtTest.QTest.qWait(1)
    qapp.processEvents()


def _legacy_v2_state(window):
    """Build state around the fixed pre-Task7 MainView-v2 Qt layout blob."""
    state = window.export_state()
    state["windowstate"] = LEGACY_MAINVIEW_V2_WINDOWSTATE
    state.pop("show_history", None)
    state.pop("history", None)
    return state


def _history_is_active(dock):
    return not dock.widget().visibleRegion().isEmpty()


def test_real_legacy_v2_state_preserves_existing_docks_and_reveals_history(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    legacy_state = _legacy_v2_state(window)
    decoded = bytes(
        QtCore.QByteArray.fromBase64(LEGACY_MAINVIEW_V2_WINDOWSTATE.encode("ascii"))
    )

    assert "History".encode("utf-16-be") not in decoded
    assert "History".encode("utf-16-le") not in decoded

    _show(qapp, window)
    window.tabifyDockWidget(window.historydock, window.commitdock)
    window.commitdock.raise_()

    assert window.widget_version == 2
    assert window.apply_state(legacy_state)
    qapp.processEvents()

    assert window.dockWidgetArea(window.statusdock) == QtCore.Qt.TopDockWidgetArea
    assert window.dockWidgetArea(window.diffdock) == QtCore.Qt.BottomDockWidgetArea
    assert window.statusdock.isVisible()
    assert window.diffdock.isVisible()
    assert not window.actionsdock.isVisible()
    assert not window.logdock.isVisible()
    assert window.submodulesdock in window.tabifiedDockWidgets(window.branchdock)
    assert window.historydock.isVisible()
    assert _history_is_active(window.historydock)


def test_mainview_has_exactly_one_dock_owned_history_widget(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))

    assert window.historydock.objectName() == "History"
    assert window.historydock.widget() is window.historywidget
    assert window.historywidget.parent() is window.historydock
    assert isinstance(window.historywidget, CommitHistoryWidget)
    assert window.findChildren(CommitHistoryWidget) == [window.historywidget]
    assert window.dockWidgetArea(window.historydock) == QtCore.Qt.TopDockWidgetArea
    assert window.historydock not in window.tabifiedDockWidgets(window.commitdock)
    for child_owned_name in (
        "active_thread",
        "active_request",
        "pending_request",
        "last_successful_cache_key",
        "selection",
        "commit_list",
        "commits",
    ):
        assert not hasattr(window, child_owned_name), child_owned_name


def test_mainview_history_defaults_are_explicit(qapp, main_context, managed_qobject):
    window = managed_qobject(MainView(main_context))

    request = window.historywidget.current_request()

    assert request.ref == "--all"
    assert request.count == 1000
    assert request.display_status is False
    assert window.historywidget.display_status_action.isChecked() is False
    assert window.historywidget.display_inline_graph_action.isChecked() is False


def test_model_update_does_not_start_mainview_history_work(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    requests = []
    window.historywidget.request_history = lambda *args, **kwargs: requests.append(
        (args, kwargs)
    )

    main_context.model.updated.emit()
    QtTest.QTest.qWait(5)
    qapp.processEvents()

    assert requests == []
    assert window.historywidget.active_thread is None


def test_explicit_history_visibility_is_applied_after_qt_restore(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    legacy_state = _legacy_v2_state(window)
    _show(qapp, window)

    hidden_state = dict(legacy_state, show_history=False)
    assert window.apply_state(hidden_state)
    qapp.processEvents()
    assert not window.historydock.isVisible()

    window.tabifyDockWidget(window.historydock, window.commitdock)
    window.commitdock.raise_()
    shown_state = dict(legacy_state, show_history=True)
    assert window.apply_state(shown_state)
    qapp.processEvents()
    assert window.historydock.isVisible()
    assert _history_is_active(window.historydock)


def test_export_owns_visibility_and_nests_exact_canonical_history_state(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    history = window.historywidget
    history.set_values("main --", 321, True)
    history.display_inline_graph_action.setChecked(True)
    history.treewidget.display_inline_graph(True)
    history.treewidget.set_column_widths([211, 122])

    state = window.export_state()

    assert state["show_history"] is (not window.historydock.isHidden())
    assert set(state["history"]) == HISTORY_KEYS
    assert state["history"] == history.export_state()
    assert state["history"] == {
        "ref": "main --",
        "count": 321,
        "display_inline_graph": True,
        "display_status": True,
        "log": {"column_widths": [211, 122]},
    }
    assert HISTORY_KEYS.isdisjoint(state.keys())

    restored = managed_qobject(MainView(main_context))
    _show(qapp, restored)
    assert restored.apply_state(state)
    assert restored.historywidget.export_state() == state["history"]


def test_export_history_visibility_is_independent_of_hidden_parent(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))

    assert window.isVisible() is False
    assert window.export_state()["show_history"] is True

    window.historydock.hide()

    assert window.export_state()["show_history"] is False


@pytest.mark.parametrize("history_state", [None, [], {"count": "bad"}])
def test_malformed_history_state_returns_false_without_partial_hide(
    qapp, main_context, managed_qobject, history_state
):
    window = managed_qobject(MainView(main_context))
    state = _legacy_v2_state(window)
    state["history"] = history_state
    state["show_history"] = False
    _show(qapp, window)
    defaults = window.historywidget.export_state()

    assert window.apply_state(state) is False
    qapp.processEvents()

    assert window.historywidget.export_state() == defaults
    assert window.historydock.isVisible()
    assert _history_is_active(window.historydock)


def test_malformed_task7_state_is_rejected_before_any_existing_state_changes(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, window.statusdock)
    window.set_lock_layout(False)
    window.lock_layout_action.setChecked(False)
    window.statuswidget.filter_widget.hide()
    window.model.set_ref_sort(0)
    before_history = window.historywidget.export_state()

    state = _legacy_v2_state(window)
    state.update(
        history={"ref": "mutated", "count": "bad"},
        show_history=False,
        lock_layout=True,
        show_status_filter=True,
        ref_sort=1,
    )

    assert window.apply_state(state) is False
    qapp.processEvents()

    assert window.dockWidgetArea(window.statusdock) == QtCore.Qt.LeftDockWidgetArea
    assert window.lock_layout is False
    assert window.lock_layout_action.isChecked() is False
    assert window.statuswidget.filter_widget.isVisible() is False
    assert window.model.ref_sort == 0
    assert window.historywidget.export_state() == before_history
    assert window.historydock.isVisible()
    assert _history_is_active(window.historydock)


def test_non_bool_history_visibility_is_rejected_before_state_changes(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    window.statuswidget.filter_widget.hide()
    state = _legacy_v2_state(window)
    state.update(
        history=window.historywidget.export_state(),
        show_history=0,
        show_status_filter=True,
    )

    assert window.apply_state(state) is False

    assert window.statuswidget.filter_widget.isVisible() is False
    assert window.historydock.isVisible()
    assert _history_is_active(window.historydock)


def test_missing_history_child_is_valid_legacy_state(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    state = _legacy_v2_state(window)
    _show(qapp, window)
    defaults = window.historywidget.export_state()

    assert window.apply_state(state)
    assert window.historywidget.export_state() == defaults
    assert window.historydock.isVisible()
    assert _history_is_active(window.historydock)


@pytest.mark.parametrize("state", [None, [], "invalid"])
def test_non_dict_state_returns_false_with_usable_history_fallback(
    qapp, main_context, managed_qobject, state
):
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    window.historydock.hide()

    assert window.apply_state(state) is False
    qapp.processEvents()

    assert window.historydock.isVisible()
    assert _history_is_active(window.historydock)
    assert window.historywidget.current_request().ref == "--all"


def test_invalid_qt_state_returns_false_and_reveals_default_history(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    state = window.export_state()
    state["windowstate"] = "not-a-valid-qt-state"
    state["show_history"] = False
    window.historydock.hide()

    assert window.apply_state(state) is False
    qapp.processEvents()

    assert window.dockWidgetArea(window.historydock) == QtCore.Qt.TopDockWidgetArea
    assert window.historydock.isVisible()
    assert _history_is_active(window.historydock)


def test_view_menu_is_rebuilt_without_duplicates_and_finds_dynamic_toolbars(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    history_toggle = window.historydock.toggleViewAction()

    window.build_view_menu(window.view_menu)
    qapp.processEvents()

    dynamic_toolbar = QtWidgets.QToolBar("Dynamic Toolbar", window)
    dynamic_toolbar.setObjectName("DynamicToolbar")
    dynamic_toolbar.addAction("Dynamic Action")
    window.addToolBar(dynamic_toolbar)
    dynamic_toggle = dynamic_toolbar.toggleViewAction()

    for _ in range(2):
        window.build_view_menu(window.view_menu)
        qapp.processEvents()
        actions = window.view_menu.actions()
        assert [action for action in actions if action is history_toggle] == [
            history_toggle
        ]
        assert [action for action in actions if action is dynamic_toggle] == [
            dynamic_toggle
        ]
        assert sum(action.text() == dynamic_toggle.text() for action in actions) == 1

    assert [action for action in window.actions() if action is history_toggle] == [
        history_toggle
    ]


def test_mainview_close_waits_for_real_blocked_history_and_discards_pending(
    qapp, main_context, managed_qobject, monkeypatch
):
    entered = threading.Event()
    release = threading.Event()
    exited = threading.Event()
    close_started = threading.Event()
    interrupted_at_exit = []
    constructed = []

    class BlockingReader:
        returncode = 0
        error = ""

        def __init__(self, _context, _params):
            constructed.append(self)

        def get(self):
            entered.set()
            release.wait()
            interrupted_at_exit.append(
                QtCore.QThread.currentThread().isInterruptionRequested()
            )
            exited.set()
            return iter(())

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr("cola.widgets.dag.dag.RepoReader", BlockingReader)
    main_context.browser_windows = []
    window = managed_qobject(MainView(main_context))
    history = window.historywidget
    assert history.request_history("active", 10, False)
    assert entered.wait(2)
    assert history.request_history("pending", 20, True)
    active_thread = history.active_thread

    order = []
    real_close_popup = history.close_popup
    real_stop_and_wait = history.stop_and_wait
    real_standard_close = standard.MainWindow.closeEvent

    def close_popup():
        order.append("popup")
        real_close_popup()

    def stop_and_wait():
        order.append("stop")
        real_stop_and_wait()

    def standard_close(self, event):
        if self is window:
            order.append("standard")
        return real_standard_close(self, event)

    monkeypatch.setattr(history, "close_popup", close_popup)
    monkeypatch.setattr(history, "stop_and_wait", stop_and_wait)
    monkeypatch.setattr(standard.MainWindow, "closeEvent", standard_close)

    helper_observations = []

    def release_from_controlled_path():
        if not close_started.wait(2):
            helper_observations.append(False)
            release.set()
            return
        deadline = time.monotonic() + 2
        while active_thread.isRunning() and time.monotonic() < deadline:
            if active_thread.isInterruptionRequested():
                helper_observations.append(True)
                release.set()
                return
            time.sleep(0.001)
        helper_observations.append(False)
        release.set()

    frozen = {}

    def close_from_event_loop():
        close_started.set()
        try:
            frozen["accepted"] = window.close()
            frozen["exited"] = exited.is_set()
            frozen["running"] = active_thread.isRunning()
            frozen["pending"] = history.pending_request
            frozen["active"] = history.active_thread
            frozen["order"] = list(order)
        finally:
            # A failing close barrier must still release and join the real QThread.
            release.set()

    helper = threading.Thread(target=release_from_controlled_path)
    helper.start()
    QtCore.QTimer.singleShot(0, close_from_event_loop)
    qapp.processEvents()
    helper.join(3)
    release.set()
    if active_thread.isRunning():
        assert active_thread.wait(2000)
    qapp.processEvents()

    assert frozen == {
        "accepted": True,
        "exited": True,
        "running": False,
        "pending": None,
        "active": None,
        "order": ["popup", "stop", "standard"],
    }
    assert helper_observations == [True]
    assert interrupted_at_exit == [True]
    assert len(constructed) == 1

    order.clear()
    assert window.close()
    assert order == ["popup", "stop", "standard"]
