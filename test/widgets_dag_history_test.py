# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Characterization tests for the existing DAG history widgets."""

import sys
import threading
import time
from typing import ClassVar

import pytest

from cola import dag as dag_cli
from cola import main as main_cli
from cola.interaction import Interaction
from cola.models import dag
from cola.models import graph as graph_model
from cola.widgets import standard
from cola.widgets.dag import COMMIT_ROLE
from cola.widgets.dag import GRAPH_PREV_ROW_ROLE
from cola.widgets.dag import GRAPH_ROW_ROLE
from cola.widgets.dag import CommitHistoryWidget
from cola.widgets.dag import CommitTreeWidget
from cola.widgets.dag import CommitTreeWidgetItem
from cola.widgets.dag import EdgeColor
from cola.widgets.dag import GitDAG
from cola.widgets.dag import GraphDelegate
from cola.widgets.dag import ReaderThread
from cola.widgets.dag import _best_contrast
from cola.widgets.dag import _HistoryCacheMetadata
from cola.widgets.dag import _opaque_color
from cola.widgets.dag import inline_graph_style
from cola.widgets.main import MainView
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtTest
from qtpy import QtWidgets

from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


# Captured from QMainWindow.saveState(version=2) for MainView's existing v2 dock
# set. Its contract is limited to restoring those existing docks; it deliberately
# says nothing about a future history dock.
LEGACY_MAINVIEW_V2_WINDOWSTATE = 'AAAA/wAAAAL9AAAAAgAAAAIAAAKAAAAA7vwBAAAAA/sAAAAMAFMAdABhAHQAdQBz' 'AQAAAAAAAADRAAAAXAAAAN77AAAADABDAG8AbQBtAGkAdAEAAADXAAAA0gAAAEoA' '/////AAAAa8AAADRAAAAggD////6AAAAAAEAAAAE+wAAABAAQgByAGEAbgBjAGgA' 'ZQBzAQAAAAD/////AAAAggD////7AAAAFABTAHUAYgBtAG8AZAB1AGwAZQBzAQAA' 'AAD/////AAAAbAD////7AAAAEgBGAGEAdgBvAHIAaQB0AGUAcwAAAAAA/////wAA' 'AFYA////+wAAAAwAUgBlAGMAZQBuAHQAAAAAAP////8AAABIAP///wAAAAMAAAKA' 'AAAA2fwBAAAAAvsAAAAIAEQAaQBmAGYBAAAAAAAAAoAAAABGAP////wAAAAA////' '/wAAAAAA////+v////8BAAAAAvsAAAAOAEEAYwB0AGkAbwBuAHMAAAAAAP////8A' 'AABLAP////sAAAAOAEMAbwBuAHMAbwBsAGUAAAAAAP////8AAAATAP///wAAAoAA' 'AAAAAAAABAAAAAQAAAAIAAAACPwAAAAA'


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for offscreen widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
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
            else getattr(obj, 'active_thread', None)
        )
        if isinstance(thread, QtCore.QThread) and thread.isRunning():
            thread.requestInterruption()
            assert thread.wait(5000)
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


def _commit(context, factory, oid, parents=()):
    commit = dag.Commit(context, factory, oid=oid)
    commit.summary = f'commit {oid}'
    commit.author = 'A U Thor'
    commit.authdate = '2026-07-28'
    commit.parents = list(parents)
    commit.generation = max((parent.generation for parent in parents), default=-1) + 1
    for parent in parents:
        parent.children.append(commit)
    return commit


def _graph_result(commits):
    commits = list(commits)
    head_oid = next((commit.oid for commit in commits if 'HEAD' in commit.tags), None)
    return graph_model.build_graph(
        [(commit.oid, [parent.oid for parent in commit.parents]) for commit in commits],
        head_oid=head_oid,
    )


def _tree(app_context, managed_qobject):
    return managed_qobject(CommitTreeWidget(app_context, None))


def _spy_count(spy):
    if hasattr(spy, '__len__'):
        return len(spy)
    return spy.count()


def _spy_payload(spy, index):
    if hasattr(spy, '__getitem__'):
        return spy[index]
    return spy.at(index)


def test_history_widget_uses_all_refs_without_status(
    qapp, app_context, managed_qobject
):
    history = managed_qobject(
        CommitHistoryWidget(app_context, ref='--all', count=1000, display_status=False)
    )

    request = history.current_request()

    assert (request.ref, request.count, request.display_status) == (
        '--all',
        1000,
        False,
    )


def test_load_if_stale_advances_generation_and_never_parses_refs_on_gui_thread(
    qapp, app_context, managed_qobject, monkeypatch
):
    history = _history(app_context, managed_qobject, monkeypatch)
    gui_thread = QtCore.QThread.currentThread()
    parse_calls = []

    def forbidden_parse_refs(*_args):
        parse_calls.append(QtCore.QThread.currentThread())
        raise AssertionError('history refresh must not resolve refs on the GUI thread')

    monkeypatch.setattr('cola.gitcmds.parse_refs', forbidden_parse_refs)

    history.load_if_stale()
    first_generation = history.active_cache_metadata.generation
    history.display()
    history.model_updated()

    assert QtCore.QThread.currentThread() is gui_thread
    assert parse_calls == []
    assert first_generation == 1
    assert history.pending_cache_metadata.generation == 2


def test_current_request_is_a_pure_snapshot(qapp, app_context, managed_qobject):
    history = managed_qobject(CommitHistoryWidget(app_context))
    next_run_id = history._next_run_id

    first = history.current_request()
    second = history.current_request()

    assert first == second
    assert first.run_id == next_run_id
    assert history._next_run_id == next_run_id


def test_accepted_requests_alone_consume_run_ids_for_both_paths(
    qapp, app_context, managed_qobject, monkeypatch
):
    history = _history(app_context, managed_qobject, monkeypatch)

    assert history.request_history()
    active = ManualReaderThread.instances[-1]
    assert active.request.run_id == 1
    assert history._next_run_id == 2

    assert not history.request_history()
    assert history._next_run_id == 2

    assert history.request_history('pending', 20, True)
    pending = history.pending_request
    assert pending.run_id == 2
    assert history._next_run_id == 3

    assert not history.request_history('pending', 20, True)
    assert history.pending_request is pending
    assert history._next_run_id == 3


def test_history_widget_owns_history_state_without_window_children(
    qapp, app_context, managed_qobject
):
    history = managed_qobject(CommitHistoryWidget(app_context))

    for name in (
        'revtext',
        'maxresults',
        'display_inline_graph_action',
        'display_status_action',
        'history_error_status',
        'treewidget',
        'active_thread',
        'pending_request',
        'commit_list',
        'commits',
        'selection',
        'last_successful_cache_key',
    ):
        assert hasattr(history, name), name
    for name in (
        'graphview',
        'diffwidget',
        'filewidget',
        'log_dock',
        'diff_dock',
        'file_dock',
        'graphview_dock',
    ):
        assert not hasattr(history, name), name
    assert history.findChildren(QtWidgets.QDockWidget) == []


def test_two_history_widgets_have_independent_state(
    qapp, app_context, managed_qobject, monkeypatch
):
    ManualReaderThread.instances = []
    monkeypatch.setattr('cola.widgets.dag.ReaderThread', ManualReaderThread)
    first = CommitHistoryWidget(app_context, ref='one', count=1)
    second = managed_qobject(CommitHistoryWidget(app_context, ref='two', count=2))
    factory = dag.CommitFactory()
    first_commit = _commit(app_context, factory, 'first')
    second_commit = _commit(app_context, factory, 'second')

    assert first.request_history('first-active', 1, False)
    first_thread = first.active_thread
    assert first.request_history('first-pending', 2, True)
    first_pending = first.pending_request
    assert second.request_history('second-active', 3, False)
    second_thread = second.active_thread
    second_thread.complete(
        dag.HistoryResult(
            second_thread.request.run_id,
            True,
            0,
            '',
            (second_commit,),
            _graph_result((second_commit,)),
        )
    )
    qapp.processEvents()

    assert first_thread is not second_thread
    assert first.active_request is first_thread.request
    assert second.active_request is None
    assert first.pending_request is first_pending
    assert second.pending_request is None
    assert first.last_successful_cache_key is None
    assert second.last_successful_cache_key == ('second-active', 3, False)
    assert first.selection == []
    assert second.selection == [second_commit]
    assert first.treewidget.topLevelItemCount() == 0
    assert second.treewidget.topLevelItemCount() == 1

    first.stop_and_wait()
    first.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(first, QtCore.QEvent.DeferredDelete)

    assert first_thread.interrupted and first_thread.waited
    assert second.commit_list == [second_commit]
    assert second.selection == [second_commit]
    assert second.treewidget.topLevelItemCount() == 1
    assert second.last_successful_cache_key == ('second-active', 3, False)
    second.apply_result((first_commit,), _graph_result((first_commit,)))
    assert second.commit_list == [first_commit]
    second.stop_and_wait()


def test_gitdag_composes_history_with_window_only_views(
    qapp, app_context, managed_qobject
):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    window = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))

    assert isinstance(window.historywidget, CommitHistoryWidget)
    assert window.log_dock.widget() is window.historywidget
    assert isinstance(window.graphview, QtWidgets.QGraphicsView)
    assert window.diffwidget is not None
    assert window.filewidget is not None
    assert window.historywidget.display_inline_graph_action.isChecked() is False
    assert window.historywidget.treewidget.itemDelegateForColumn(0) is None
    assert len(window.historywidget.treewidget.menu_actions) == 24
    assert len(set(window.historywidget.treewidget.menu_actions.values())) == 24
    for name in (
        'active_thread',
        'pending_request',
        'commit_list',
        'commits',
        'selection',
        'last_successful_cache_key',
    ):
        assert not hasattr(window, name), name


def test_gitdag_window_owns_docks_graph_diff_and_files(
    qapp, app_context, managed_qobject
):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    window = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))

    assert window.log_dock.parent() is window
    assert window.graphview_dock.parent() is window
    assert window.diff_dock.parent() is window
    assert window.file_dock.parent() is window
    assert window.log_dock.widget() is window.historywidget
    assert window.graphview_dock.widget() is window.graphview
    assert window.diff_dock.widget() is window.diff_panel
    assert window.file_dock.widget() is window.filewidget
    assert window.historywidget.findChildren(QtWidgets.QDockWidget) == []


def test_public_apply_result_updates_standalone_views_synchronously(
    qapp, app_context, managed_qobject, monkeypatch
):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    monkeypatch.setattr(
        app_context.git,
        'show',
        lambda *_args, **_kwargs: (0, '1\t0\ttracked.txt\0', ''),
    )
    window = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))
    history = window.historywidget
    factory = dag.CommitFactory()
    root = _commit(app_context, factory, 'root')
    tip = _commit(app_context, factory, 'tip', (root,))
    loaded = QtTest.QSignalSpy(history.commits_loaded)
    selected = QtTest.QSignalSpy(window.commits_selected)

    history.apply_result((root, tip), _graph_result((root, tip)))

    assert _spy_count(loaded) == 1
    assert list(_spy_payload(loaded, 0)[0]) == [root, tip]
    assert _spy_count(selected) == 1
    assert list(_spy_payload(selected, 0)[0]) == [tip]
    assert window.graphview.commits == [root, tip]
    assert set(window.graphview.items) == {'root', 'tip'}
    assert [item.commit for item in window.graphview.selected_items()] == [tip]
    assert window.diffwidget.oid == 'tip'
    assert window.filewidget.topLevelItemCount() == 1
    assert window.diffwidget_copy_commit.isEnabled()


