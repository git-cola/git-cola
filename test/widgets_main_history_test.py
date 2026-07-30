# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Main-window history dock integration and v2 layout migration tests."""

import inspect
import subprocess
import sys
import threading
import time
from typing import ClassVar
from unittest.mock import Mock

import pytest

from cola import cmds
from cola import qtutils
from cola.interaction import Interaction
from cola.models import dag as dag_model
from cola.models import graph as graph_model
from cola.widgets import standard
from cola.widgets.dag import GRAPH_ROW_ROLE
from cola.widgets.dag import CommitHistoryWidget
from cola.widgets.main import HISTORY_INLINE_GRAPH_DEFAULT_VERSION
from cola.widgets.main import MainView
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtTest
from qtpy import QtWidgets

from .helper import app_context

assert app_context is not None

HISTORY_KEYS = {
    'ref',
    'count',
    'display_inline_graph',
    'display_status',
    'display_files',
    'files_sizes',
    'log',
}

VIEWER_ACTION_KEYS = {
    'checkout_branch',
    'checkout_detached',
    'cherry_pick',
    'copy',
    'copy_short',
    'create_branch',
    'create_patch',
    'create_tag',
    'create_tarball',
    'diff_commit',
    'diff_commit_all',
    'diff_selected_this',
    'diff_this_selected',
    'rebase_to_commit',
    'reset_hard',
    'reset_keep',
    'reset_merge',
    'reset_mixed',
    'reset_soft',
    'restore_worktree',
    'revert',
    'save_blob',
    'save_blob_from_parent',
    'search_line_range',
}

UNSUPPORTED_MAIN_VIEWER_ACTION_KEYS = {
    'diff_selected_this',
    'diff_this_selected',
    'search_line_range',
}

LEGACY_MAINVIEW_V2_WINDOWSTATE = 'AAAA/wAAAAL9AAAAAgAAAAIAAAKAAAAA7vwBAAAAA/sAAAAMAFMAdABhAHQAdQBz' 'AQAAAAAAAADRAAAAXAAAAN77AAAADABDAG8AbQBtAGkAdAEAAADXAAAA0gAAAEoA' '/////AAAAa8AAADRAAAAggD////6AAAAAAEAAAAE+wAAABAAQgByAGEAbgBjAGgA' 'ZQBzAQAAAAD/////AAAAggD////7AAAAFABTAHUAYgBtAG8AZAB1AGwAZQBzAQAA' 'AAD/////AAAAbAD////7AAAAEgBGAGEAdgBvAHIAaQB0AGUAcwAAAAAA/////wAA' 'AFYA////+wAAAAwAUgBlAGMAZQBuAHQAAAAAAP////8AAABIAP///wAAAAMAAAKA' 'AAAA2fwBAAAAAvsAAAAIAEQAaQBmAGYBAAAAAAAAAoAAAABGAP////wAAAAA////' '/wAAAAAA////+v////8BAAAAAvsAAAAOAEEAYwB0AGkAbwBuAHMAAAAAAP////8A' 'AABLAP////sAAAAOAEMAbwBuAHMAbwBsAGUAAAAAAP////8AAAATAP///wAAAoAA' 'AAAAAAAABAAAAAQAAAAIAAAACPwAAAAA'


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


@pytest.fixture
def main_context(app_context, monkeypatch):
    monkeypatch.setattr(Interaction, 'log_status', Mock())
    monkeypatch.setattr(Interaction, 'log', Mock())
    app_context.settings.get_gui_state.return_value = {}
    app_context.browser_windows = []
    app_context.settings.bookmarks = []
    app_context.settings.recent = []
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    app_context.timestamp = 0.0
    return app_context


def _spy_count(spy):
    try:
        return len(spy)
    except TypeError:
        return spy.count()


def _drain_initialization(qapp):
    for _ in range(3):
        qapp.processEvents()
        QtTest.QTest.qWait(1)


def _git(*args, cwd=None):
    return subprocess.run(
        ('git', *args), cwd=cwd, check=True, text=True, capture_output=True
    ).stdout.strip()


def _wait_for_history(qapp, window, oid=None):
    history = window.historywidget
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        qapp.processEvents()
        ready = window._initial_history_loaded and history.active_thread is None
        if ready and (oid is None or oid in history.commits):
            break
        QtTest.QTest.qWait(10)
    assert window._initial_history_loaded
    assert history.active_thread is None
    if oid is not None:
        assert oid in history.commits, (
            history.repository_generation,
            history.successful_repository_generation,
            history.last_successful_cache_key,
            history.active_request,
            history.pending_request,
            history.error_status,
        )
        item = history.treewidget.oidmap[oid]
        assert item.data(0, GRAPH_ROW_ROLE).commit_oid == oid


def _main_with_refresh_spy(main_context, managed_qobject, monkeypatch):
    calls = []
    original_refresh = MainView.refresh

    def recording_refresh(window):
        calls.append(window)
        return original_refresh(window)

    monkeypatch.setattr(MainView, 'refresh', recording_refresh)
    return managed_qobject(MainView(main_context)), calls