def test_public_selection_reaches_all_standalone_consumers_synchronously(
    qapp, app_context, managed_qobject, monkeypatch
):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    show_calls = []
    monkeypatch.setattr(
        app_context.git,
        'show',
        lambda *args, **kwargs: (
            show_calls.append((args, kwargs)) or (0, '2\t1\tchosen.txt\0', '')
        ),
    )
    window = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))
    history = window.historywidget
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'chosen')
    history.apply_result((commit,), _graph_result((commit,)))
    show_calls.clear()

    history.select_commits([commit])

    assert history.selection == [commit]
    assert [item.commit for item in history.treewidget.selected_items()] == [commit]
    assert [item.commit for item in window.graphview.selected_items()] == [commit]
    assert window.diffwidget.oid == 'chosen'
    assert window.filewidget.topLevelItemCount() == 1
    assert len(show_calls) == 1
    assert window.diffwidget_copy_commit.isEnabled()


def test_empty_public_apply_clears_standalone_graph_and_selection(
    qapp, app_context, managed_qobject, monkeypatch
):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    monkeypatch.setattr(
        app_context.git,
        'show',
        lambda *_args, **_kwargs: (0, '1\t0\ttracked.txt\0', ''),
    )
    window = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))
    history = window.historywidget
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'old')
    history.apply_result((commit,), _graph_result((commit,)))
    selected = QtTest.QSignalSpy(window.commits_selected)

    history.apply_result((), graph_model.GraphResult([], 0))

    assert window.graphview.commits == []
    assert window.graphview.items == {}
    assert window.graphview.selected_items() == []
    assert window.diffwidget.oid is None
    assert window.filewidget.topLevelItemCount() == 0
    assert not window.diffwidget_copy_commit.isEnabled()
    assert _spy_count(selected) == 1
    assert list(_spy_payload(selected, 0)[0]) == []


@pytest.mark.parametrize('outcome', ['failure', 'stale'])
def test_failed_or_stale_result_preserves_all_standalone_views(
    outcome, qapp, app_context, managed_qobject, monkeypatch
):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    monkeypatch.setattr(
        app_context.git, 'show', lambda *_args, **_kwargs: (0, '1\t0\told.txt\0', '')
    )
    ManualReaderThread.instances = []
    monkeypatch.setattr('cola.widgets.dag.ReaderThread', ManualReaderThread)
    window = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))
    history = window.historywidget
    factory = dag.CommitFactory()
    old = _commit(app_context, factory, 'old')
    replacement = _commit(app_context, factory, 'replacement')
    history.apply_result((old,), _graph_result((old,)))
    before = (
        list(window.graphview.commits),
        dict(window.graphview.items),
        [item.commit for item in window.graphview.selected_items()],
        window.diffwidget.oid,
        window.filewidget.topLevelItemCount(),
        list(history.selection),
    )
    assert history.request_history('next', 10, False)
    active = history.active_thread
    result = dag.HistoryResult(
        active.request.run_id + (1 if outcome == 'stale' else 0),
        outcome != 'failure',
        128 if outcome == 'failure' else 0,
        'fatal' if outcome == 'failure' else '',
        (replacement,),
        _graph_result((replacement,)),
    )

    history.thread_result(result)

    assert (
        list(window.graphview.commits),
        dict(window.graphview.items),
        [item.commit for item in window.graphview.selected_items()],
        window.diffwidget.oid,
        window.filewidget.topLevelItemCount(),
        list(history.selection),
    ) == before


def test_gitdag_close_delegates_stop_to_history_widget(
    qapp, app_context, managed_qobject, monkeypatch
):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    calls = []
    monkeypatch.setattr(
        CommitHistoryWidget,
        'stop_and_wait',
        lambda self: calls.append(self),
        raising=False,
    )
    window = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))

    assert window.close()

    assert calls == [window.historywidget]


def _palette(window, window_text, base, alternate, highlight, highlighted_text):
    palette = QtGui.QPalette()
    for role, color in (
        (QtGui.QPalette.Window, window),
        (QtGui.QPalette.WindowText, window_text),
        (QtGui.QPalette.Base, base),
        (QtGui.QPalette.AlternateBase, alternate),
        (QtGui.QPalette.Text, window_text),
        (QtGui.QPalette.Button, alternate),
        (QtGui.QPalette.ButtonText, window_text),
        (QtGui.QPalette.Highlight, highlight),
        (QtGui.QPalette.HighlightedText, highlighted_text),
    ):
        palette.setColor(role, QtGui.QColor(color))
    return palette


def _contrast(first, second):
    def luminance(color):
        channels = []
        for value in (color.redF(), color.greenF(), color.blueF()):
            channels.append(
                value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            )
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize(
    'palette',
    [
        _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff'),
        _palette('#202328', '#e8eaed', '#17191d', '#292d33', '#6ea8fe', '#101216'),
    ],
)
def test_inline_graph_style_is_palette_derived_distinct_and_repeatable(palette):
    first = inline_graph_style(palette)
    second = inline_graph_style(QtGui.QPalette(palette))

    assert first == second
    assert first is not second
    with pytest.raises(AttributeError):
        first.normal_fill = QtGui.QColor('#000000')
    assert len(first.lane_colors) >= 4
    assert len({color.rgba() for color in first.lane_colors}) == len(first.lane_colors)
    assert (
        len({first.normal_fill.rgba(), first.merge_fill.rgba(), first.head_fill.rgba()})
        == 3
    )
    assert first.head_accent != first.head_fill
    for color in (
        first.normal_fill,
        first.merge_fill,
        first.head_fill,
        first.head_accent,
        first.outline,
        first.text,
        first.chip_text,
        *first.lane_colors,
    ):
        assert color.isValid()
    backgrounds = (
        palette.base().color(),
        palette.alternateBase().color(),
        palette.highlight().color(),
    )
    for color in first.lane_colors:
        assert min(_contrast(color, background) for background in backgrounds) >= 1.6


def test_lane_colors_handle_adversarial_achromatic_palette():
    palette = _palette('#000000', '#c0c0c0', '#000000', '#404040', '#808080', '#000000')

    lanes = inline_graph_style(palette).lane_colors

    assert len(lanes) == 5
    assert all(color.isValid() for color in lanes)
    assert len({color.rgba() for color in lanes}) == 5
    backgrounds = (
        palette.base().color(),
        palette.alternateBase().color(),
        palette.highlight().color(),
    )
    assert all(
        min(_contrast(color, background) for background in backgrounds) >= 1.6
        for color in lanes
    )


def test_lane_colors_expand_fully_collapsed_palette_to_distinct_strong_colors():
    palette = _palette('#000000', '#000000', '#000000', '#000000', '#000000', '#000000')

    lanes = inline_graph_style(palette).lane_colors

    assert len(lanes) == 5
    assert all(color.isValid() for color in lanes)
    assert len({color.rgba() for color in lanes}) == 5
    assert all(_contrast(color, palette.base().color()) >= 4.5 for color in lanes)


def test_lane_colors_expand_fully_collapsed_white_palette():
    palette = _palette('#ffffff', '#ffffff', '#ffffff', '#ffffff', '#ffffff', '#ffffff')

    lanes = inline_graph_style(palette).lane_colors
    backgrounds = (
        palette.base().color(),
        palette.alternateBase().color(),
        palette.highlight().color(),
    )

    assert len(lanes) == 5
    assert all(color.isValid() and color.alpha() == 255 for color in lanes)
    assert len({color.rgba() for color in lanes}) == 5
    assert all(
        min(_contrast(color, background) for background in backgrounds) >= 1.6
        for color in lanes
    )


def test_lane_colors_from_transparent_roles_are_opaque_visible_and_distinct():
    palette = QtGui.QPalette()
    role_colors = (
        (QtGui.QPalette.Base, QtGui.QColor(255, 255, 255, 0)),
        (QtGui.QPalette.AlternateBase, QtGui.QColor(128, 128, 128, 0)),
        (QtGui.QPalette.Highlight, QtGui.QColor(0, 0, 0, 0)),
        (QtGui.QPalette.Text, QtGui.QColor(255, 0, 0, 0)),
        (QtGui.QPalette.HighlightedText, QtGui.QColor(0, 0, 255, 0)),
    )
    for role, color in role_colors:
        palette.setColor(role, color)

    style = inline_graph_style(palette)
    lanes = style.lane_colors
    white = QtGui.QColor(255, 255, 255)

    assert style.selected_text.isValid()
    assert style.selected_text.alpha() == 255
    assert len(lanes) == 5
    assert all(color.isValid() and color.alphaF() == 1.0 for color in lanes)
    assert len({color.rgba() for color in lanes}) == 5
    assert all(_contrast(color, white) >= 1.6 for color in lanes)


def test_inline_graph_style_changes_with_palette_and_ignores_global_edge_colors(
    monkeypatch,
):
    light = _palette('#ffffff', '#191919', '#ffffff', '#eeeeee', '#2468a2', '#ffffff')
    changed = QtGui.QPalette(light)
    changed.setColor(QtGui.QPalette.Highlight, QtGui.QColor('#a23872'))
    expected = inline_graph_style(light)
    empty = []
    monkeypatch.setattr(EdgeColor, 'colors', empty)
    assert inline_graph_style(light) == expected
    assert EdgeColor.colors is empty
    assert empty == []
    replacement = [QtGui.QColor('#010203')]
    monkeypatch.setattr(EdgeColor, 'colors', replacement)
    assert inline_graph_style(light) == expected
    assert EdgeColor.colors is replacement
    assert replacement == [QtGui.QColor('#010203')]
    assert inline_graph_style(changed) != expected


def _paint_graph_row(tree, row_color, palette, selected=False):
    item = tree.topLevelItem(0)
    item.data(0, GRAPH_ROW_ROLE).color = row_color
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = QtCore.QRect(0, 0, 240, 26)
    option.palette = QtGui.QPalette(palette)
    option.font = tree.font()
    option.fontMetrics = QtGui.QFontMetrics(option.font)
    if selected:
        option.state |= QtWidgets.QStyle.State_Selected
    image = QtGui.QImage(option.rect.size(), QtGui.QImage.Format_ARGB32)
    image.fill(palette.base().color())
    painter = QtGui.QPainter(image)
    tree.graph_delegate.paint(painter, option, tree.indexFromItem(item, 0))
    painter.end()
    return image


_SEMANTIC_PAINT_SCENARIOS = (
    ('linear', [('root', []), ('tip', ['root'])], None),
    ('fork', [('root', []), ('left', ['root']), ('right', ['root'])], None),
    (
        'merge',
        [
            ('root', []),
            ('left', ['root']),
            ('right', ['root']),
            ('merge', ['left', 'right']),
        ],
        None,
    ),
    ('HEAD', [('root', []), ('tip', ['root'])], 'tip'),
)

# This oracle is deliberately independent of build_graph(). A paint test must fail
# when graph construction drops or rewrites a segment, rather than merely painting
# whatever topology the builder happens to return.
_SEMANTIC_TOPOLOGY_ORACLE = {
    'linear': (
        ('tip', 0, graph_model.GraphRowColor.NORMAL, ((0, 0, 0),)),
        ('root', 0, graph_model.GraphRowColor.NORMAL, ()),
    ),
    'fork': (
        ('right', 0, graph_model.GraphRowColor.NORMAL, ((0, 0, 0),)),
        (
            'left',
            1,
            graph_model.GraphRowColor.NORMAL,
            ((0, 0, 0), (1, 0, 0)),
        ),
        ('root', 0, graph_model.GraphRowColor.NORMAL, ()),
    ),
    'merge': (
        (
            'merge',
            0,
            graph_model.GraphRowColor.MERGE,
            ((0, 0, 0), (0, 1, 1)),
        ),
        (
            'right',
            1,
            graph_model.GraphRowColor.NORMAL,
            ((0, 0, 0), (1, 1, 1)),
        ),
        (
            'left',
            0,
            graph_model.GraphRowColor.NORMAL,
            ((1, 1, 1), (0, 1, 1)),
        ),
        ('root', 1, graph_model.GraphRowColor.NORMAL, ()),
    ),
    'HEAD': (
        ('tip', 0, graph_model.GraphRowColor.HEAD, ((0, 0, 0),)),
        ('root', 0, graph_model.GraphRowColor.NORMAL, ()),
    ),
}


def _region_has_visible_pixel(image, rect):
    clipped = rect.intersected(image.rect())
    return any(
        image.pixelColor(x, y).alpha() > 0
        for y in range(clipped.top(), clipped.bottom() + 1)
        for x in range(clipped.left(), clipped.right() + 1)
    )


def _colors_are_close(actual, expected, tolerance=2):
    return all(
        abs(actual_channel - expected_channel) <= tolerance
        for actual_channel, expected_channel in zip(
            actual.getRgb(), expected.getRgb(), strict=True
        )
    )


def _region_has_color(image, rect, expected, tolerance=2):
    clipped = rect.intersected(image.rect())
    return any(
        _colors_are_close(image.pixelColor(x, y), expected, tolerance)
        for y in range(clipped.top(), clipped.bottom() + 1)
        for x in range(clipped.left(), clipped.right() + 1)
    )


def _render_semantic_graph(delegate, qapp, palette, graph_result, selected_row=None):
    model = QtGui.QStandardItemModel()
    row_rects = []
    margin = 8
    width = 160
    for row_index, row in enumerate(graph_result.rows):
        item = QtGui.QStandardItem()
        item.setData(row, GRAPH_ROW_ROLE)
        if row_index:
            item.setData(graph_result.rows[row_index - 1], GRAPH_PREV_ROW_ROLE)
        model.appendRow(item)
        row_rects.append(
            QtCore.QRect(
                margin,
                margin + row_index * GraphDelegate.ROW_HEIGHT,
                width,
                GraphDelegate.ROW_HEIGHT,
            )
        )

    image = QtGui.QImage(
        width + margin * 3,
        len(graph_result.rows) * GraphDelegate.ROW_HEIGHT + margin * 2,
        QtGui.QImage.Format_ARGB32_Premultiplied,
    )
    image.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(image)
    try:
        for row_index, rect in enumerate(row_rects):
            option = QtWidgets.QStyleOptionViewItem()
            option.rect = rect
            option.palette = QtGui.QPalette(palette)
            option.font = qapp.font()
            option.fontMetrics = QtGui.QFontMetrics(option.font)
            if row_index == selected_row:
                option.state |= QtWidgets.QStyle.State_Selected
            delegate.paint(painter, option, model.index(row_index, 0))
    finally:
        painter.end()
    return image, row_rects, model


@pytest.mark.parametrize(
    'palette',
    [
        _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff'),
        _palette('#202328', '#e8eaed', '#17191d', '#292d33', '#6ea8fe', '#101216'),
    ],
    ids=('light', 'dark'),
)
@pytest.mark.parametrize(
    ('scenario', 'commits', 'head_oid'),
    _SEMANTIC_PAINT_SCENARIOS,
    ids=('linear', 'fork', 'merge', 'HEAD'),
)
def test_semantic_paint_smoke_renders_graph_regions_without_touching_background(
    qapp, managed_qobject, palette, scenario, commits, head_oid
):
    graph_result = graph_model.build_graph(commits, head_oid=head_oid)
    expected_rows = _SEMANTIC_TOPOLOGY_ORACLE[scenario]

    # Assert the complete semantic topology before painting. In particular, this
    # catches a missing linear edge and either of the merge commit's two edges.
    assert [row.commit_oid for row in graph_result.rows] == [
        expected[0] for expected in expected_rows
    ]
    assert [
        (
            row.commit_column,
            row.color,
            tuple(
                (edge.from_column, edge.to_column, edge.color_index)
                for edge in row.edges_to_parent
            ),
        )
        for row in graph_result.rows
    ] == [(column, color, edges) for _, column, color, edges in expected_rows]

    delegate = managed_qobject(GraphDelegate())
    image, row_rects, _model = _render_semantic_graph(
        delegate, qapp, palette, graph_result
    )
    style = inline_graph_style(palette)

    assert not _region_has_visible_pixel(
        image, QtCore.QRect(0, 0, image.width(), row_rects[0].top())
    )
    assert not _region_has_visible_pixel(
        image,
        QtCore.QRect(
            row_rects[0].right() + 1,
            0,
            image.width() - row_rects[0].right() - 1,
            image.height(),
        ),
    )

    node_guard = GraphDelegate.DOT_RADIUS + max(2, GraphDelegate.EDGE_WIDTH)
    for row_index, (row, expected) in enumerate(
        zip(graph_result.rows, expected_rows, strict=True)
    ):
        rect = row_rects[row_index]
        center_x = (
            rect.left()
            + row.commit_column * GraphDelegate.LANE_WIDTH
            + GraphDelegate.LANE_WIDTH // 2
        )
        center_y = rect.center().y()
        assert _region_has_visible_pixel(
            image, QtCore.QRect(center_x - 2, center_y - 2, 5, 5)
        )

        for from_column, to_column, color_index in expected[3]:
            from_x = (
                rect.left()
                + from_column * GraphDelegate.LANE_WIDTH
                + GraphDelegate.LANE_WIDTH // 2
            )
            to_x = (
                rect.left()
                + to_column * GraphDelegate.LANE_WIDTH
                + GraphDelegate.LANE_WIDTH // 2
            )
            lane_color = style.lane_colors[color_index]
            if from_column == to_column:
                # Tiny outgoing and incoming samples are on opposite row edges,
                # farther from both commit nodes than either pen can reach.
                outgoing_y = rect.bottom() - 2
                assert outgoing_y - 1 - center_y > node_guard
                assert _region_has_color(
                    image,
                    QtCore.QRect(from_x - 1, outgoing_y - 1, 3, 3),
                    lane_color,
                )
            else:
                # At t=0.5 this cubic is halfway between both lanes and row
                # halves, semantically on the diagonal and away from either node.
                diagonal_x = round((from_x + to_x) / 2)
                diagonal_y = round((center_y + rect.bottom() + 1) / 2)
                assert (
                    (abs(diagonal_x - center_x) - 1) ** 2
                    + (abs(diagonal_y - center_y) - 1) ** 2
                ) ** 0.5 > node_guard
                assert _region_has_color(
                    image,
                    QtCore.QRect(diagonal_x - 1, diagonal_y - 1, 3, 3),
                    lane_color,
                )

            next_rect = row_rects[row_index + 1]
            incoming_y = next_rect.top() + 2
            assert next_rect.center().y() - (incoming_y + 1) > node_guard
            assert _region_has_color(
                image,
                QtCore.QRect(to_x - 1, incoming_y - 1, 3, 3),
                lane_color,
            )

    if scenario == 'linear':
        selected_image, selected_rects, selected_model = _render_semantic_graph(
            delegate, qapp, palette, graph_result, selected_row=0
        )
        selected_rect = selected_rects[0]
        sample_x = selected_rect.right() - 4
        sample_y = selected_rect.center().y()
        graph_right = selected_rect.left() + (
            graph_result.max_columns * GraphDelegate.LANE_WIDTH
        )
        assert sample_x > graph_right + 8
        assert all(
            selected_model.index(row, 0).data(QtCore.Qt.DisplayRole) is None
            and selected_model.index(row, 0).data(COMMIT_ROLE) is None
            for row in range(selected_model.rowCount())
        )
        assert selected_image.pixelColor(sample_x, sample_y).rgba() == (
            palette.highlight().color().rgba()
        )
        assert not _region_has_visible_pixel(
            selected_image,
            QtCore.QRect(
                selected_rect.right() + 1,
                0,
                selected_image.width() - selected_rect.right() - 1,
                selected_image.height(),
            ),
        )

    if scenario == 'HEAD':
        head_index = next(
            index
            for index, row in enumerate(graph_result.rows)
            if row.color == graph_model.GraphRowColor.HEAD
        )
        head_row = graph_result.rows[head_index]
        head_rect = row_rects[head_index]
        center_x = (
            head_rect.left()
            + head_row.commit_column * GraphDelegate.LANE_WIDTH
            + GraphDelegate.LANE_WIDTH // 2
        )
        center_y = head_rect.center().y()
        fill_region = QtCore.QRect(center_x - 2, center_y - 2, 5, 5)
        annulus_region = QtCore.QRect(
            center_x + GraphDelegate.DOT_RADIUS + 1, center_y - 2, 3, 5
        )
        assert not fill_region.intersects(annulus_region)
        assert _region_has_color(image, fill_region, style.head_fill)
        assert _region_has_color(image, annulus_region, style.head_accent)