def _wait_for_head(qapp, window, oid, refresh_calls, baseline):
    history = window.historywidget
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        qapp.processEvents()
        commit = history.commits.get(oid)
        if (
            len(refresh_calls) > baseline
            and history.active_thread is None
            and commit is not None
            and 'HEAD' in commit.tags
        ):
            break
        QtTest.QTest.qWait(10)
    assert len(refresh_calls) > baseline
    assert 'HEAD' in history.commits[oid].tags


def _show(qapp, window):
    window.resize(1000, 800)
    window.show()
    QtTest.QTest.qWait(1)
    qapp.processEvents()


class ControlledReaderThread(QtCore.QObject):
    result = QtCore.Signal(object)
    finished = QtCore.Signal()
    instances: ClassVar[list] = []

    def __init__(self, _context, request):
        super().__init__()
        self.request = request
        self.running = False
        self.__class__.instances.append(self)

    def start(self):
        self.running = True

    def isRunning(self):
        return self.running

    def requestInterruption(self):
        self.running = False

    def wait(self):
        return True

    def complete(self, result):
        self.result.emit(result)
        self.running = False
        self.finished.emit()

    def finish(self):
        self.running = False
        self.finished.emit()


def _commit(context, oid):
    factory = dag_model.CommitFactory()
    commit = dag_model.Commit(context, factory, oid=oid)
    commit.summary = f'commit {oid}'
    commit.author = 'A U Thor'
    commit.authdate = '2026-07-29'
    commit.parents = []
    commit.generation = 0
    return commit


def _graph(commits):
    return graph_model.build_graph(
        [(commit.oid, [parent.oid for parent in commit.parents]) for commit in commits]
    )


def _controlled_main(qapp, main_context, managed_qobject, monkeypatch, oids):
    ControlledReaderThread.instances = []
    monkeypatch.setattr('cola.widgets.dag.ReaderThread', ControlledReaderThread)
    main_context.model.local_branches = ['main']
    main_context.model.remote_branches = []
    main_context.model.tags = []
    window = managed_qobject(MainView(main_context))
    assert ControlledReaderThread.instances == []
    _drain_initialization(qapp)
    assert len(ControlledReaderThread.instances) == 1
    return window


def _legacy_v2_state(window):
    """Build state around the fixed pre-Task7 MainView-v2 Qt layout blob."""
    state = window.export_state()
    state['windowstate'] = LEGACY_MAINVIEW_V2_WINDOWSTATE
    state.pop('show_history', None)
    state.pop('history', None)
    state.pop('history_inline_graph_default_version', None)
    return state


def _history_is_active(dock):
    return not dock.widget().visibleRegion().isEmpty()