def test_graph_delegate_offscreen_nodes_selection_lanes_and_size(
    qapp, app_context, managed_qobject, monkeypatch
):
    palette = _palette('#f8f8f8', '#202020', '#ffffff', '#ececec', '#315f9c', '#fff7df')
    factory = dag.CommitFactory()
    parent = _commit(app_context, factory, 'parent')
    commit = _commit(app_context, factory, 'commit', (parent,))
    commit.tags = ['heads/main']
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([parent, commit], _graph_result([parent, commit]))
    tree.setPalette(palette)
    tree.display_inline_graph(True)
    original = list(EdgeColor.colors)
    monkeypatch.setattr(EdgeColor, 'colors', [])

    images = {
        color: _paint_graph_row(tree, color, palette)
        for color in (
            graph_model.GraphRowColor.NORMAL,
            graph_model.GraphRowColor.MERGE,
            graph_model.GraphRowColor.HEAD,
        )
    }
    center = QtCore.QPoint(GraphDelegate.LANE_WIDTH // 2, 13)
    centers = {
        color: image.pixelColor(center).rgba() for color, image in images.items()
    }
    assert len(set(centers.values())) == 3
    head = images[graph_model.GraphRowColor.HEAD]
    assert (
        head.pixelColor(center.x() + GraphDelegate.DOT_RADIUS + 2, center.y()).rgba()
        != palette.base().color().rgba()
    )
    selected = _paint_graph_row(
        tree, graph_model.GraphRowColor.NORMAL, palette, selected=True
    )
    assert selected.pixelColor(230, 2) == palette.highlight().color()
    assert EdgeColor.colors == []
    assert original

    option = QtWidgets.QStyleOptionViewItem()
    option.font = tree.font()
    option.fontMetrics = QtGui.QFontMetrics(option.font)
    hint = tree.graph_delegate.sizeHint(
        option, tree.indexFromItem(tree.topLevelItem(0), 0)
    )
    assert GraphDelegate.LANE_WIDTH == 18
    assert hint.height() == 26
    assert 24 <= hint.height() <= 28


@pytest.mark.parametrize('point_size', (18, 24))
def test_graph_delegate_large_font_size_and_label_hit_area_stay_coherent(
    point_size, qapp, app_context, managed_qobject
):
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['heads/main']
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([commit], _graph_result([commit]))
    item = tree.topLevelItem(0)
    index = tree.indexFromItem(item, 0)
    option = QtWidgets.QStyleOptionViewItem()
    option.font = QtGui.QFont(tree.font())
    option.font.setPointSize(point_size)
    option.fontMetrics = QtGui.QFontMetrics(option.font)

    hint = tree.graph_delegate.sizeHint(option, index)

    assert hint.height() >= option.fontMetrics.height() + 4
    rect = QtCore.QRectF(0, 0, hint.width(), hint.height())
    label_x = GraphDelegate.LANE_WIDTH + 8
    label_index, _condensed = tree.graph_delegate._label_hit_test(
        QtCore.QPointF(label_x, rect.center().y()),
        rect,
        option.fontMetrics,
        index,
        item,
    )
    assert label_index == 0


class _TextRecordingPainter:
    def __init__(self):
        self.pen = QtGui.QPen()
        self.text_colors = []
        self.fills = []
        self.brush = QtGui.QBrush()
        self.rounded_styles = []
        self.rounded_rects = []

    def save(self):
        pass

    def restore(self):
        pass

    def setRenderHint(self, *_args):
        pass

    def setClipRect(self, *_args):
        pass

    def fillRect(self, _rect, brush):
        self.fills.append(brush.color())

    def setPen(self, pen):
        self.pen = QtGui.QPen(pen)

    def setBrush(self, brush):
        self.brush = QtGui.QBrush(brush)

    def setFont(self, *_args):
        pass

    def drawLine(self, *_args):
        pass

    def drawPath(self, *_args):
        pass

    def drawEllipse(self, *_args):
        pass

    def drawRoundedRect(self, *args):
        self.rounded_rects.append(QtCore.QRectF(args[0]))
        self.rounded_styles.append((self.pen.color(), self.brush.color()))

    def drawText(self, *args):
        self.text_colors.append((str(args[-1]), self.pen.color()))


def test_24pt_visible_chip_and_hit_area_have_identical_boundaries(
    qapp, app_context, managed_qobject
):
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['heads/main']
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([commit], _graph_result([commit]))
    item = tree.topLevelItem(0)
    index = tree.indexFromItem(item, 0)
    font = QtGui.QFont(tree.font())
    font.setPointSize(24)
    metrics = QtGui.QFontMetrics(font)
    option = QtWidgets.QStyleOptionViewItem()
    option.font = font
    option.fontMetrics = metrics
    hint = tree.graph_delegate.sizeHint(option, index)
    rect = QtCore.QRectF(0, 0, hint.width(), hint.height())
    painter = _TextRecordingPainter()
    label_x = GraphDelegate.LANE_WIDTH + 8
    tree.graph_delegate._draw_labels(
        painter,
        rect.center().y(),
        commit.tags,
        label_x,
        metrics,
        item,
        inline_graph_style(tree.palette()),
    )
    chip = painter.rounded_rects[0]
    x = chip.center().x()

    assert hint.height() == max(26, metrics.height() + 4)
    for y in (chip.top(), chip.bottom()):
        assert (
            tree.graph_delegate._label_hit_test(
                QtCore.QPointF(x, y), rect, metrics, index, item
            )[0]
            == 0
        )
    for y in (chip.top() - 0.01, chip.bottom() + 0.01):
        assert (
            tree.graph_delegate._label_hit_test(
                QtCore.QPointF(x, y), rect, metrics, index, item
            )[0]
            == -1
        )


def _adversarial_chip_palettes():
    invalid = QtGui.QColor()
    transparent = QtGui.QColor(127, 127, 127, 0)
    return [
        _palette(*(QtGui.QColor(value, value, value) for _ in range(6)))
        for value in (0, 127, 255)
    ] + [
        _palette(*(transparent for _ in range(6))),
        _palette(*(invalid for _ in range(6))),
    ]


@pytest.mark.parametrize('selected', (False, True))
@pytest.mark.parametrize('palette', _adversarial_chip_palettes())
def test_draw_labels_makes_every_adversarial_chip_opaque_and_contrasting(
    qapp, managed_qobject, selected, palette
):
    parent = managed_qobject(QtWidgets.QWidget())
    delegate = managed_qobject(GraphDelegate(parent))
    painter = _TextRecordingPainter()
    style = inline_graph_style(palette)
    selected_text = palette.highlightedText().color() if selected else None

    delegate._draw_labels(
        painter,
        20,
        ['other', 'tags/v1', 'heads/main'],
        20,
        QtGui.QFontMetrics(qapp.font()),
        None,
        style,
        selected_text,
    )

    assert len(painter.rounded_styles) == 3
    assert len({brush.rgba() for _pen, brush in painter.rounded_styles}) == 3
    assert (
        _contrast(style.selected_text, _opaque_color(palette.highlight().color()))
        >= 4.5
    )
    for pen, brush in painter.rounded_styles:
        assert pen.isValid() and pen.alpha() == 255
        assert brush.isValid() and brush.alpha() == 255
        assert _contrast(pen, brush) >= 4.5
    for color in style.__dict__.values():
        colors = color if isinstance(color, tuple) else (color,)
        assert all(item.isValid() and item.alpha() == 255 for item in colors)


def test_best_contrast_empty_inputs_return_valid_opaque_fallbacks():
    fallback = _best_contrast([], [])
    without_background = _best_contrast([QtGui.QColor()], [])

    assert fallback.isValid() and fallback.alpha() == 255
    assert without_background.isValid() and without_background.alpha() == 255


@pytest.mark.parametrize(
    'palette',
    [
        _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff'),
        _palette('#202328', '#e8eaed', '#17191d', '#292d33', '#6ea8fe', '#101216'),
    ],
)
def test_selected_inline_summary_and_each_chip_have_contrasting_text(
    qapp, app_context, managed_qobject, palette
):
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['other', 'tags/v1', 'heads/main']
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([commit], _graph_result([commit]))
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = QtCore.QRect(0, 0, 420, 26)
    option.palette = palette
    option.font = tree.font()
    option.fontMetrics = QtGui.QFontMetrics(option.font)
    option.state |= QtWidgets.QStyle.State_Selected
    painter = _TextRecordingPainter()

    tree.graph_delegate.paint(
        painter, option, tree.indexFromItem(tree.topLevelItem(0), 0)
    )

    style = inline_graph_style(palette)
    assert painter.fills == [palette.highlight().color()]
    assert [background for _pen, background in painter.rounded_styles] == [
        style.chip_other,
        style.chip_remote,
        style.chip_head,
    ]
    for pen, background in painter.rounded_styles:
        assert _contrast(pen, background) >= 4.5
    text_colors = dict(painter.text_colors)
    assert set(text_colors) >= {'other', 'v1', 'main', 'commit commit'}
    assert text_colors['commit commit'] == palette.highlightedText().color()


def test_commit_tree_palette_change_updates_viewport_and_next_paint_style(
    qapp, app_context, managed_qobject, monkeypatch
):
    import cola.widgets.dag as dag_widget

    first = _palette('#ffffff', '#202020', '#ffffff', '#eeeeee', '#225f99', '#ffffff')
    second = _palette('#181818', '#eeeeee', '#151515', '#292929', '#b66d24', '#111111')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([commit], _graph_result([commit]))
    calls = []
    updates = []
    real_factory = dag_widget.inline_graph_style
    monkeypatch.setattr(
        dag_widget,
        'inline_graph_style',
        lambda palette: calls.append(real_factory(palette)) or calls[-1],
    )
    monkeypatch.setattr(tree.viewport(), 'update', lambda: updates.append(True))

    tree.setPalette(first)
    before = _paint_graph_row(tree, graph_model.GraphRowColor.NORMAL, first)
    updates.clear()
    tree.setPalette(second)
    QtWidgets.QApplication.sendEvent(tree, QtCore.QEvent(QtCore.QEvent.PaletteChange))
    after = _paint_graph_row(tree, graph_model.GraphRowColor.NORMAL, second)

    assert updates
    assert len(calls) == 2
    assert calls[0] != calls[1]
    center = QtCore.QPoint(GraphDelegate.LANE_WIDTH // 2, 13)
    assert before.pixelColor(center) != after.pixelColor(center)


def test_default_column_ratio_prioritizes_summary_without_overwriting_saved_widths(
    qapp, app_context, managed_qobject
):
    history = managed_qobject(CommitHistoryWidget(app_context))
    tree = history.treewidget
    history.resize(800, 400)
    history.show()
    qapp.processEvents()

    assert tree.columnWidth(CommitTreeWidgetItem.SUMMARY) == pytest.approx(
        tree.header().width() * 0.70, abs=2
    )
    assert tree.columnWidth(CommitTreeWidgetItem.AUTHOR) == pytest.approx(
        tree.header().width() * 0.15, abs=2
    )

    custom_widths = [301, 201]
    tree.set_column_widths(custom_widths)
    saved_state = history.export_state()
    restored = managed_qobject(CommitHistoryWidget(app_context))

    assert restored.apply_state(saved_state)
    assert restored.treewidget.column_widths()[:2] == custom_widths


def test_display_inline_graph_installs_and_removes_delegate(
    qapp, app_context, managed_qobject
):
    tree = _tree(app_context, managed_qobject)

    tree.display_inline_graph(True)
    assert tree.itemDelegateForColumn(0) is tree.graph_delegate

    tree.display_inline_graph(False)
    assert tree.itemDelegateForColumn(0) is None


def test_history_widget_preserves_positional_parent_constructor_compatibility(
    qapp, app_context, managed_qobject
):
    parent = managed_qobject(QtWidgets.QWidget())
    history = managed_qobject(
        CommitHistoryWidget(app_context, '--all', 1000, False, parent)
    )

    assert history.parent() is parent
    assert history.display_inline_graph_action.isChecked() is False


@pytest.mark.parametrize('display_inline_graph', (False, True))
def test_history_widget_inline_graph_constructor_owns_action_and_delegate_default(
    display_inline_graph, qapp, app_context, managed_qobject
):
    history = managed_qobject(
        CommitHistoryWidget(app_context, display_inline_graph=display_inline_graph)
    )

    assert history.display_inline_graph_action.isChecked() is display_inline_graph
    expected_delegate = (
        history.treewidget.graph_delegate if display_inline_graph else None
    )
    assert history.treewidget.itemDelegateForColumn(0) is expected_delegate


def test_linear_history_items_expose_graph_and_commit_roles(
    qapp, app_context, managed_qobject
):
    factory = dag.CommitFactory()
    root = _commit(app_context, factory, 'A')
    middle = _commit(app_context, factory, 'B', (root,))
    tip = _commit(app_context, factory, 'C', (middle,))
    tree = _tree(app_context, managed_qobject)

    tree.add_commits([root, middle, tip], _graph_result([root, middle, tip]))

    expected = [('C', None), ('B', 'C'), ('A', 'B')]
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
    root = _commit(app_context, factory, 'A')
    left = _commit(app_context, factory, 'B', (root,))
    right = _commit(app_context, factory, 'C', (root,))
    tree = _tree(app_context, managed_qobject)

    tree.add_commits([root, left, right], _graph_result([root, left, right]))

    expected = [('C', 0, None), ('B', 1, 'C'), ('A', 0, 'B')]
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
    root = _commit(app_context, factory, 'A')
    tip = _commit(app_context, factory, 'B', (root,))
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([root, tip], _graph_result([root, tip]))
    selected = QtTest.QSignalSpy(tree.commits_selected)

    tree.topLevelItem(0).setSelected(True)

    assert selected.wait(1000)
    qapp.processEvents()
    assert _spy_count(selected) == 1
    assert list(_spy_payload(selected, 0)[0]) == [tip]


def test_history_widget_state_round_trips_canonically_between_children(
    qapp, app_context, managed_qobject
):
    first = managed_qobject(CommitHistoryWidget(app_context))
    second = managed_qobject(CommitHistoryWidget(app_context))
    first.set_values('topic -- path', 4321, True)
    first.display_inline_graph_action.setChecked(True)
    first.treewidget.display_inline_graph(True)
    widths = [271, 183, 149]
    for column, width in enumerate(widths):
        first.treewidget.setColumnWidth(column, width)

    state = first.export_state()
    assert second.apply_state(state)

    assert second.export_state() == state
    assert state['ref'] == 'topic -- path'
    assert state['count'] == 4321
    assert state['display_status'] is True
    assert state['display_inline_graph'] is True
    assert state['log']['column_widths'] == widths[:2]
    assert not ({'windowstate', 'lock_layout', 'graph', 'diff', 'files'} & state.keys())


def _new_gitdag(app_context, managed_qobject, params):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    return managed_qobject(GitDAG(app_context, params))


def _stored_history_state(history, nested):
    return {'history': history} if nested else dict(history)


def test_gitdag_exports_canonical_nested_history_state(
    qapp, app_context, managed_qobject
):
    widget = _new_gitdag(app_context, managed_qobject, dag.DAG('HEAD', 1000))
    widget.historywidget.set_values('stored-ref', 321, False)

    state = widget.export_state()

    assert state['history'] == widget.historywidget.export_state()
    assert not (
        {'ref', 'count', 'display_inline_graph', 'display_status', 'log'} & state.keys()
    )
    assert {
        'windowstate',
        'word_wrap',
        'intraline_diff_preset',
        'intraline_diff_timing',
    } <= state.keys()


def test_gitdag_applies_and_round_trips_nested_history_state(
    qapp, app_context, managed_qobject
):
    params = dag.DAG('HEAD', 1000)
    widget = _new_gitdag(app_context, managed_qobject, params)
    history = {
        'ref': 'stored-ref',
        'count': 321,
        'display_inline_graph': False,
        'display_status': False,
        'log': {'column_widths': [240, 120]},
    }

    widget.apply_state({'history': history})
    exported = widget.export_state()

    assert params.ref == 'stored-ref'
    assert params.count == 321
    assert params.display_status is False
    assert exported['history'] == history
    assert not (set(history) & exported.keys())


def test_gitdag_migrates_legacy_flat_history_state_to_canonical_nested_state(
    qapp, app_context, managed_qobject
):
    params = dag.DAG('HEAD', 1000)
    widget = _new_gitdag(app_context, managed_qobject, params)
    legacy = {
        'ref': 'legacy-ref',
        'count': 321,
        'display_inline_graph': False,
        'display_status': False,
        'log': {'column_widths': [240, 120]},
    }

    widget.apply_state(legacy)
    exported = widget.export_state()

    assert params.ref == 'legacy-ref'
    assert params.count == 321
    assert params.display_status is False
    assert exported['history'] == legacy
    assert not (set(legacy) & exported.keys())


@pytest.mark.parametrize('nested', (False, True))
@pytest.mark.parametrize(
    ('field', 'malformed'),
    (
        ('count', None),
        ('count', 'oops'),
        ('count', {}),
        ('count', True),
        ('ref', 123),
        ('display_inline_graph', 'oops'),
        ('display_status', {}),
        ('log', 'oops'),
        ('log', {'column_widths': 'oops'}),
        ('log', {'column_widths': [240, {}]}),
    ),
)
def test_gitdag_rejects_malformed_flat_and_nested_history_state(
    field, malformed, nested, qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before = widget.historywidget.export_state()
    history = dict(before)
    history[field] = malformed

    result = widget.apply_state(_stored_history_state(history, nested))

    assert result is False
    assert widget.historywidget.export_state() == before
    assert params.ref == before['ref']
    assert params.count == before['count']
    assert params.display_status == before['display_status']


@pytest.mark.parametrize('nested_history', (None, 'oops', [], True))
def test_gitdag_rejects_non_dict_nested_history_state(
    nested_history, qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before = widget.historywidget.export_state()

    result = widget.apply_state({'history': nested_history})

    assert result is False
    assert widget.historywidget.export_state() == before
    assert (params.ref, params.count, params.display_status) == (
        before['ref'],
        before['count'],
        before['display_status'],
    )


def test_gitdag_rejects_malformed_nested_state_without_legacy_fallback(
    qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before = widget.historywidget.export_state()
    state = dict(before)
    state['ref'] = 'flat-ref'
    state['count'] = 123
    state['history'] = 'malformed'

    result = widget.apply_state(state)

    assert result is False
    assert widget.historywidget.export_state() == before
    assert (params.ref, params.count) == (before['ref'], before['count'])


def test_gitdag_rejects_history_state_missing_count_atomically(
    qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before = widget.historywidget.export_state()
    history = dict(before)
    history.pop('count')
    history['ref'] = 'stored-ref'

    result = widget.apply_state({'history': history})

    assert result is False
    assert widget.historywidget.export_state() == before
    assert (params.ref, params.count) == (before['ref'], before['count'])


@pytest.mark.parametrize(
    ('field', 'malformed', 'override_value'),
    (
        ('count', 'malformed', 1000),
        ('ref', 123, 'main --'),
    ),
)
def test_gitdag_rejects_malformed_state_before_cli_override(
    field, malformed, override_value, qapp, app_context, managed_qobject
):
    params = dag.DAG('main --', 1000)
    params.overrides[field] = override_value
    widget = _new_gitdag(app_context, managed_qobject, params)
    before = widget.historywidget.export_state()
    history = dict(before)
    history[field] = malformed
    history['display_status'] = not before['display_status']

    result = widget.apply_state({'history': history})

    assert result is False
    assert widget.historywidget.export_state() == before
    assert (params.ref, params.count) == (before['ref'], before['count'])


def test_gitdag_rejects_malformed_history_before_window_state_mutation(
    qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before_lock = widget.lock_layout
    before_action = widget.lock_layout_action.isChecked()

    result = widget.apply_state({'history': 'malformed', 'lock_layout': True})

    assert result is False
    assert widget.lock_layout is before_lock
    assert widget.lock_layout_action.isChecked() is before_action


def test_gitdag_rolls_back_failed_window_apply_before_history_and_params(
    qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before = widget.historywidget.export_state()
    history = dict(before)
    history['ref'] = 'stored-ref'
    history['count'] = 123

    result = widget.apply_state({'history': history, 'lock_layout': True})

    assert result is False
    assert widget.historywidget.export_state() == before
    assert (params.ref, params.count) == (before['ref'], before['count'])
    assert widget.lock_layout is False
    assert widget.lock_layout_action.isChecked() is False


def test_history_widget_missing_inline_state_uses_legacy_true_default(
    qapp, app_context, managed_qobject
):
    widget = managed_qobject(
        CommitHistoryWidget(
            app_context, ref='current-ref', count=777, display_status=True
        )
    )
    assert widget.display_inline_graph_action.isChecked() is False

    result = widget.apply_state({'ref': 'saved-ref', 'count': 123})

    assert result is True
    assert widget.display_inline_graph_action.isChecked() is True


def test_gitdag_rejects_malformed_windowstate_before_any_commit(
    qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before_history = widget.historywidget.export_state()
    before_geometry = bytes(widget.saveGeometry())
    state = widget.export_state()
    state['history']['ref'] = 'stored-ref'
    state['windowstate'] = {}

    result = widget.apply_state(state)

    assert result is False
    assert widget.historywidget.export_state() == before_history
    assert (params.ref, params.count) == (
        before_history['ref'],
        before_history['count'],
    )
    assert bytes(widget.saveGeometry()) == before_geometry


def test_gitdag_rejects_malformed_diff_option_before_history_commit(
    qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before = widget.historywidget.export_state()
    history = dict(before)
    history['ref'] = 'stored-ref'

    result = widget.apply_state({'history': history, 'intraline_diff_preset': []})

    assert result is False
    assert widget.historywidget.export_state() == before
    assert (params.ref, params.count) == (before['ref'], before['count'])


@pytest.mark.parametrize('count', (0, -1, 10_000_000, 2**63))
def test_history_widget_rejects_count_outside_spinbox_range(
    count, qapp, app_context, managed_qobject
):
    widget = managed_qobject(
        CommitHistoryWidget(
            app_context, ref='current-ref', count=777, display_status=True
        )
    )
    before = widget.export_state()

    result = widget.apply_state({'ref': 'stored-ref', 'count': count})

    assert result is False
    assert widget.export_state() == before


def test_gitdag_rolls_back_unexpected_base_apply_exception(
    monkeypatch, qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before = widget.historywidget.export_state()
    state = widget.export_state()
    state['history']['ref'] = 'stored-ref'
    original_apply_state = standard.MainWindow.apply_state
    calls = 0

    def fail_once(window, applied_state):
        nonlocal calls
        calls += 1
        if calls == 1:
            window.lock_layout = True
            raise RuntimeError('injected base failure')
        return original_apply_state(window, applied_state)

    monkeypatch.setattr(standard.MainWindow, 'apply_state', fail_once)

    result = widget.apply_state(state)

    assert result is False
    assert calls == 2
    assert widget.lock_layout is False
    assert widget.historywidget.export_state() == before
    assert (params.ref, params.count) == (before['ref'], before['count'])


def test_gitdag_rolls_back_unexpected_diff_apply_exception(
    monkeypatch, qapp, app_context, managed_qobject
):
    params = dag.DAG('current-ref', 777)
    widget = _new_gitdag(app_context, managed_qobject, params)
    before = widget.historywidget.export_state()
    before_word_wrap = widget.diffwidget.options.enable_word_wrapping.isChecked()
    history = dict(before)
    history['ref'] = 'stored-ref'
    original_set_preset = widget.diffwidget.set_intraline_diff_preset
    calls = 0

    def fail_once(preset, update=False):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError('injected diff failure')
        return original_set_preset(preset, update=update)

    monkeypatch.setattr(widget.diffwidget, 'set_intraline_diff_preset', fail_once)

    result = widget.apply_state({'history': history, 'word_wrap': True})

    assert result is False
    assert calls == 2
    assert widget.historywidget.export_state() == before
    assert (params.ref, params.count) == (before['ref'], before['count'])
    assert (
        widget.diffwidget.options.enable_word_wrapping.isChecked() is before_word_wrap
    )


@pytest.mark.parametrize(
    'state',
    (
        None,
        'oops',
        [],
        True,
        {'ref': 123, 'count': 777},
        {'ref': 'current-ref', 'count': 'oops'},
        {'ref': 'current-ref', 'count': 777, 'log': 'oops'},
        {
            'ref': 'current-ref',
            'count': 777,
            'log': {'column_widths': [240, {}]},
        },
    ),
)
def test_history_widget_rejects_malformed_direct_child_state(
    state, qapp, app_context, managed_qobject
):
    widget = managed_qobject(
        CommitHistoryWidget(
            app_context, ref='current-ref', count=777, display_status=True
        )
    )
    before = widget.export_state()

    result = widget.apply_state(state)

    assert result is False
    assert widget.export_state() == before


@pytest.mark.parametrize(
    ('parser', 'argv'),
    (
        (dag_cli.parse_args, ['--count', '1000']),
        (main_cli.parse_args, ['dag', '--count', '1000']),
    ),
)
@pytest.mark.parametrize('nested', (False, True))
def test_explicit_parser_count_wins_over_flat_and_nested_stored_count(
    parser, argv, nested, qapp, app_context, managed_qobject
):
    params = dag.DAG('main --', 1000)
    params.set_arguments(parser(argv))
    widget = _new_gitdag(app_context, managed_qobject, params)
    history = {
        'ref': 'stored-ref',
        'count': 500,
        'display_inline_graph': True,
        'display_status': False,
        'log': {'column_widths': [240, 120]},
    }

    widget.apply_state(_stored_history_state(history, nested))

    assert params.count == 1000
    assert widget.historywidget.maxresults.value() == 1000


@pytest.mark.parametrize(
    ('parser', 'argv'),
    (
        (dag_cli.parse_args, ['main', '--']),
        (main_cli.parse_args, ['dag', 'main', '--']),
    ),
)
@pytest.mark.parametrize('nested', (False, True))
def test_explicit_parser_current_ref_wins_over_flat_and_nested_foreign_ref(
    parser, argv, nested, qapp, app_context, managed_qobject
):
    params = dag.DAG('main --', 1000)
    params.set_arguments(parser(argv))
    widget = _new_gitdag(app_context, managed_qobject, params)
    history = {
        'ref': 'foreign-ref',
        'count': 500,
        'display_inline_graph': True,
        'display_status': False,
        'log': {'column_widths': [240, 120]},
    }

    widget.apply_state(_stored_history_state(history, nested))

    assert params.ref == 'main --'
    assert widget.historywidget.revtext.text() == 'main --'
    assert params.count == 500


def test_mainview_accepts_legacy_version_2_dock_state(
    qapp, app_context, managed_qobject, monkeypatch
):
    monkeypatch.setattr(Interaction, 'log', lambda *_args: None)
    monkeypatch.setattr(Interaction, 'log_status', lambda *_args: None)
    app_context.settings.get_gui_state.return_value = {}
    app_context.settings.bookmarks = []
    app_context.settings.recent = []
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    widget = managed_qobject(MainView(app_context))
    legacy_state = widget.export_state()
    legacy_state['windowstate'] = LEGACY_MAINVIEW_V2_WINDOWSTATE
    legacy_state.pop('history', None)
    legacy_state.pop('show_history', None)

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
    request = dag.HistoryRequest(9, 'bad-ref', 1000, False)
    error = 'fatal: exact repository error'

    class FakeReader:
        def __init__(self, _context, _params):
            self.returncode = 128
            self.error = error

        def get(self):
            return iter(())

        def get_worktree_commits(self):
            raise AssertionError('failed reads must not add pseudo-commits')

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', FakeReader)
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
            self.error = ''

        def get(self):
            return iter(())

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', FakeReader)
    request = dag.HistoryRequest(3, 'HEAD', 10, False)
    thread = managed_qobject(ReaderThread(app_context, request))
    results = QtTest.QSignalSpy(thread.result)
    # Mutating the live UI parameters after construction cannot affect the request.
    ui_params = dag.DAG('HEAD', 10)
    ui_params.ref = 'mutated'
    ui_params.count = 999

    thread.start()

    assert thread.wait(5000)
    qapp.processEvents()
    assert _spy_count(results) == 1
    assert captured == [('HEAD', 10, False)]


def test_reader_thread_interruption_after_empty_read_skips_worktree(
    qapp, app_context, managed_qobject, monkeypatch
):
    entered = threading.Event()
    release = threading.Event()
    worktree_called = threading.Event()

    class BlockingEmptyReader:
        returncode = 0
        error = ''

        def __init__(self, _context, _params):
            pass

        def get(self):
            entered.set()
            release.wait()
            return iter(())

        def get_worktree_commits(self):
            worktree_called.set()
            return (None, None)

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', BlockingEmptyReader)
    request = dag.HistoryRequest(23, 'HEAD', 10, False)
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
    assert _spy_payload(results, 0)[0] == dag.HistoryResult(23, False, -1, '', (), None)


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


def _history(app_context, managed_qobject, monkeypatch):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    ManualReaderThread.instances = []
    monkeypatch.setattr('cola.widgets.dag.ReaderThread', ManualReaderThread)
    return managed_qobject(CommitHistoryWidget(app_context, ref='HEAD', count=1000))


def test_active_same_key_with_new_metadata_schedules_followup(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    old_metadata = _HistoryCacheMetadata(
        (), frozenset({'old-ref'}), 10, False, generation=1
    )
    new_metadata = _HistoryCacheMetadata(
        (), frozenset({'new-ref'}), 10, False, generation=2
    )
    assert widget.request_history('same', 10, False, old_metadata)
    active = ManualReaderThread.instances[-1]

    assert widget.request_history('same', 10, False, new_metadata)
    assert widget.pending_request is not None

    active.complete(dag.HistoryResult(active.request.run_id, True, 0, '', (), None))
    qapp.processEvents()
    followup = ManualReaderThread.instances[-1]
    assert followup is not active
    assert widget.last_successful_cache_key is None

    followup.complete(dag.HistoryResult(followup.request.run_id, True, 0, '', (), None))
    qapp.processEvents()
    assert widget.successful_repository_generation == 2
    assert widget.old_refs == {'new-ref'}


def test_same_key_generations_coalesce_latest_and_duplicate_generation_dedupes(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    widget.load_if_stale()
    active = ManualReaderThread.instances[-1]

    widget.model_updated()
    pending = widget.pending_request
    assert pending is not None
    assert widget.pending_cache_metadata.generation == 2

    widget.display()
    assert widget.pending_request is pending
    assert widget.pending_cache_metadata.generation == 2

    widget.model_updated()
    widget.model_updated()
    assert widget.pending_request is pending
    assert widget.pending_cache_metadata.generation == 4
    assert len(ManualReaderThread.instances) == 1

    active.complete(dag.HistoryResult(active.request.run_id, True, 0, '', (), None))
    qapp.processEvents()
    assert len(ManualReaderThread.instances) == 2
    assert widget.active_cache_metadata.generation == 4


def test_control_request_a_b_a_discards_pending_without_new_generation(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    assert widget.request_history('A', 10, False)
    active = ManualReaderThread.instances[-1]
    assert widget.request_history('B', 10, False)
    assert not widget.request_history('A', 10, False)
    assert widget.pending_request is None

    active.complete(dag.HistoryResult(active.request.run_id, True, 0, '', (), None))
    qapp.processEvents()
    assert len(ManualReaderThread.instances) == 1


def test_history_requests_deduplicate_and_coalesce_last_different_request(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)

    assert widget.request_history('HEAD', 10, False)
    first = ManualReaderThread.instances[-1]
    assert not widget.request_history('HEAD', 10, False)
    assert widget.request_history('main', 20, False)
    assert not widget.request_history('main', 20, False)
    assert widget.request_history('topic', 30, True)

    assert len(ManualReaderThread.instances) == 1
    assert widget.pending_request.cache_key == ('topic', 30, True)

    first.complete(dag.HistoryResult(first.request.run_id, True, 0, '', (), None))
    qapp.processEvents()

    assert len(ManualReaderThread.instances) == 2
    assert ManualReaderThread.instances[-1].request.cache_key == ('topic', 30, True)


def test_pending_same_key_uses_latest_non_none_cache_metadata(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    old_metadata = _HistoryCacheMetadata(
        (), frozenset({'old-ref'}), 10, False, generation=1
    )
    new_metadata = _HistoryCacheMetadata(
        (), frozenset({'new-ref'}), 10, False, generation=3
    )
    widget.request_history('blocker', 1, False)
    blocker = ManualReaderThread.instances[-1]
    assert widget.request_history('same', 10, False, old_metadata)

    assert not widget.request_history('same', 10, False, new_metadata)

    blocker.complete(dag.HistoryResult(blocker.request.run_id, True, 0, '', (), None))
    qapp.processEvents()
    pending = ManualReaderThread.instances[-1]
    pending.complete(dag.HistoryResult(pending.request.run_id, True, 0, '', (), None))
    qapp.processEvents()
    assert widget.successful_repository_generation == 3
    assert widget.old_refs == {'new-ref'}


def test_successful_empty_result_clears_items_graph_maps_and_selection(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    widget.restore_selection = lambda: None
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'A')
    widget.request_history('HEAD', 10, False)
    first = ManualReaderThread.instances[-1]
    first.complete(
        dag.HistoryResult(
            first.request.run_id, True, 0, '', (commit,), _graph_result((commit,))
        )
    )
    qapp.processEvents()
    QtTest.QTest.qWait(1)
    qapp.processEvents()
    widget.selection = [commit]
    widget.old_selection = [commit]
    assert widget.treewidget.topLevelItemCount() == 1

    widget.request_history('empty', 10, False)
    empty = ManualReaderThread.instances[-1]
    empty.complete(dag.HistoryResult(empty.request.run_id, True, 0, '', (), None))
    qapp.processEvents()

    assert widget.treewidget.topLevelItemCount() == 0
    assert widget.commits == {}
    assert widget.commit_list == []
    assert widget.selection == []
    assert widget.old_selection == []


def test_failure_preserves_view_sets_error_and_pending_success_clears_it(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    widget.restore_selection = lambda: None
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'A')
    widget.request_history('HEAD', 10, False)
    first = ManualReaderThread.instances[-1]
    first.complete(
        dag.HistoryResult(
            first.request.run_id, True, 0, '', (commit,), _graph_result((commit,))
        )
    )
    qapp.processEvents()

    widget.request_history('bad', 10, False)
    failed = ManualReaderThread.instances[-1]
    widget.request_history('next', 10, False)
    failed.emit_result(
        dag.HistoryResult(failed.request.run_id, False, 128, 'fatal: exact', (), None)
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
    assert pending.request.ref == 'next'
    assert widget.loading is True

    pending.complete(dag.HistoryResult(pending.request.run_id, True, 0, '', (), None))
    qapp.processEvents()
    assert widget.error_status is None
    assert widget.loading is False


def test_stale_result_does_not_change_view(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'A')
    widget.request_history('HEAD', 10, False)
    active = ManualReaderThread.instances[-1]

    widget.thread_result(
        dag.HistoryResult(
            active.request.run_id + 99, True, 0, '', (commit,), _graph_result((commit,))
        )
    )

    assert widget.treewidget.topLevelItemCount() == 0
    assert widget.commits == {}


def test_stop_discards_pending_and_prevents_scheduled_or_late_updates(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    widget.request_history('HEAD', 10, False)
    active = ManualReaderThread.instances[-1]
    widget.request_history('pending', 20, True)
    QtCore.QTimer.singleShot(0, widget.display)

    widget.stop_and_wait()
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'late')
    active.result.emit(
        dag.HistoryResult(
            active.request.run_id, True, 0, '', (commit,), _graph_result((commit,))
        )
    )
    qapp.processEvents()

    assert active.interrupted
    assert active.waited
    assert widget.pending_request is None
    assert len(ManualReaderThread.instances) == 1
    assert widget.treewidget.topLevelItemCount() == 0
    assert not widget.request_history('after', 1, False)


# Task 3 review regressions (RED -> GREEN slices).
def test_active_pending_active_discards_pending_and_accepts_active_result(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'A')

    assert widget.request_history('A', 10, False)
    active = ManualReaderThread.instances[-1]
    assert widget.request_history('B', 10, False)
    assert not widget.request_history('A', 10, False)
    assert widget.pending_request is None

    active.emit_result(
        dag.HistoryResult(
            active.request.run_id, True, 0, '', (commit,), _graph_result((commit,))
        )
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
    widget = _history(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'A')
    widget.request_history('A', 10, False)
    active = ManualReaderThread.instances[-1]
    widget.request_history('B', 10, False)
    active.emit_result(
        dag.HistoryResult(
            active.request.run_id, True, 0, '', (commit,), _graph_result((commit,))
        )
    )
    qapp.processEvents()
    assert widget.commit_list == []

    assert not widget.request_history('A', 10, False)
    qapp.processEvents()

    assert widget.pending_request is None
    assert widget.commit_list == [commit]


def test_active_result_is_invisible_until_pending_finishes(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    old = _commit(app_context, factory, 'old')
    active_commit = _commit(app_context, factory, 'active')
    pending_commit = _commit(app_context, factory, 'pending')
    widget.apply_result((old,), _graph_result((old,)))
    widget.last_successful_cache_key = ('old', 1, False)
    widget.error_status = 'existing'
    widget.revtext.setToolTip('existing')
    widget.selection = widget.old_selection = [old]

    widget.request_history('A', 10, False)
    active = ManualReaderThread.instances[-1]
    widget.request_history('B', 20, True)
    active.emit_result(
        dag.HistoryResult(
            active.request.run_id,
            True,
            0,
            '',
            (active_commit,),
            _graph_result((active_commit,)),
        )
    )
    qapp.processEvents()

    assert widget.commit_list == [old]
    assert widget.selection == [old]
    assert widget.error_status == 'existing'
    assert widget.last_successful_cache_key == ('old', 1, False)
    assert widget.loading is True
    assert len(ManualReaderThread.instances) == 1

    active.finish()
    qapp.processEvents()
    assert len(ManualReaderThread.instances) == 2
    pending = ManualReaderThread.instances[-1]
    assert widget.loading is True
    pending.emit_result(
        dag.HistoryResult(
            pending.request.run_id,
            True,
            0,
            '',
            (pending_commit,),
            _graph_result((pending_commit,)),
        )
    )
    qapp.processEvents()
    assert widget.commit_list == [pending_commit]
    pending.finish()
    qapp.processEvents()
    assert widget.loading is False


def test_failure_without_pending_stops_loading_and_shows_visible_exact_error(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    error_label = widget.findChild(QtWidgets.QLabel, 'HistoryErrorStatus')
    assert error_label is not None
    assert error_label.isHidden()
    widget.show()
    qapp.processEvents()
    widget.request_history('bad', 10, False)
    active = ManualReaderThread.instances[-1]
    active.emit_result(
        dag.HistoryResult(active.request.run_id, False, 128, 'fatal: exact', (), None)
    )
    qapp.processEvents()

    expected = 'returncode 128: fatal: exact'
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
    widget = _history(app_context, managed_qobject, monkeypatch)
    error_label = widget.findChild(QtWidgets.QLabel, 'HistoryErrorStatus')
    assert error_label is not None
    widget.show()
    qapp.processEvents()
    widget.request_history('bad', 10, False)
    failed = ManualReaderThread.instances[-1]
    failed.complete(
        dag.HistoryResult(failed.request.run_id, False, 7, 'exact', (), None)
    )
    qapp.processEvents()
    widget.request_history('good', 10, False)
    success = ManualReaderThread.instances[-1]
    success.emit_result(
        dag.HistoryResult(success.request.run_id, True, 0, '', (), None)
    )
    qapp.processEvents()

    assert widget.error_status is None
    assert error_label.text() == ''
    assert error_label.isHidden()
    assert error_label.toolTip() == ''
    assert widget.revtext.toolTip() == ''
    assert widget.revtext.styleSheet() == ''


def test_success_replaces_selection_with_new_commit_objects_synchronously(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    old_factory = dag.CommitFactory()
    old_a = _commit(app_context, old_factory, 'A')
    old_b = _commit(app_context, old_factory, 'B', (old_a,))
    widget.apply_result((old_a, old_b), _graph_result((old_a, old_b)))
    widget.selection = widget.old_selection = [old_a]
    new_factory = dag.CommitFactory()
    new_a = _commit(app_context, new_factory, 'A')
    new_b = _commit(app_context, new_factory, 'B', (new_a,))
    selected = QtTest.QSignalSpy(widget.commits_selected)

    widget.apply_result((new_a, new_b), _graph_result((new_a, new_b)))

    assert widget.selection == [new_a]
    assert widget.old_selection == [new_a]
    assert widget.selection[0] is not old_a
    assert _spy_count(selected) == 1
    assert list(_spy_payload(selected, 0)[0]) == [new_a]


def test_private_apply_history_result_alias_is_removed(
    qapp, app_context, managed_qobject
):
    widget = managed_qobject(CommitHistoryWidget(app_context))

    assert not hasattr(widget, '_apply_history_result')


def test_empty_success_clears_selection_and_emits_once(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'A')
    widget.apply_result((commit,), _graph_result((commit,)))
    widget.selection = widget.old_selection = [commit]
    selected = QtTest.QSignalSpy(widget.commits_selected)

    widget.apply_result((), graph_model.GraphResult([], 0))

    assert widget.selection == widget.old_selection == []
    assert _spy_count(selected) == 1
    assert list(_spy_payload(selected, 0)[0]) == []
    assert widget.treewidget.selected_items() == []


def test_display_cache_changes_only_after_current_success_and_failure_retries(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    widget.model.local_branches = ['main']
    widget.model.remote_branches = []
    widget.model.tags = []

    widget.load_if_stale()
    first = ManualReaderThread.instances[-1]
    assert widget.old_refs == set()
    assert widget.old_count == 0
    assert widget.old_display_status is None
    assert widget.successful_repository_generation == -1
    assert widget.last_successful_cache_key is None

    first.emit_result(
        dag.HistoryResult(first.request.run_id, False, 1, 'failed', (), None)
    )
    first.finish()
    qapp.processEvents()
    assert widget.successful_repository_generation == -1
    assert widget.last_successful_cache_key is None

    widget.display()
    retry = ManualReaderThread.instances[-1]
    assert retry is not first
    retry.emit_result(dag.HistoryResult(retry.request.run_id, True, 0, '', (), None))
    qapp.processEvents()
    assert widget.successful_repository_generation == 1
    assert widget.old_refs == {'main'}
    assert widget.old_count == widget.maxresults.value()
    assert widget.old_display_status == widget.display_status_action.isChecked()
    assert widget.last_successful_cache_key == retry.request.cache_key


@pytest.mark.parametrize(
    ('phase', 'repo_error', 'exception_text', 'expected_error'),
    [
        ('construct', '', 'constructor exploded', 'constructor exploded'),
        ('get', 'fatal: reader exact', 'iteration exploded', 'fatal: reader exact'),
        ('worktree', '', 'worktree exploded', 'worktree exploded'),
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
    commit = _commit(app_context, factory, 'A')

    class FakeReader:
        def __init__(self, _context, _params):
            if phase == 'construct':
                raise RuntimeError(exception_text)
            self.returncode = 0
            self.error = repo_error

        def get(self):
            yield commit
            if phase == 'get':
                raise RuntimeError(exception_text)

        def get_worktree_commits(self):
            if phase == 'worktree':
                raise RuntimeError(exception_text)
            return (None, None)

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', FakeReader)
    request = dag.HistoryRequest(17, 'HEAD', 10, False)
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
        error = ''

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

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', EmptyReader)
    monkeypatch.setattr(graph_model, 'build_graph', recording_build_graph)
    thread = managed_qobject(
        ReaderThread(app_context, dag.HistoryRequest(20, 'HEAD', 10, False))
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
    commit = _commit(app_context, factory, 'A')
    worktree_entered = threading.Event()
    release_worktree = threading.Event()
    build_called = threading.Event()

    class WorktreeBlockingReader:
        returncode = 0
        error = ''

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
        raise AssertionError((head_oid, 'graph phase must be skipped'))

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', WorktreeBlockingReader)
    monkeypatch.setattr(graph_model, 'build_graph', forbidden_build_graph)
    thread = managed_qobject(
        ReaderThread(app_context, dag.HistoryRequest(22, 'HEAD', 10, True))
    )
    results = QtTest.QSignalSpy(thread.result)
    thread.start()
    assert worktree_entered.wait(2)

    thread.requestInterruption()
    release_worktree.set()

    assert thread.wait(5000)
    qapp.processEvents()
    assert not build_called.is_set()
    assert _spy_payload(results, 0)[0] == dag.HistoryResult(22, False, -1, '', (), None)


def test_reader_thread_builds_graph_from_commits_and_status_pseudo_commits(
    qapp, app_context, managed_qobject, monkeypatch
):
    factory = dag.CommitFactory()
    root = _commit(app_context, factory, 'root')
    root.tags = ['HEAD']
    stage = _commit(app_context, factory, dag.STAGE, (root,))
    worktree = _commit(app_context, factory, dag.WORKTREE, (stage,))

    class StatusReader:
        returncode = 0
        error = ''

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

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', StatusReader)
    monkeypatch.setattr(graph_model, 'build_graph', recording_build_graph)
    thread = managed_qobject(
        ReaderThread(app_context, dag.HistoryRequest(24, 'HEAD', 10, True))
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
            ('root', []),
            (dag.STAGE, ['root']),
            (dag.WORKTREE, [dag.STAGE]),
        ],
        'root',
    )
    assert calls[0][0] != gui_thread_id
    result = _spy_payload(results, 0)[0]
    assert result.commits == (root, stage, worktree)
    assert {row.commit_oid for row in result.graph.rows} == {
        'root',
        dag.STAGE,
        dag.WORKTREE,
    }


def test_reader_thread_emits_complete_multi_commit_tuple_and_has_no_add_signal(
    qapp, app_context, managed_qobject, monkeypatch
):
    factory = dag.CommitFactory()
    commits = tuple(_commit(app_context, factory, oid) for oid in ('A', 'B', 'C'))

    class FakeReader:
        returncode = 0
        error = ''

        def __init__(self, _context, _params):
            pass

        def get(self):
            return iter(commits)

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', FakeReader)
    thread = managed_qobject(
        ReaderThread(app_context, dag.HistoryRequest(21, 'HEAD', 10, False))
    )
    results = QtTest.QSignalSpy(thread.result)

    assert not hasattr(thread, 'add')
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
            f'{index:040x}',
            (parent,) if parent is not None else (),
        )
        commits.append(commit)
        parent = commit
    commits[-1].tags = ['HEAD']
    boundary_parent = commits[2047]
    boundary_child = commits[2048]
    partial_read = threading.Event()
    release = threading.Event()

    class LargeReader:
        returncode = 0
        error = ''

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

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', LargeReader)
    monkeypatch.setattr(graph_model, 'build_graph', recording_build_graph)
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    window = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))
    widget = window.historywidget
    existing_factory = dag.CommitFactory()
    existing = _commit(app_context, existing_factory, 'existing')
    existing_graph = real_build_graph([('existing', [])])
    widget.apply_result((existing,), existing_graph)
    widget.selection = widget.old_selection = [existing]
    before = (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(window.graphview.items),
        list(widget.selection),
    )
    graph_add_calls = []
    real_graph_add_commits = window.graphview.add_commits

    def recording_graph_add_commits(added_commits):
        graph_add_calls.append((threading.get_ident(), list(added_commits)))
        return real_graph_add_commits(added_commits)

    monkeypatch.setattr(window.graphview, 'add_commits', recording_graph_add_commits)
    gui_thread_id = threading.get_ident()

    assert widget.request_history('large', len(commits), False)
    thread = widget.active_thread
    assert partial_read.wait(2)
    assert (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        dict(window.graphview.items),
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
        dict(window.graphview.items),
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
    assert window.graphview.commits == commits


def test_successful_nonempty_result_without_graph_is_rejected(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    existing = _commit(app_context, factory, 'existing')
    widget.apply_result((existing,), _graph_result((existing,)))
    before = (
        list(widget.commit_list),
        dict(widget.treewidget.oidmap),
    )
    widget.request_history('missing-graph', 10, False)
    active = ManualReaderThread.instances[-1]

    active.emit_result(
        dag.HistoryResult(active.request.run_id, True, 0, '', (existing,), None)
    )
    qapp.processEvents()

    assert (
        list(widget.commit_list),
        dict(widget.treewidget.oidmap),
    ) == before
    assert widget.last_successful_cache_key is None
    assert widget.error_status == 'successful history result is missing graph data'


def test_stale_result_preserves_loading_error_cache_and_selection(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    existing = _commit(app_context, factory, 'existing')
    stale = _commit(app_context, factory, 'stale')
    widget.apply_result((existing,), _graph_result((existing,)))
    qapp.processEvents()
    widget.selection = widget.old_selection = [existing]
    widget._set_error_status('existing error')
    widget.last_successful_cache_key = ('existing', 1, False)
    widget.old_oids = ['existing']
    old_oidmap = dict(widget.treewidget.oidmap)
    widget.request_history('active', 10, False)
    active = ManualReaderThread.instances[-1]

    widget.thread_result(
        dag.HistoryResult(
            active.request.run_id + 1, True, 0, '', (stale,), _graph_result((stale,))
        )
    )

    assert widget.loading is True
    assert widget.error_status == 'existing error'
    assert widget.last_successful_cache_key == ('existing', 1, False)
    assert widget.old_oids == ['existing']
    assert widget.selection == [existing]
    assert widget.commit_list == [existing]
    assert widget.treewidget.oidmap == old_oidmap


def test_failure_preserves_all_applied_state_and_cache(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'A')
    widget.apply_result((commit,), _graph_result((commit,)))
    qapp.processEvents()
    widget.selection = widget.old_selection = [commit]
    widget.last_successful_cache_key = ('old', 1, False)
    widget.old_oids = ['A']
    before = (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        list(widget.selection),
        widget.last_successful_cache_key,
        list(widget.old_oids),
    )
    widget.request_history('bad', 10, False)
    active = ManualReaderThread.instances[-1]

    active.emit_result(
        dag.HistoryResult(active.request.run_id, False, 128, 'fatal', (), None)
    )

    after = (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
        list(widget.selection),
        widget.last_successful_cache_key,
        list(widget.old_oids),
    )
    assert after == before


@pytest.mark.parametrize('outcome', ['failure', 'stale', 'stop'])
def test_partial_real_reader_outcomes_preserve_last_successful_view(
    outcome, qapp, app_context, managed_qobject, monkeypatch
):
    factory = dag.CommitFactory()
    replacement = _commit(app_context, factory, 'replacement')
    partial_read = threading.Event()
    release = threading.Event()

    class PartialReader:
        returncode = 0
        error = ''

        def __init__(self, _context, _params):
            pass

        def get(self):
            yield replacement
            partial_read.set()
            release.wait()
            if outcome == 'failure':
                self.returncode = 128
                self.error = 'fatal after partial read'

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', PartialReader)
    widget = _real_history(app_context, managed_qobject)
    existing_factory = dag.CommitFactory()
    existing = _commit(app_context, existing_factory, 'existing')
    widget.apply_result((existing,), _graph_result((existing,)))
    widget.selection = widget.old_selection = [existing]
    widget.last_successful_cache_key = ('existing', 1, False)
    before = (
        list(widget.commit_list),
        dict(widget.commits),
        dict(widget.treewidget.oidmap),
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
        list(widget.selection),
        widget.last_successful_cache_key,
    ) == before

    if outcome == 'stale':
        widget.active_run_id += 1
        release.set()
        assert thread.wait(5000)
    elif outcome == 'stop':
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
        list(widget.selection),
        widget.last_successful_cache_key,
    ) == before


def _real_history(app_context, managed_qobject):
    app_context.settings.get_gui_state.return_value = {}
    app_context.app.theme.background_color_rgb.return_value = '#ffffff'
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    app_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')
    return managed_qobject(CommitHistoryWidget(app_context, ref='HEAD', count=1000))


def test_history_close_closes_popup_and_stops_worker(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = managed_qobject(CommitHistoryWidget(app_context))
    calls = []
    monkeypatch.setattr(widget.revtext, 'close_popup', lambda: calls.append('popup'))
    monkeypatch.setattr(widget, 'stop_and_wait', lambda: calls.append('stop'))

    assert widget.close()

    assert calls == ['popup', 'stop']


def test_deferred_delete_waits_for_real_blocked_reader(qapp, app_context, monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    exited = threading.Event()
    interrupted_at_exit = []

    class BlockingReader:
        returncode = 0
        error = ''

        def __init__(self, _context, _params):
            pass

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
    widget = CommitHistoryWidget(app_context)
    destroyed = QtTest.QSignalSpy(widget.destroyed)
    assert widget.request_history('active', 10, False)
    assert entered.wait(2)
    thread = widget.active_thread
    helper = threading.Thread(target=lambda: (time.sleep(0.05), release.set()))
    helper.start()

    widget.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(widget, QtCore.QEvent.DeferredDelete)
    deleted_state = (
        exited.is_set(),
        thread.isRunning(),
        interrupted_at_exit,
        _spy_count(destroyed),
    )
    helper.join(2)

    assert deleted_state == (True, False, [True], 1)


def test_close_waits_for_real_blocked_reader_and_discards_pending(
    qapp, app_context, managed_qobject, monkeypatch
):
    entered = threading.Event()
    release = threading.Event()
    exited = threading.Event()
    constructed = []

    class BlockingReader:
        returncode = 0
        error = ''

        def __init__(self, _context, _params):
            constructed.append(self)

        def get(self):
            entered.set()
            release.wait()
            exited.set()
            return iter(())

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', BlockingReader)
    widget = _real_history(app_context, managed_qobject)
    assert widget.request_history('active', 10, False)
    assert entered.wait(2)
    assert widget.request_history('pending', 20, True)
    active_thread = widget.active_thread

    helper = threading.Thread(target=lambda: (time.sleep(0.1), release.set()))
    helper.start()
    widget.stop_and_wait()
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
    assert not widget.request_history('after-close', 1, False)


def test_close_before_scheduled_display_prevents_reader_start(
    qapp, app_context, managed_qobject, monkeypatch
):
    widget = _history(app_context, managed_qobject, monkeypatch)
    QtCore.QTimer.singleShot(0, widget.display)

    widget.stop_and_wait()
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
        error = ''

        def __init__(self, _context, _params):
            pass

        def get(self):
            entered.set()
            release.wait()
            return iter(())

        def get_worktree_commits(self):
            return (None, None)

    monkeypatch.setattr('cola.widgets.dag.dag.RepoReader', BlockingReader)
    widget = _real_history(app_context, managed_qobject)
    widget.request_history('active', 10, False)
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