def test_real_legacy_v2_state_preserves_existing_docks_and_reveals_history(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    legacy_state = _legacy_v2_state(window)
    decoded = bytes(
        QtCore.QByteArray.fromBase64(LEGACY_MAINVIEW_V2_WINDOWSTATE.encode('ascii'))
    )

    assert 'History'.encode('utf-16-be') not in decoded
    assert 'History'.encode('utf-16-le') not in decoded

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

    assert window.historydock.objectName() == 'History'
    assert window.historydock.widget() is window.historywidget
    assert window.historywidget.parent() is window.historydock
    assert isinstance(window.historywidget, CommitHistoryWidget)
    assert window.findChildren(CommitHistoryWidget) == [window.historywidget]
    assert window.dockWidgetArea(window.historydock) == QtCore.Qt.TopDockWidgetArea
    assert window.historydock not in window.tabifiedDockWidgets(window.commitdock)
    for child_owned_name in (
        'active_thread',
        'active_request',
        'pending_request',
        'last_successful_cache_key',
        'selection',
        'commit_list',
        'commits',
    ):
        assert not hasattr(window, child_owned_name), child_owned_name


def test_mainview_history_defaults_are_explicit(qapp, main_context, managed_qobject):
    window = managed_qobject(MainView(main_context))

    request = window.historywidget.current_request()

    assert request.ref == '--all'
    assert request.count == 1000
    assert request.display_status is False
    assert window.historywidget.display_status_action.isChecked() is False
    assert window.historywidget.display_inline_graph_action.isChecked() is True
    assert (
        window.historywidget.treewidget.itemDelegateForColumn(0)
        is window.historywidget.treewidget.graph_delegate
    )


def test_mainview_history_context_actions_are_composed_once_and_disable_off_item(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    tree = window.historywidget.treewidget

    assert isinstance(tree.menu_actions, dict)
    assert set(tree.menu_actions) == VIEWER_ACTION_KEYS
    assert len(tree.menu_actions) == 24
    assert len(set(tree.menu_actions.values())) == 24
    assert {
        name for name, action in tree.menu_actions.items() if not action.isVisible()
    } == UNSUPPORTED_MAIN_VIEWER_ACTION_KEYS
    assert all(
        action.shortcut().isEmpty()
        for name, action in tree.menu_actions.items()
        if name in UNSUPPORTED_MAIN_VIEWER_ACTION_KEYS
    )
    assert all(
        action.isVisible()
        for name, action in tree.menu_actions.items()
        if name not in UNSUPPORTED_MAIN_VIEWER_ACTION_KEYS
    )
    event = QtGui.QContextMenuEvent(
        QtGui.QContextMenuEvent.Mouse,
        QtCore.QPoint(-1, -1),
        QtCore.QPoint(-1, -1),
    )
    tree.update_menu_actions(event)

    assert all(not action.isEnabled() for action in tree.menu_actions.values())


def test_mainview_history_supported_copy_action_uses_selected_commit(
    qapp, main_context, managed_qobject, monkeypatch
):
    monkeypatch.setattr(CommitHistoryWidget, 'load_if_stale', lambda _history: None)
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    tree = window.historywidget.treewidget
    commit = _commit(main_context, 'selected-oid')
    window.historywidget.apply_result((commit,), _graph((commit,)))
    item = tree.oidmap[commit.oid]
    item.setSelected(True)
    tree.scrollToItem(item)
    qapp.processEvents()
    copied = []
    monkeypatch.setattr(qtutils, 'set_clipboard', copied.append)
    position = tree.visualItemRect(item).center()
    assert tree.itemAt(position) is item
    event = QtGui.QContextMenuEvent(
        QtGui.QContextMenuEvent.Mouse,
        position,
        tree.viewport().mapToGlobal(position),
    )

    tree.update_menu_actions(event)
    assert tree.menu_actions['copy'].isEnabled()
    tree.menu_actions['copy'].trigger()
    qapp.processEvents()

    assert copied == [commit.oid]


def test_mainview_history_context_menu_outside_items_does_not_crash(
    qapp, main_context, managed_qobject, monkeypatch
):
    window = managed_qobject(MainView(main_context))
    tree = window.historywidget.treewidget
    monkeypatch.setattr(QtWidgets.QMenu, 'exec_', lambda *_args: None)
    event = QtGui.QContextMenuEvent(
        QtGui.QContextMenuEvent.Mouse,
        QtCore.QPoint(-1, -1),
        QtCore.QPoint(-1, -1),
    )

    tree.contextMenuEvent(event)

    assert all(not action.isEnabled() for action in tree.menu_actions.values())


def test_successful_initialize_loads_history_once_after_git_check_and_state_restore(
    qapp, main_context, managed_qobject, monkeypatch
):
    order = []

    def restore_state(window, _settings, _callback):
        order.append('restore')
        window.historywidget.set_values('restored', 321, True)

    def git_version(_context):
        order.append('git-check')
        return 'git version test'

    def load_if_stale(history):
        order.append((
            'load',
            history.current_request().ref,
            history.current_request().count,
            history.current_request().display_status,
        ))

    monkeypatch.setattr(MainView, 'init_state', restore_state)
    monkeypatch.setattr('cola.widgets.main.version.git_version_str', git_version)
    monkeypatch.setattr(
        CommitHistoryWidget, 'load_if_stale', load_if_stale, raising=False
    )

    managed_qobject(MainView(main_context))

    # GitDagLineEdit probes the version while constructing its completer; the
    # deferred initialize check is the second probe and must precede loading.
    assert order == ['git-check', 'restore']
    _drain_initialization(qapp)
    assert order == [
        'git-check',
        'restore',
        'git-check',
        ('load', 'restored', 321, True),
    ]


def test_queued_model_update_before_git_check_uses_one_initial_request(
    qapp, main_context, managed_qobject, monkeypatch
):
    ControlledReaderThread.instances = []
    monkeypatch.setattr('cola.widgets.dag.ReaderThread', ControlledReaderThread)
    monkeypatch.setattr(
        'cola.widgets.main.version.git_version_str', lambda _context: 'git version test'
    )
    main_context.model.local_branches = ['main']
    main_context.model.remote_branches = []
    main_context.model.tags = []
    window = managed_qobject(MainView(main_context))

    main_context.model.updated.emit()
    _drain_initialization(qapp)

    assert len(ControlledReaderThread.instances) == 1
    assert window.historywidget.active_thread is ControlledReaderThread.instances[0]
    assert window.historywidget.pending_request is None
    assert window.historywidget.repository_generation == 1


def test_failed_initialize_exits_without_loading_history(
    qapp, main_context, managed_qobject, monkeypatch
):
    loads = []
    exits = []
    monkeypatch.setattr(
        'cola.widgets.main.version.git_version_str', lambda _context: ''
    )
    monkeypatch.setattr(
        'cola.widgets.main.Interaction.critical', lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(main_context.app, 'exit', lambda code: exits.append(code))
    monkeypatch.setattr(
        CommitHistoryWidget,
        'load_if_stale',
        lambda history: loads.append(history),
    )

    managed_qobject(MainView(main_context))
    assert loads == []
    qapp.processEvents()

    assert exits
    assert loads == []


def test_close_before_initial_history_callback_prevents_load(
    qapp, main_context, managed_qobject, monkeypatch
):
    loads = []
    monkeypatch.setattr(
        CommitHistoryWidget,
        'load_if_stale',
        lambda history: loads.append(history.current_request()),
        raising=False,
    )
    main_context.browser_windows = []
    window = managed_qobject(MainView(main_context))

    assert window.close()
    qapp.processEvents()

    assert window.historywidget.stopping
    assert loads == []


def test_queued_model_update_refreshes_hidden_history_through_public_api_once(
    qapp, main_context, managed_qobject, monkeypatch
):
    loads = []
    monkeypatch.setattr(
        CommitHistoryWidget,
        'load_if_stale',
        lambda history: loads.append(history),
        raising=False,
    )
    window = managed_qobject(MainView(main_context))
    _drain_initialization(qapp)
    loads.clear()
    window.historydock.hide()

    main_context.model.updated.emit()
    qapp.processEvents()

    assert loads == [window.historywidget]


def test_refresh_reaches_hidden_history_before_missing_cwd_early_return(
    qapp, main_context, managed_qobject, monkeypatch
):
    loads = []
    monkeypatch.setattr(
        CommitHistoryWidget,
        'load_if_stale',
        lambda history: loads.append(history),
    )
    window = managed_qobject(MainView(main_context))
    _drain_initialization(qapp)
    loads.clear()
    window.historydock.hide()
    monkeypatch.setattr(
        'cola.widgets.main.core.getcwd',
        lambda: (_ for _ in ()).throw(FileNotFoundError()),
    )

    main_context.model.updated.emit()
    qapp.processEvents()

    assert loads == [window.historywidget]


def test_mainview_owns_no_history_reader_or_cache_implementation():
    source = inspect.getsource(MainView)

    for forbidden in (
        'RepoReader',
        'ReaderThread',
        'request_history',
        'historywidget.display(',
        'active_request',
        'pending_request',
        'last_successful_cache_key',
    ):
        assert forbidden not in source


def test_real_mainview_initial_load_and_rescan_show_real_commits_off_gui_thread(
    qapp, main_context, managed_qobject, monkeypatch
):
    def git(*args):
        return subprocess.run(
            ('git', *args), check=True, text=True, capture_output=True
        ).stdout.strip()

    git('commit', '-m', 'initial')
    initial_oid = git('rev-parse', 'HEAD')
    main_context.model.update_status()
    build_threads = []
    real_build_graph = graph_model.build_graph

    def recording_build_graph(graph_input, head_oid=None):
        build_threads.append(threading.get_ident())
        return real_build_graph(list(graph_input), head_oid=head_oid)

    monkeypatch.setattr(graph_model, 'build_graph', recording_build_graph)
    gui_thread = threading.get_ident()
    window, refresh_calls = _main_with_refresh_spy(
        main_context, managed_qobject, monkeypatch
    )
    history = window.historywidget
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        qapp.processEvents()
        if history.active_thread is None and history.commit_list:
            break
        QtTest.QTest.qWait(10)

    assert history.active_thread is None
    assert initial_oid in {commit.oid for commit in history.commit_list}
    assert build_threads and all(thread_id != gui_thread for thread_id in build_threads)
    initial_item = history.treewidget.oidmap[initial_oid]
    assert initial_item.data(0, GRAPH_ROW_ROLE).commit_oid == initial_oid

    with open('after-rescan', 'w', encoding='utf-8') as handle:
        handle.write('changed\n')
    git('add', 'after-rescan')
    git('commit', '-m', 'after rescan')
    final_oid = git('rev-parse', 'HEAD')

    refresh_baseline = len(refresh_calls)
    cmds.do(cmds.Rescan, main_context)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        qapp.processEvents()
        if history.active_thread is None and final_oid in history.commits:
            break
        QtTest.QTest.qWait(10)

    assert len(refresh_calls) > refresh_baseline
    assert final_oid in {commit.oid for commit in history.commit_list}
    final_item = history.treewidget.oidmap[final_oid]
    assert final_item.data(0, GRAPH_ROW_ROLE).commit_oid == final_oid


def test_real_commit_command_refreshes_visible_mainview_history(
    qapp, main_context, managed_qobject, monkeypatch
):
    window, refresh_calls = _main_with_refresh_spy(
        main_context, managed_qobject, monkeypatch
    )
    _wait_for_history(qapp, window)
    updated = QtTest.QSignalSpy(main_context.model.updated)
    refresh_baseline = len(refresh_calls)

    result = cmds.do(cmds.Commit, main_context, False, 'real commit', False)
    oid = _git('rev-parse', 'HEAD')
    assert result is not None and result[0] == 0
    assert _spy_count(updated) == 1
    _wait_for_history(qapp, window, oid)
    assert len(refresh_calls) > refresh_baseline


def test_commit_command_accepts_disabled_status_update(
    main_context, monkeypatch, tmp_path
):
    main_context.timestamp = time.time()
    main_context.git.commit = Mock(return_value=(0, '', ''))
    main_context.model.update_file_status = Mock()
    main_context.model.update_status = Mock()
    monkeypatch.setattr(
        cmds.utils, 'tmp_filename', lambda _name: str(tmp_path / 'message')
    )
    monkeypatch.setattr(cmds.prefs, 'verbose_simple_commands', lambda _context: False)
    monkeypatch.setattr(cmds.main, 'autodetect_proxy_environ', dict)
    command = cmds.Commit(main_context, amend=False, msg='message', sign=False)

    command.do(update_status=False)

    main_context.model.update_file_status.assert_called_once_with()
    main_context.model.update_status.assert_not_called()


def test_failed_commit_emits_no_model_update(qapp, main_context):
    _git('commit', '-m', 'base')
    main_context.model.update_status()
    updated = QtTest.QSignalSpy(main_context.model.updated)

    result = cmds.do(cmds.Commit, main_context, False, 'nothing to commit', False)
    qapp.processEvents()

    assert result is not None and result[0] != 0
    assert _spy_count(updated) == 0


def test_real_checkout_command_refreshes_visible_mainview_history(
    qapp, main_context, managed_qobject, monkeypatch
):
    _git('commit', '-m', 'base')
    original_branch = _git('branch', '--show-current')
    _git('checkout', '-b', 'topic')
    with open('topic-file', 'w', encoding='utf-8') as handle:
        handle.write('topic\n')
    _git('add', 'topic-file')
    _git('commit', '-m', 'topic')
    topic_oid = _git('rev-parse', 'HEAD')
    _git('checkout', original_branch)
    main_context.model.update_status()
    window, refresh_calls = _main_with_refresh_spy(
        main_context, managed_qobject, monkeypatch
    )
    _wait_for_history(qapp, window)
    assert 'HEAD' not in window.historywidget.commits[topic_oid].tags
    updated = QtTest.QSignalSpy(main_context.model.updated)
    refresh_baseline = len(refresh_calls)

    result = cmds.do(cmds.CheckoutBranch, main_context, 'topic')
    _wait_for_head(qapp, window, topic_oid, refresh_calls, refresh_baseline)

    assert result is not None and result[0] == 0
    assert main_context.model.currentbranch == 'topic'
    assert _spy_count(updated) >= 1


def test_real_fetch_refreshes_visible_mainview_history(
    qapp, main_context, managed_qobject, monkeypatch, tmp_path
):
    _git('commit', '-m', 'base')
    branch = _git('branch', '--show-current')
    remote = tmp_path / 'remote.git'
    producer = tmp_path / 'producer'
    _git('init', '--bare', str(remote))
    _git('remote', 'add', 'origin', str(remote))
    _git('push', 'origin', f'HEAD:refs/heads/{branch}')
    _git('clone', '--branch', branch, str(remote), str(producer))
    _git('config', 'user.name', 'Your Name', cwd=producer)
    _git('config', 'user.email', 'you@example.com', cwd=producer)
    (producer / 'remote-file').write_text('remote\n', encoding='utf-8')
    _git('add', 'remote-file', cwd=producer)
    _git('commit', '-m', 'remote commit', cwd=producer)
    remote_oid = _git('rev-parse', 'HEAD', cwd=producer)
    _git('push', 'origin', branch, cwd=producer)
    main_context.model.update_status()
    window, refresh_calls = _main_with_refresh_spy(
        main_context, managed_qobject, monkeypatch
    )
    _wait_for_history(qapp, window)
    assert remote_oid not in window.historywidget.commits
    updated = QtTest.QSignalSpy(main_context.model.updated)
    refresh_baseline = len(refresh_calls)

    result = main_context.model.fetch('origin')
    _wait_for_history(qapp, window, remote_oid)

    assert result[0] == 0
    assert _spy_count(updated) >= 1
    assert len(refresh_calls) > refresh_baseline


def test_real_rescan_command_emits_model_updated_contract(qapp, main_context):
    updated = QtTest.QSignalSpy(main_context.model.updated)

    cmds.do(cmds.Rescan, main_context)
    qapp.processEvents()

    assert _spy_count(updated) >= 1


def test_initial_serialized_result_populates_mainview_graph_rows(
    qapp, main_context, managed_qobject, monkeypatch
):
    oids = ['A']
    window = _controlled_main(qapp, main_context, managed_qobject, monkeypatch, oids)
    thread = ControlledReaderThread.instances[-1]
    assert (
        thread.request.ref,
        thread.request.count,
        thread.request.display_status,
    ) == ('--all', 1000, False)
    assert window.historywidget.treewidget.topLevelItemCount() == 0
    commit = _commit(main_context, 'A')
    graph = _graph((commit,))

    thread.complete(
        dag_model.HistoryResult(thread.request.run_id, True, 0, '', (commit,), graph)
    )
    qapp.processEvents()

    tree = window.historywidget.treewidget
    assert tree.topLevelItemCount() == 1
    assert tree.topLevelItem(0).data(0, GRAPH_ROW_ROLE) == graph.rows[0]
    assert [item.oid for item in window.historywidget.commit_list] == ['A']


def test_mode_change_plus_model_update_starts_exactly_one_history_reader(
    qapp, main_context, managed_qobject, monkeypatch
):
    window = _controlled_main(qapp, main_context, managed_qobject, monkeypatch, ['A'])
    history = window.historywidget
    first = ControlledReaderThread.instances[0]
    first.complete(
        dag_model.HistoryResult(first.request.run_id, True, 0, '', (), _graph(()))
    )
    qapp.processEvents()
    assert history.active_thread is None

    main_context.model.mode_changed.emit(main_context.model.mode_none)
    main_context.model.updated.emit()
    qapp.processEvents()

    assert len(ControlledReaderThread.instances) == 2
    assert history.active_thread is ControlledReaderThread.instances[1]
    assert history.pending_request is None


def test_mainview_refresh_deduplicates_and_coalesces_last_metadata_snapshot(
    qapp, main_context, managed_qobject, monkeypatch
):
    oids = ['A']
    window = _controlled_main(qapp, main_context, managed_qobject, monkeypatch, oids)
    history = window.historywidget
    first = ControlledReaderThread.instances[-1]
    window.historydock.hide()

    main_context.model.updated.emit()
    qapp.processEvents()
    assert len(ControlledReaderThread.instances) == 1
    first_pending = history.pending_request
    assert first_pending is not None
    assert history.pending_cache_metadata.generation == 2

    history.display()
    assert history.pending_request is first_pending

    oids[:] = ['B']
    main_context.model.local_branches = ['branch-b']
    main_context.model.updated.emit()
    qapp.processEvents()
    assert history.pending_cache_metadata.refs == frozenset({'branch-b'})
    assert history.pending_cache_metadata.generation == 3

    oids[:] = ['C']
    main_context.model.local_branches = ['branch-c']
    main_context.model.updated.emit()
    qapp.processEvents()
    assert len(ControlledReaderThread.instances) == 1
    assert history.pending_cache_metadata.refs == frozenset({'branch-c'})
    assert history.pending_cache_metadata.generation == 4
    pending = history.pending_request

    history.display()
    assert len(ControlledReaderThread.instances) == 1
    assert history.pending_request is pending

    first.complete(dag_model.HistoryResult(first.request.run_id, True, 0, '', (), None))
    qapp.processEvents()
    final = ControlledReaderThread.instances[-1]
    assert final is not first
    commit = _commit(main_context, 'C')
    graph = _graph((commit,))
    final.complete(
        dag_model.HistoryResult(final.request.run_id, True, 0, '', (commit,), graph)
    )
    qapp.processEvents()

    tree = history.treewidget
    assert [item.oid for item in history.commit_list] == ['C']
    assert tree.topLevelItem(0).data(0, GRAPH_ROW_ROLE) == graph.rows[0]


def test_mainview_failure_preserves_tree_then_success_and_empty_replace_atomically(
    qapp, main_context, managed_qobject, monkeypatch
):
    oids = ['A']
    window = _controlled_main(qapp, main_context, managed_qobject, monkeypatch, oids)
    history = window.historywidget
    initial = ControlledReaderThread.instances[-1]
    commit_a = _commit(main_context, 'A')
    graph_a = _graph((commit_a,))
    initial.complete(
        dag_model.HistoryResult(
            initial.request.run_id, True, 0, '', (commit_a,), graph_a
        )
    )
    qapp.processEvents()
    selected = list(history.selection)

    oids[:] = ['bad']
    main_context.model.updated.emit()
    qapp.processEvents()
    failed = ControlledReaderThread.instances[-1]
    failed.result.emit(
        dag_model.HistoryResult(
            failed.request.run_id, False, 128, 'fatal: exact', (), None
        )
    )
    qapp.processEvents()

    assert [commit.oid for commit in history.commit_list] == ['A']
    assert history.selection == selected
    assert history.error_status == 'returncode 128: fatal: exact'
    assert not history.history_error_status.isHidden()
    assert history.history_error_status.text() == 'returncode 128: fatal: exact'

    oids[:] = ['C']
    main_context.model.updated.emit()
    qapp.processEvents()
    assert history.pending_request is not None
    failed.finish()
    qapp.processEvents()
    success = ControlledReaderThread.instances[-1]
    commit_c = _commit(main_context, 'C')
    graph_c = _graph((commit_c,))
    success.complete(
        dag_model.HistoryResult(
            success.request.run_id, True, 0, '', (commit_c,), graph_c
        )
    )
    qapp.processEvents()

    assert history.error_status is None
    assert [commit.oid for commit in history.commit_list] == ['C']
    assert history.treewidget.topLevelItem(0).data(0, GRAPH_ROW_ROLE) == graph_c.rows[0]

    oids[:] = []
    main_context.model.updated.emit()
    qapp.processEvents()
    empty = ControlledReaderThread.instances[-1]
    empty.complete(dag_model.HistoryResult(empty.request.run_id, True, 0, '', (), None))
    qapp.processEvents()

    assert history.treewidget.topLevelItemCount() == 0
    assert history.commit_list == []
    assert history.selection == []


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
    history.set_values('main --', 321, True)
    history.display_inline_graph_action.setChecked(True)
    history.treewidget.display_inline_graph(True)
    history.treewidget.set_column_widths([211, 122])

    state = window.export_state()

    assert state['show_history'] is (not window.historydock.isHidden())
    assert (
        state['history_inline_graph_default_version']
        == HISTORY_INLINE_GRAPH_DEFAULT_VERSION
        == 1
    )
    assert set(state['history']) == HISTORY_KEYS
    assert state['history'] == history.export_state()
    # files_sizes is excluded from the hardcoded comparison because it depends
    # on the live splitter geometry.
    history_state = dict(state['history'])
    history_state.pop('files_sizes', None)
    assert history_state == {
        'ref': 'main --',
        'count': 321,
        'display_inline_graph': True,
        'display_status': True,
        'display_files': False,
        'log': {'column_widths': [211, 122]},
    }
    assert HISTORY_KEYS.isdisjoint(state.keys())

    restored = managed_qobject(MainView(main_context))
    _show(qapp, restored)
    assert restored.apply_state(state)
    assert restored.historywidget.export_state() == state['history']


def test_export_history_visibility_is_independent_of_hidden_parent(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))

    assert window.isVisible() is False
    assert window.export_state()['show_history'] is True

    window.historydock.hide()

    assert window.export_state()['show_history'] is False


@pytest.mark.parametrize('history_state', [None, [], {'count': 'bad'}])
def test_malformed_history_state_returns_false_without_partial_hide(
    qapp, main_context, managed_qobject, history_state
):
    window = managed_qobject(MainView(main_context))
    state = _legacy_v2_state(window)
    state['history'] = history_state
    state['show_history'] = False
    _show(qapp, window)
    _wait_for_history(qapp, window)
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
    _wait_for_history(qapp, window)
    window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, window.statusdock)
    window.set_lock_layout(False)
    window.lock_layout_action.setChecked(False)
    window.statuswidget.filter_widget.hide()
    window.model.set_ref_sort(0)
    # files_sizes depends on the live splitter geometry and is therefore
    # excluded from the atomic-rejection assertion.
    before_history = window.historywidget.export_state()
    before_history.pop('files_sizes', None)

    state = _legacy_v2_state(window)
    state.update(
        history={'ref': 'mutated', 'count': 'bad'},
        show_history=False,
        lock_layout=True,
        show_status_filter=True,
        ref_sort=1,
    )

    assert window.apply_state(state) is False
    qapp.processEvents()

    after_history = window.historywidget.export_state()
    after_history.pop('files_sizes', None)
    assert window.dockWidgetArea(window.statusdock) == QtCore.Qt.LeftDockWidgetArea
    assert window.lock_layout is False
    assert window.lock_layout_action.isChecked() is False
    assert window.statuswidget.filter_widget.isVisible() is False
    assert window.model.ref_sort == 0
    assert after_history == before_history
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
    # Exclude files_sizes because the live splitter geometry can shift as a
    # side effect of apply_state setting dock visibility.
    defaults = window.historywidget.export_state()
    defaults.pop('files_sizes', None)

    assert window.apply_state(state)
    after = window.historywidget.export_state()
    after.pop('files_sizes', None)
    assert after == defaults
    assert window.historydock.isVisible()
    assert _history_is_active(window.historydock)


@pytest.mark.parametrize('marker', (None, 0))
def test_old_mainview_false_inline_graph_state_is_migrated_without_mutating_input(
    marker, qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    state = _legacy_v2_state(window)
    state['history'] = window.historywidget.export_state()
    state['history']['display_inline_graph'] = False
    if marker is not None:
        state['history_inline_graph_default_version'] = marker
    original_history = dict(state['history'])

    assert window.apply_state(state)

    assert state['history'] == original_history
    assert window.historywidget.display_inline_graph_action.isChecked() is True
    assert (
        window.historywidget.treewidget.itemDelegateForColumn(0)
        is window.historywidget.treewidget.graph_delegate
    )


def test_current_mainview_inline_graph_false_state_round_trips_without_migration(
    qapp, main_context, managed_qobject
):
    first = managed_qobject(MainView(main_context))
    first.historywidget.display_inline_graph_action.trigger()
    state = first.export_state()
    second = managed_qobject(MainView(main_context))

    assert state['history_inline_graph_default_version'] == 1
    assert state['history']['display_inline_graph'] is False
    assert second.apply_state(state)
    assert second.historywidget.display_inline_graph_action.isChecked() is False
    assert second.historywidget.treewidget.itemDelegateForColumn(0) is None
    assert second.export_state()['history']['display_inline_graph'] is False


@pytest.mark.parametrize('marker', (True, False, None, '1', -1))
def test_malformed_inline_graph_migration_marker_is_rejected_atomically(
    marker, qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    window.statuswidget.filter_widget.hide()
    before = window.historywidget.export_state()
    state = _legacy_v2_state(window)
    state.update(
        history=window.historywidget.export_state(),
        history_inline_graph_default_version=marker,
        show_status_filter=True,
    )

    assert window.apply_state(state) is False

    assert window.statuswidget.filter_widget.isVisible() is False
    assert window.historywidget.export_state() == before


def test_future_inline_graph_marker_restores_compatible_state_without_migration(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    state = _legacy_v2_state(window)
    state.update(
        history=window.historywidget.export_state(),
        history_inline_graph_default_version=2,
        show_status_filter=True,
    )
    state['history']['display_inline_graph'] = False
    original = {**state, 'history': dict(state['history'])}

    assert window.apply_state(state)

    assert state == original
    assert window.statuswidget.filter_widget.isVisible() is True
    assert window.historywidget.display_inline_graph_action.isChecked() is False
    assert window.historywidget.treewidget.itemDelegateForColumn(0) is None


@pytest.mark.parametrize('state', [None, [], 'invalid'])
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
    assert window.historywidget.current_request().ref == '--all'


def test_invalid_qt_state_returns_false_and_reveals_default_history(
    qapp, main_context, managed_qobject
):
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    state = window.export_state()
    state['windowstate'] = 'not-a-valid-qt-state'
    state['show_history'] = False
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
    inline_graph = window.historywidget.display_inline_graph_action

    window.build_view_menu(window.view_menu)
    qapp.processEvents()

    dynamic_toolbar = QtWidgets.QToolBar('Dynamic Toolbar', window)
    dynamic_toolbar.setObjectName('DynamicToolbar')
    dynamic_toolbar.addAction('Dynamic Action')
    window.addToolBar(dynamic_toolbar)
    dynamic_toggle = dynamic_toolbar.toggleViewAction()

    for _ in range(2):
        window.build_view_menu(window.view_menu)
        qapp.processEvents()
        actions = window.view_menu.actions()
        assert [action for action in actions if action is history_toggle] == [
            history_toggle
        ]
        assert [action for action in actions if action is inline_graph] == [
            inline_graph
        ]
        assert inline_graph.isChecked() is True
        assert [action for action in actions if action is dynamic_toggle] == [
            dynamic_toggle
        ]
        assert sum(action.text() == dynamic_toggle.text() for action in actions) == 1

    assert [action for action in window.actions() if action is history_toggle] == [
        history_toggle
    ]

    inline_graph.trigger()
    qapp.processEvents()
    assert inline_graph.isChecked() is False
    assert window.historywidget.treewidget.itemDelegateForColumn(0) is None
    inline_graph.trigger()
    qapp.processEvents()
    assert inline_graph.isChecked() is True
    assert (
        window.historywidget.treewidget.itemDelegateForColumn(0)
        is window.historywidget.treewidget.graph_delegate
    )


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
        error = ''

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

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', BlockingReader)
    main_context.browser_windows = []
    window = managed_qobject(MainView(main_context))
    history = window.historywidget
    assert history.request_history('active', 10, False)
    assert entered.wait(2)
    assert history.request_history('pending', 20, True)
    active_thread = history.active_thread

    order = []
    real_close_popup = history.close_popup
    real_stop_and_wait = history.stop_and_wait
    real_standard_close = standard.MainWindow.closeEvent

    def close_popup():
        order.append('popup')
        real_close_popup()

    def stop_and_wait():
        order.append('stop')
        real_stop_and_wait()

    def standard_close(self, event):
        if self is window:
            order.append('standard')
        return real_standard_close(self, event)

    monkeypatch.setattr(history, 'close_popup', close_popup)
    monkeypatch.setattr(history, 'stop_and_wait', stop_and_wait)
    monkeypatch.setattr(standard.MainWindow, 'closeEvent', standard_close)

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
            frozen['accepted'] = window.close()
            frozen['exited'] = exited.is_set()
            frozen['running'] = active_thread.isRunning()
            frozen['pending'] = history.pending_request
            frozen['active'] = history.active_thread
            frozen['order'] = list(order)
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
        'accepted': True,
        'exited': True,
        'running': False,
        'pending': None,
        'active': None,
        'order': ['popup', 'stop', 'standard'],
    }
    assert helper_observations == [True]
    assert interrupted_at_exit == [True]
    assert len(constructed) == 1

    order.clear()
    assert window.close()
    assert order == ['popup', 'stop', 'standard']
