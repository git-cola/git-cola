from __future__ import division, absolute_import, unicode_literals
import collections
import math
from itertools import count

from qtpy.QtCore import Qt
from qtpy.QtCore import Signal
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

from ..compat import maxsize
from ..i18n import N_
from ..models import dag
from .. import core
from .. import cmds
from .. import difftool
from .. import hotkeys
from .. import icons
from .. import observable
from .. import qtcompat
from .. import qtutils
from . import archive
from . import browse
from . import completion
from . import createbranch
from . import createtag
from . import defs
from . import diff
from . import filelist
from . import standard


def git_dag(model, args=None, settings=None, existing_view=None):
    """Return a pre-populated git DAG widget."""
    branch = model.currentbranch
    # disambiguate between branch names and filenames by using '--'
    branch_doubledash = branch and (branch + ' --') or ''
    ctx = dag.DAG(branch_doubledash, 1000)
    ctx.set_arguments(args)

    if existing_view is None:
        view = GitDAG(model, ctx, settings=settings)
    else:
        view = existing_view
        view.set_context(ctx)
    if ctx.ref:
        view.display()
    return view


class FocusRedirectProxy(object):
    """Redirect actions from the main widget to child widgets"""

    def __init__(self, *widgets):
        """Provide proxied widgets; the default widget must be first"""
        self.widgets = widgets
        self.default = widgets[0]

    def __getattr__(self, name):
        return (lambda *args, **kwargs:
                self._forward_action(name, *args, **kwargs))

    def _forward_action(self, name, *args, **kwargs):
        """Forward the captured action to the focused or default widget"""
        widget = QtWidgets.QApplication.focusWidget()
        if widget in self.widgets and hasattr(widget, name):
            fn = getattr(widget, name)
        else:
            fn = getattr(self.default, name)

        return fn(*args, **kwargs)


class ViewerMixin(object):
    """Implementations must provide selected_items()"""

    def __init__(self):
        self.selected = None
        self.clicked = None
        self.menu_actions = None  # provided by implementation

    def selected_item(self):
        """Return the currently selected item"""
        selected_items = self.selected_items()
        if not selected_items:
            return None
        return selected_items[0]

    def selected_oid(self):
        item = self.selected_item()
        if item is None:
            result = None
        else:
            result = item.commit.oid
        return result

    def selected_oids(self):
        return [i.commit for i in self.selected_items()]

    def with_oid(self, fn):
        oid = self.selected_oid()
        if oid:
            result = fn(oid)
        else:
            result = None
        return result

    def diff_selected_this(self):
        clicked_oid = self.clicked.oid
        selected_oid = self.selected.oid
        self.diff_commits.emit(selected_oid, clicked_oid)

    def diff_this_selected(self):
        clicked_oid = self.clicked.oid
        selected_oid = self.selected.oid
        self.diff_commits.emit(clicked_oid, selected_oid)

    def cherry_pick(self):
        self.with_oid(lambda oid: cmds.do(cmds.CherryPick, [oid]))

    def copy_to_clipboard(self):
        self.with_oid(lambda oid: qtutils.set_clipboard(oid))

    def create_branch(self):
        self.with_oid(lambda oid: createbranch.create_new_branch(revision=oid))

    def create_tag(self):
        self.with_oid(lambda oid: createtag.create_tag(ref=oid))

    def create_tarball(self):
        self.with_oid(lambda oid: archive.show_save_dialog(oid, parent=self))

    def show_diff(self):
        self.with_oid(lambda oid:
                difftool.diff_expression(self, oid + '^!',
                                         hide_expr=False, focus_tree=True))

    def show_dir_diff(self):
        self.with_oid(lambda oid:
                cmds.difftool_launch(left=oid, left_take_magic=True,
                                     dir_diff=True))

    def reset_branch_head(self):
        self.with_oid(lambda oid: cmds.do(cmds.ResetBranchHead, ref=oid))

    def reset_worktree(self):
        self.with_oid(lambda oid: cmds.do(cmds.ResetWorktree, ref=oid))

    def save_blob_dialog(self):
        self.with_oid(lambda oid: browse.BrowseDialog.browse(oid))

    def update_menu_actions(self, event):
        selected_items = self.selected_items()
        item = self.itemAt(event.pos())
        if item is None:
            self.clicked = commit = None
        else:
            self.clicked = commit = item.commit

        has_single_selection = len(selected_items) == 1
        has_selection = bool(selected_items)
        can_diff = bool(commit and has_single_selection and
                        commit is not selected_items[0].commit)

        if can_diff:
            self.selected = selected_items[0].commit
        else:
            self.selected = None

        self.menu_actions['diff_this_selected'].setEnabled(can_diff)
        self.menu_actions['diff_selected_this'].setEnabled(can_diff)
        self.menu_actions['diff_commit'].setEnabled(has_single_selection)
        self.menu_actions['diff_commit_all'].setEnabled(has_single_selection)

        self.menu_actions['cherry_pick'].setEnabled(has_single_selection)
        self.menu_actions['copy'].setEnabled(has_single_selection)
        self.menu_actions['create_branch'].setEnabled(has_single_selection)
        self.menu_actions['create_patch'].setEnabled(has_selection)
        self.menu_actions['create_tag'].setEnabled(has_single_selection)
        self.menu_actions['create_tarball'].setEnabled(has_single_selection)
        self.menu_actions['reset_branch_head'].setEnabled(has_single_selection)
        self.menu_actions['reset_worktree'].setEnabled(has_single_selection)
        self.menu_actions['save_blob'].setEnabled(has_single_selection)

    def context_menu_event(self, event):
        self.update_menu_actions(event)
        menu = qtutils.create_menu(N_('Actions'), self)
        menu.addAction(self.menu_actions['diff_this_selected'])
        menu.addAction(self.menu_actions['diff_selected_this'])
        menu.addAction(self.menu_actions['diff_commit'])
        menu.addAction(self.menu_actions['diff_commit_all'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['create_branch'])
        menu.addAction(self.menu_actions['create_tag'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['cherry_pick'])
        menu.addAction(self.menu_actions['create_patch'])
        menu.addAction(self.menu_actions['create_tarball'])
        menu.addSeparator()
        reset_menu = menu.addMenu(N_('Reset'))
        reset_menu.addAction(self.menu_actions['reset_branch_head'])
        reset_menu.addAction(self.menu_actions['reset_worktree'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['save_blob'])
        menu.addAction(self.menu_actions['copy'])
        menu.exec_(self.mapToGlobal(event.pos()))


def viewer_actions(widget):
    return {
        'diff_this_selected':
        qtutils.add_action(widget, N_('Diff this -> selected'),
                           widget.proxy.diff_this_selected),
        'diff_selected_this':
        qtutils.add_action(widget, N_('Diff selected -> this'),
                           widget.proxy.diff_selected_this),
        'create_branch':
        qtutils.add_action(widget, N_('Create Branch'),
                           widget.proxy.create_branch),
        'create_patch':
        qtutils.add_action(widget, N_('Create Patch'),
                           widget.proxy.create_patch),
        'create_tag':
        qtutils.add_action(widget, N_('Create Tag'),
                           widget.proxy.create_tag),
        'create_tarball':
        qtutils.add_action(widget, N_('Save As Tarball/Zip...'),
                           widget.proxy.create_tarball),
        'cherry_pick':
        qtutils.add_action(widget, N_('Cherry Pick'),
                           widget.proxy.cherry_pick),
        'diff_commit':
        qtutils.add_action(widget, N_('Launch Diff Tool'),
                           widget.proxy.show_diff, hotkeys.DIFF),
        'diff_commit_all':
        qtutils.add_action(widget, N_('Launch Directory Diff Tool'),
                           widget.proxy.show_dir_diff, hotkeys.DIFF_SECONDARY),
        'reset_branch_head':
        qtutils.add_action(widget, N_('Reset Branch Head'),
                           widget.proxy.reset_branch_head),
        'reset_worktree':
        qtutils.add_action(widget, N_('Reset Worktree'),
                           widget.proxy.reset_worktree),
        'save_blob':
        qtutils.add_action(widget, N_('Grab File...'),
                           widget.proxy.save_blob_dialog),
        'copy':
        qtutils.add_action(widget, N_('Copy SHA-1'),
                           widget.proxy.copy_to_clipboard,
                           QtGui.QKeySequence.Copy),
    }


class CommitTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, commit, parent=None):
        QtWidgets.QTreeWidgetItem.__init__(self, parent)
        self.commit = commit
        self.setText(0, commit.summary)
        self.setText(1, commit.author)
        self.setText(2, commit.authdate)


class CommitTreeWidget(standard.TreeWidget, ViewerMixin):

    diff_commits = Signal(object, object)

    def __init__(self, notifier, parent):
        standard.TreeWidget.__init__(self, parent=parent)
        ViewerMixin.__init__(self)

        self.setSelectionMode(self.ExtendedSelection)
        self.setHeaderLabels([N_('Summary'), N_('Author'), N_('Date, Time')])

        self.oidmap = {}
        self.menu_actions = None
        self.notifier = notifier
        self.selecting = False
        self.commits = []

        self.action_up = qtutils.add_action(self, N_('Go Up'),
                                            self.go_up, hotkeys.MOVE_UP)

        self.action_down = qtutils.add_action(self, N_('Go Down'),
                                              self.go_down, hotkeys.MOVE_DOWN)

        notifier.add_observer(diff.COMMITS_SELECTED, self.commits_selected)

        self.itemSelectionChanged.connect(self.selection_changed)

    # ViewerMixin
    def go_up(self):
        self.goto(self.itemAbove)

    def go_down(self):
        self.goto(self.itemBelow)

    def goto(self, finder):
        items = self.selected_items()
        item = items and items[0] or None
        if item is None:
            return
        found = finder(item)
        if found:
            self.select([found.commit.oid])

    def selected_commit_range(self):
        selected_items = self.selected_items()
        if not selected_items:
            return None, None
        return selected_items[-1].commit.oid, selected_items[0].commit.oid

    def set_selecting(self, selecting):
        self.selecting = selecting

    def selection_changed(self):
        items = self.selected_items()
        if not items:
            return
        self.set_selecting(True)
        self.notifier.notify_observers(diff.COMMITS_SELECTED,
                                       [i.commit for i in items])
        self.set_selecting(False)

    def commits_selected(self, commits):
        if self.selecting:
            return
        with qtutils.BlockSignals(self):
            self.select([commit.oid for commit in commits])

    def select(self, oids):
        if not oids:
            return
        self.clearSelection()
        for idx, oid in enumerate(oids):
            try:
                item = self.oidmap[oid]
            except KeyError:
                continue
            self.scrollToItem(item)
            item.setSelected(True)

    def adjust_columns(self):
        width = self.width()-20
        zero = width * 2 / 3
        onetwo = width / 6
        self.setColumnWidth(0, zero)
        self.setColumnWidth(1, onetwo)
        self.setColumnWidth(2, onetwo)

    def clear(self):
        QtWidgets.QTreeWidget.clear(self)
        self.oidmap.clear()
        self.commits = []

    def add_commits(self, commits):
        self.commits.extend(commits)
        items = []
        for c in reversed(commits):
            item = CommitTreeWidgetItem(c)
            items.append(item)
            self.oidmap[c.oid] = item
            for tag in c.tags:
                self.oidmap[tag] = item
        self.insertTopLevelItems(0, items)

    def create_patch(self):
        items = self.selectedItems()
        if not items:
            return
        oids = [item.commit.oid for item in reversed(items)]
        all_oids = [c.oid for c in self.commits]
        cmds.do(cmds.FormatPatch, oids, all_oids)

    # Qt overrides
    def contextMenuEvent(self, event):
        self.context_menu_event(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            event.accept()
            return
        QtWidgets.QTreeWidget.mousePressEvent(self, event)


class GitDAG(standard.MainWindow):
    """The git-dag widget."""
    updated = Signal()

    def __init__(self, model, ctx, parent=None, settings=None):
        super(GitDAG, self).__init__(parent)

        self.setMinimumSize(420, 420)

        # change when widgets are added/removed
        self.widget_version = 2
        self.model = model
        self.ctx = ctx
        self.settings = settings

        self.commits = {}
        self.commit_list = []
        self.selection = []

        self.thread = None
        self.revtext = completion.GitLogLineEdit()
        self.maxresults = standard.SpinBox()

        self.zoom_out = qtutils.create_action_button(
                tooltip=N_('Zoom Out'), icon=icons.zoom_out())

        self.zoom_in = qtutils.create_action_button(
                tooltip=N_('Zoom In'), icon=icons.zoom_in())

        self.zoom_to_fit = qtutils.create_action_button(
                tooltip=N_('Zoom to Fit'), icon=icons.zoom_fit_best())

        self.notifier = notifier = observable.Observable()
        self.notifier.refs_updated = refs_updated = 'refs_updated'
        self.notifier.add_observer(refs_updated, self.display)
        self.notifier.add_observer(filelist.HISTORIES_SELECTED,
                                   self.histories_selected)
        self.notifier.add_observer(filelist.DIFFTOOL_SELECTED,
                                   self.difftool_selected)
        self.notifier.add_observer(diff.COMMITS_SELECTED, self.commits_selected)

        self.treewidget = CommitTreeWidget(notifier, self)
        self.diffwidget = diff.DiffWidget(notifier, self, is_commit=True)
        self.filewidget = filelist.FileWidget(notifier, self)
        self.graphview = GraphView(notifier, self)

        self.proxy = FocusRedirectProxy(self.treewidget,
                                        self.graphview,
                                        self.filewidget)

        self.viewer_actions = actions = viewer_actions(self)
        self.treewidget.menu_actions = actions
        self.graphview.menu_actions = actions

        self.controls_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                            self.revtext, self.maxresults)

        self.controls_widget = QtWidgets.QWidget()
        self.controls_widget.setLayout(self.controls_layout)

        self.log_dock = qtutils.create_dock(N_('Log'), self, stretch=False)
        self.log_dock.setWidget(self.treewidget)
        log_dock_titlebar = self.log_dock.titleBarWidget()
        log_dock_titlebar.add_corner_widget(self.controls_widget)

        self.file_dock = qtutils.create_dock(N_('Files'), self)
        self.file_dock.setWidget(self.filewidget)

        self.diff_dock = qtutils.create_dock(N_('Diff'), self)
        self.diff_dock.setWidget(self.diffwidget)

        self.graph_controls_layout = qtutils.hbox(
                defs.no_margin, defs.button_spacing,
                self.zoom_out, self.zoom_in, self.zoom_to_fit,
                defs.spacing)

        self.graph_controls_widget = QtWidgets.QWidget()
        self.graph_controls_widget.setLayout(self.graph_controls_layout)

        self.graphview_dock = qtutils.create_dock(N_('Graph'), self)
        self.graphview_dock.setWidget(self.graphview)
        graph_titlebar = self.graphview_dock.titleBarWidget()
        graph_titlebar.add_corner_widget(self.graph_controls_widget)

        self.lock_layout_action = qtutils.add_action_bool(
                self, N_('Lock Layout'), self.set_lock_layout, False)

        self.refresh_action = qtutils.add_action(
                self, N_('Refresh'), self.refresh, hotkeys.REFRESH)

        # Create the application menu
        self.menubar = QtWidgets.QMenuBar(self)

        # View Menu
        self.view_menu = qtutils.create_menu(N_('View'), self.menubar)
        self.view_menu.addAction(self.refresh_action)

        self.view_menu.addAction(self.log_dock.toggleViewAction())
        self.view_menu.addAction(self.graphview_dock.toggleViewAction())
        self.view_menu.addAction(self.diff_dock.toggleViewAction())
        self.view_menu.addAction(self.file_dock.toggleViewAction())
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.lock_layout_action)

        self.menubar.addAction(self.view_menu.menuAction())
        self.setMenuBar(self.menubar)

        left = Qt.LeftDockWidgetArea
        right = Qt.RightDockWidgetArea
        self.addDockWidget(left, self.log_dock)
        self.addDockWidget(left, self.diff_dock)
        self.addDockWidget(right, self.graphview_dock)
        self.addDockWidget(right, self.file_dock)

        # Also re-loads dag.* from the saved state
        self.init_state(settings, self.resize_to_desktop)

        qtutils.connect_button(self.zoom_out, self.graphview.zoom_out)
        qtutils.connect_button(self.zoom_in, self.graphview.zoom_in)
        qtutils.connect_button(self.zoom_to_fit,
                               self.graphview.zoom_to_fit)

        self.treewidget.diff_commits.connect(self.diff_commits)
        self.graphview.diff_commits.connect(self.diff_commits)

        self.maxresults.editingFinished.connect(self.display)
        self.revtext.textChanged.connect(self.text_changed)

        self.revtext.activated.connect(self.display)
        self.revtext.enter.connect(self.display)
        self.revtext.down.connect(self.focus_tree)

        # The model is updated in another thread so use
        # signals/slots to bring control back to the main GUI thread
        self.model.add_observer(self.model.message_updated, self.updated.emit)
        self.updated.connect(self.model_updated, type=Qt.QueuedConnection)

        qtutils.add_action(self, 'Focus Input', self.focus_input, hotkeys.FOCUS)
        qtutils.add_close_action(self)

        self.set_context(ctx)

    def set_context(self, ctx):
        self.ctx = ctx

        # Update fields affected by model
        self.revtext.setText(ctx.ref)
        self.maxresults.setValue(ctx.count)
        self.update_window_title()

        if self.thread is not None:
            self.thread.stop()
        self.thread = ReaderThread(ctx, self)

        thread = self.thread
        thread.begin.connect(self.thread_begin, type=Qt.QueuedConnection)
        thread.status.connect(self.thread_status, type=Qt.QueuedConnection)
        thread.add.connect(self.add_commits, type=Qt.QueuedConnection)
        thread.end.connect(self.thread_end, type=Qt.QueuedConnection)

    def focus_input(self):
        self.revtext.setFocus()

    def focus_tree(self):
        self.treewidget.setFocus()

    def text_changed(self, txt):
        self.ctx.ref = txt
        self.update_window_title()

    def update_window_title(self):
        project = self.model.project
        if self.ctx.ref:
            self.setWindowTitle(N_('%(project)s: %(ref)s - DAG')
                                % dict(project=project, ref=self.ctx.ref))
        else:
            self.setWindowTitle(project + N_(' - DAG'))

    def export_state(self):
        state = standard.MainWindow.export_state(self)
        state['count'] = self.ctx.count
        return state

    def apply_state(self, state):
        result = standard.MainWindow.apply_state(self, state)
        try:
            count = state['count']
            if self.ctx.overridden('count'):
                count = self.ctx.count
        except:
            count = self.ctx.count
            result = False
        self.ctx.set_count(count)
        self.lock_layout_action.setChecked(state.get('lock_layout', False))
        return result

    def model_updated(self):
        self.display()

    def refresh(self):
        cmds.do(cmds.Refresh)

    def display(self):
        new_ref = self.revtext.value()
        new_count = self.maxresults.value()

        self.thread.stop()
        self.ctx.set_ref(new_ref)
        self.ctx.set_count(new_count)
        self.thread.start()

    def show(self):
        standard.MainWindow.show(self)
        self.treewidget.adjust_columns()

    def commits_selected(self, commits):
        if commits:
            self.selection = commits

    def clear(self):
        self.commits.clear()
        self.commit_list = []
        self.graphview.clear()
        self.treewidget.clear()

    def add_commits(self, commits):
        self.commit_list.extend(commits)
        # Keep track of commits
        for commit_obj in commits:
            self.commits[commit_obj.oid] = commit_obj
            for tag in commit_obj.tags:
                self.commits[tag] = commit_obj
        self.graphview.add_commits(commits)
        self.treewidget.add_commits(commits)

    def thread_begin(self):
        self.clear()

    def thread_end(self):
        self.focus_tree()
        self.restore_selection()

    def thread_status(self, successful):
        self.revtext.hint.set_error(not successful)

    def restore_selection(self):
        selection = self.selection
        try:
            commit_obj = self.commit_list[-1]
        except IndexError:
            # No commits, exist, early-out
            return

        new_commits = [self.commits.get(s.oid, None) for s in selection]
        new_commits = [c for c in new_commits if c is not None]
        if new_commits:
            # The old selection exists in the new state
            self.notifier.notify_observers(diff.COMMITS_SELECTED, new_commits)
        else:
            # The old selection is now empty.  Select the top-most commit
            self.notifier.notify_observers(diff.COMMITS_SELECTED, [commit_obj])

        self.graphview.update_scene_rect()
        self.graphview.set_initial_view()

    def diff_commits(self, a, b):
        paths = self.ctx.paths()
        if paths:
            cmds.difftool_launch(left=a, right=b, paths=paths)
        else:
            difftool.diff_commits(self, a, b)

    # Qt overrides
    def closeEvent(self, event):
        self.revtext.close_popup()
        self.thread.stop()
        standard.MainWindow.closeEvent(self, event)

    def resizeEvent(self, e):
        standard.MainWindow.resizeEvent(self, e)
        self.treewidget.adjust_columns()

    def histories_selected(self, histories):
        argv = [self.model.currentbranch, '--']
        argv.extend(histories)
        text = core.list2cmdline(argv)
        self.revtext.setText(text)
        self.display()

    def difftool_selected(self, files):
        bottom, top = self.treewidget.selected_commit_range()
        if not top:
            return
        cmds.difftool_launch(left=bottom, left_take_parent=True,
                             right=top, paths=files)


class ReaderThread(QtCore.QThread):
    begin = Signal()
    add = Signal(object)
    end = Signal()
    status = Signal(object)

    def __init__(self, ctx, parent):
        QtCore.QThread.__init__(self, parent)
        self.ctx = ctx
        self._abort = False
        self._stop = False
        self._mutex = QtCore.QMutex()
        self._condition = QtCore.QWaitCondition()

    def run(self):
        repo = dag.RepoReader(self.ctx)
        repo.reset()
        self.begin.emit()
        commits = []
        for c in repo:
            self._mutex.lock()
            if self._stop:
                self._condition.wait(self._mutex)
            self._mutex.unlock()
            if self._abort:
                repo.reset()
                return
            commits.append(c)
            if len(commits) >= 512:
                self.add.emit(commits)
                commits = []

        self.status.emit(repo.returncode == 0)
        if commits:
            self.add.emit(commits)
        self.end.emit()

    def start(self):
        self._abort = False
        self._stop = False
        QtCore.QThread.start(self)

    def pause(self):
        self._mutex.lock()
        self._stop = True
        self._mutex.unlock()

    def resume(self):
        self._mutex.lock()
        self._stop = False
        self._mutex.unlock()
        self._condition.wakeOne()

    def stop(self):
        self._abort = True
        self.wait()


class Cache(object):
    pass


class Edge(QtWidgets.QGraphicsItem):
    item_type = QtWidgets.QGraphicsItem.UserType + 1

    def __init__(self, source, dest):

        QtWidgets.QGraphicsItem.__init__(self)

        self.setAcceptedMouseButtons(Qt.NoButton)
        self.source = source
        self.dest = dest
        self.commit = source.commit
        self.setZValue(-2)

        dest_pt = Commit.item_bbox.center()

        self.source_pt = self.mapFromItem(self.source, dest_pt)
        self.dest_pt = self.mapFromItem(self.dest, dest_pt)
        self.line = QtCore.QLineF(self.source_pt, self.dest_pt)

        width = self.dest_pt.x() - self.source_pt.x()
        height = self.dest_pt.y() - self.source_pt.y()
        rect = QtCore.QRectF(self.source_pt, QtCore.QSizeF(width, height))
        self.bound = rect.normalized()

        # Choose a new color for new branch edges
        if self.source.x() < self.dest.x():
            color = EdgeColor.cycle()
            line = Qt.SolidLine
        elif self.source.x() != self.dest.x():
            color = EdgeColor.current()
            line = Qt.SolidLine
        else:
            color = EdgeColor.current()
            line = Qt.SolidLine

        self.pen = QtGui.QPen(color, 4.0, line, Qt.SquareCap, Qt.RoundJoin)

    # Qt overrides
    def type(self):
        return self.item_type

    def boundingRect(self):
        return self.bound

    def paint(self, painter, option, widget):
        QRectF = QtCore.QRectF
        QPointF = QtCore.QPointF

        arc_rect = 10
        connector_length = 5

        painter.setPen(self.pen)
        path = QtGui.QPainterPath()

        if self.source.x() == self.dest.x():
            path.moveTo(self.source.x(), self.source.y())
            path.lineTo(self.dest.x(), self.dest.y())
            painter.drawPath(path)
        else:
            # Define points starting from source
            point1 = QPointF(self.source.x(), self.source.y())
            point2 = QPointF(point1.x(), point1.y() - connector_length)
            point3 = QPointF(point2.x() + arc_rect, point2.y() - arc_rect)

            # Define points starting from dest
            point4 = QPointF(self.dest.x(), self.dest.y())
            point5 = QPointF(point4.x(), point3.y() - arc_rect)
            point6 = QPointF(point5.x() - arc_rect, point5.y() + arc_rect)

            start_angle_arc1 = 180
            span_angle_arc1 = 90
            start_angle_arc2 = 90
            span_angle_arc2 = -90

            # If the dest is at the left of the source, then we
            # need to reverse some values
            if self.source.x() > self.dest.x():
                point5 = QPointF(point4.x(), point4.y() + connector_length)
                point6 = QPointF(point5.x() + arc_rect, point5.y() + arc_rect)
                point3 = QPointF(self.source.x() - arc_rect, point6.y())
                point2 = QPointF(self.source.x(), point3.y() + arc_rect)

                span_angle_arc1 = 90

            path.moveTo(point1)
            path.lineTo(point2)
            path.arcTo(QRectF(point2, point3),
                       start_angle_arc1, span_angle_arc1)
            path.lineTo(point6)
            path.arcTo(QRectF(point6, point5),
                       start_angle_arc2, span_angle_arc2)
            path.lineTo(point4)
            painter.drawPath(path)


class EdgeColor(object):
    """An edge color factory"""

    current_color_index = 0
    colors = [
                QtGui.QColor(Qt.red),
                QtGui.QColor(Qt.green),
                QtGui.QColor(Qt.blue),
                QtGui.QColor(Qt.black),
                QtGui.QColor(Qt.darkRed),
                QtGui.QColor(Qt.darkGreen),
                QtGui.QColor(Qt.darkBlue),
                QtGui.QColor(Qt.cyan),
                QtGui.QColor(Qt.magenta),
                # Orange; Qt.yellow is too low-contrast
                qtutils.rgba(0xff, 0x66, 0x00),
                QtGui.QColor(Qt.gray),
                QtGui.QColor(Qt.darkCyan),
                QtGui.QColor(Qt.darkMagenta),
                QtGui.QColor(Qt.darkYellow),
                QtGui.QColor(Qt.darkGray),
             ]

    @classmethod
    def cycle(cls):
        cls.current_color_index += 1
        cls.current_color_index %= len(cls.colors)
        color = cls.colors[cls.current_color_index]
        color.setAlpha(128)
        return color

    @classmethod
    def current(cls):
        return cls.colors[cls.current_color_index]

    @classmethod
    def reset(cls):
        cls.current_color_index = 0


class Commit(QtWidgets.QGraphicsItem):
    item_type = QtWidgets.QGraphicsItem.UserType + 2
    commit_radius = 12.0
    merge_radius = 18.0

    item_shape = QtGui.QPainterPath()
    item_shape.addRect(commit_radius/-2.0,
                       commit_radius/-2.0,
                       commit_radius, commit_radius)
    item_bbox = item_shape.boundingRect()

    inner_rect = QtGui.QPainterPath()
    inner_rect.addRect(commit_radius/-2.0 + 2.0,
                       commit_radius/-2.0 + 2.0,
                       commit_radius - 4.0,
                       commit_radius - 4.0)
    inner_rect = inner_rect.boundingRect()

    commit_color = QtGui.QColor(Qt.white)
    outline_color = commit_color.darker()
    merge_color = QtGui.QColor(Qt.lightGray)

    commit_selected_color = QtGui.QColor(Qt.green)
    selected_outline_color = commit_selected_color.darker()

    commit_pen = QtGui.QPen()
    commit_pen.setWidth(1.0)
    commit_pen.setColor(outline_color)

    def __init__(self, commit,
                 notifier,
                 selectable=QtWidgets.QGraphicsItem.ItemIsSelectable,
                 cursor=Qt.PointingHandCursor,
                 xpos=commit_radius/2.0 + 1.0,
                 cached_commit_color=commit_color,
                 cached_merge_color=merge_color):

        QtWidgets.QGraphicsItem.__init__(self)

        self.commit = commit
        self.notifier = notifier

        self.setZValue(0)
        self.setFlag(selectable)
        self.setCursor(cursor)
        self.setToolTip(commit.oid[:7] + ': ' + commit.summary)

        if commit.tags:
            self.label = label = Label(commit)
            label.setParentItem(self)
            label.setPos(xpos, -self.commit_radius/2.0)
        else:
            self.label = None

        if len(commit.parents) > 1:
            self.brush = cached_merge_color
        else:
            self.brush = cached_commit_color

        self.pressed = False
        self.dragged = False

    def blockSignals(self, blocked):
        self.notifier.notification_enabled = not blocked

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            # Broadcast selection to other widgets
            selected_items = self.scene().selectedItems()
            commits = [item.commit for item in selected_items]
            self.scene().parent().set_selecting(True)
            self.notifier.notify_observers(diff.COMMITS_SELECTED, commits)
            self.scene().parent().set_selecting(False)

            # Cache the pen for use in paint()
            if value:
                self.brush = self.commit_selected_color
                color = self.selected_outline_color
            else:
                if len(self.commit.parents) > 1:
                    self.brush = self.merge_color
                else:
                    self.brush = self.commit_color
                color = self.outline_color
            commit_pen = QtGui.QPen()
            commit_pen.setWidth(1.0)
            commit_pen.setColor(color)
            self.commit_pen = commit_pen

        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

    def type(self):
        return self.item_type

    def boundingRect(self, rect=item_bbox):
        return rect

    def shape(self):
        return self.item_shape

    def paint(self, painter, option, widget,
              inner=inner_rect,
              cache=Cache):

        # Do not draw outside the exposed rect
        painter.setClipRect(option.exposedRect)

        # Draw ellipse
        painter.setPen(self.commit_pen)
        painter.setBrush(self.brush)
        painter.drawEllipse(inner)

    def mousePressEvent(self, event):
        QtWidgets.QGraphicsItem.mousePressEvent(self, event)
        self.pressed = True
        self.selected = self.isSelected()

    def mouseMoveEvent(self, event):
        if self.pressed:
            self.dragged = True
        QtWidgets.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        QtWidgets.QGraphicsItem.mouseReleaseEvent(self, event)
        if (not self.dragged and
                self.selected and
                event.button() == Qt.LeftButton):
            return
        self.pressed = False
        self.dragged = False


class Label(QtWidgets.QGraphicsItem):
    item_type = QtWidgets.QGraphicsItem.UserType + 3

    width = 72
    height = 18

    item_shape = QtGui.QPainterPath()
    item_shape.addRect(0, 0, width, height)
    item_bbox = item_shape.boundingRect()

    text_options = QtGui.QTextOption()
    text_options.setAlignment(Qt.AlignCenter)
    text_options.setAlignment(Qt.AlignVCenter)

    def __init__(self, commit,
                 other_color=QtGui.QColor(Qt.white),
                 head_color=QtGui.QColor(Qt.green)):
        QtWidgets.QGraphicsItem.__init__(self)
        self.setZValue(-1)

        # Starts with enough space for two tags. Any more and the commit
        # needs to be taller to accommodate.
        self.commit = commit

        if 'HEAD' in commit.tags:
            self.color = head_color
        else:
            self.color = other_color

        self.color.setAlpha(180)
        self.pen = QtGui.QPen()
        self.pen.setColor(self.color.darker())
        self.pen.setWidth(1.0)

    def type(self):
        return self.item_type

    def boundingRect(self, rect=item_bbox):
        return rect

    def shape(self):
        return self.item_shape

    def paint(self, painter, option, widget,
              text_opts=text_options,
              black=Qt.black,
              cache=Cache):
        try:
            font = cache.label_font
        except AttributeError:
            font = cache.label_font = QtWidgets.QApplication.font()
            font.setPointSize(6)

        # Draw tags
        painter.setBrush(self.color)
        painter.setPen(self.pen)
        painter.setFont(font)

        current_width = 0

        QRectF = QtCore.QRectF
        for tag in self.commit.tags:
            text_rect = painter.boundingRect(
                    QRectF(current_width, 0, 0, 0), Qt.TextSingleLine, tag)
            box_rect = text_rect.adjusted(-1, -1, 1, 1)
            painter.drawRoundedRect(box_rect, 2, 2)
            painter.drawText(text_rect, Qt.TextSingleLine, tag)
            current_width += text_rect.width() + 5


class GraphView(QtWidgets.QGraphicsView, ViewerMixin):

    diff_commits = Signal(object, object)

    x_min = 24
    x_max = 0
    y_min = 24

    x_adjust = Commit.commit_radius*4/3
    y_adjust = Commit.commit_radius*4/3

    x_off = 18
    y_off = 24

    def __init__(self, notifier, parent):
        QtWidgets.QGraphicsView.__init__(self, parent)
        ViewerMixin.__init__(self)

        highlight = self.palette().color(QtGui.QPalette.Highlight)
        Commit.commit_selected_color = highlight
        Commit.selected_outline_color = highlight.darker()

        self.selection_list = []
        self.menu_actions = None
        self.notifier = notifier
        self.commits = []
        self.items = {}
        self.saved_matrix = self.transform()

        self.x_offsets = collections.defaultdict(lambda: self.x_min)

        self.is_panning = False
        self.pressed = False
        self.selecting = False
        self.last_mouse = [0, 0]
        self.zoom = 2
        self.setDragMode(self.RubberBandDrag)

        scene = QtWidgets.QGraphicsScene(self)
        scene.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        self.setScene(scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setViewportUpdateMode(self.BoundingRectViewportUpdate)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setBackgroundBrush(QtGui.QColor(Qt.white))

        qtutils.add_action(self, N_('Zoom In'), self.zoom_in,
                           hotkeys.ZOOM_IN, hotkeys.ZOOM_IN_SECONDARY)

        qtutils.add_action(self, N_('Zoom Out'), self.zoom_out,
                           hotkeys.ZOOM_OUT)

        qtutils.add_action(self, N_('Zoom to Fit'),
                           self.zoom_to_fit, hotkeys.FIT)

        qtutils.add_action(self, N_('Select Parent'),
                           self.select_parent, hotkeys.MOVE_DOWN_TERTIARY)

        qtutils.add_action(self, N_('Select Oldest Parent'),
                           self.select_oldest_parent, hotkeys.MOVE_DOWN)

        qtutils.add_action(self, N_('Select Child'),
                           self.select_child, hotkeys.MOVE_UP_TERTIARY)

        qtutils.add_action(self, N_('Select Newest Child'),
                           self.select_newest_child, hotkeys.MOVE_UP)

        notifier.add_observer(diff.COMMITS_SELECTED, self.commits_selected)

    def clear(self):
        EdgeColor.reset()
        self.scene().clear()
        self.selection_list = []
        self.items.clear()
        self.x_offsets.clear()
        self.x_max = 24
        self.y_min = 24
        self.commits = []

    # ViewerMixin interface
    def selected_items(self):
        """Return the currently selected items"""
        return self.scene().selectedItems()

    def zoom_in(self):
        self.scale_view(1.5)

    def zoom_out(self):
        self.scale_view(1.0/1.5)

    def commits_selected(self, commits):
        if self.selecting:
            return
        self.select([commit.oid for commit in commits])

    def select(self, oids):
        """Select the item for the oids"""
        self.scene().clearSelection()
        for oid in oids:
            try:
                item = self.items[oid]
            except KeyError:
                continue
            item.blockSignals(True)
            item.setSelected(True)
            item.blockSignals(False)
            item_rect = item.sceneTransform().mapRect(item.boundingRect())
            self.ensureVisible(item_rect)

    def get_item_by_generation(self, commits, criteria_fn):
        """Return the item for the commit matching criteria"""
        if not commits:
            return None
        generation = None
        for commit in commits:
            if (generation is None or
                    criteria_fn(generation, commit.generation)):
                oid = commit.oid
                generation = commit.generation
        try:
            return self.items[oid]
        except KeyError:
            return None

    def oldest_item(self, commits):
        """Return the item for the commit with the oldest generation number"""
        return self.get_item_by_generation(commits, lambda a, b: a > b)

    def newest_item(self, commits):
        """Return the item for the commit with the newest generation number"""
        return self.get_item_by_generation(commits, lambda a, b: a < b)

    def create_patch(self):
        items = self.selected_items()
        if not items:
            return
        selected_commits = self.sort_by_generation([n.commit for n in items])
        oids = [c.oid for c in selected_commits]
        all_oids = [c.oid for c in self.commits]
        cmds.do(cmds.FormatPatch, oids, all_oids)

    def select_parent(self):
        """Select the parent with the newest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self.newest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        self.ensureVisible(
                parent_item.mapRectToScene(parent_item.boundingRect()))

    def select_oldest_parent(self):
        """Select the parent with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self.oldest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        scene_rect = parent_item.mapRectToScene(parent_item.boundingRect())
        self.ensureVisible(scene_rect)

    def select_child(self):
        """Select the child with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        child_item = self.oldest_item(selected_item.commit.children)
        if child_item is None:
            return
        selected_item.setSelected(False)
        child_item.setSelected(True)
        scene_rect = child_item.mapRectToScene(child_item.boundingRect())
        self.ensureVisible(scene_rect)

    def select_newest_child(self):
        """Select the Nth child with the newest generation number (N > 1)"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        if len(selected_item.commit.children) > 1:
            children = selected_item.commit.children[1:]
        else:
            children = selected_item.commit.children
        child_item = self.newest_item(children)
        if child_item is None:
            return
        selected_item.setSelected(False)
        child_item.setSelected(True)
        scene_rect = child_item.mapRectToScene(child_item.boundingRect())
        self.ensureVisible(scene_rect)

    def set_initial_view(self):
        self_commits = self.commits
        self_items = self.items

        items = self.selected_items()
        if not items:
            commits = self_commits[-8:]
            items = [self_items[c.oid] for c in commits]

        self.fit_view_to_items(items)

    def zoom_to_fit(self):
        """Fit selected items into the viewport"""

        items = self.selected_items()
        self.fit_view_to_items(items)

    def fit_view_to_items(self, items):
        if not items:
            rect = self.scene().itemsBoundingRect()
        else:
            x_min = y_min = maxsize
            x_max = y_max = -maxsize

            for item in items:
                pos = item.pos()
                item_rect = item.boundingRect()
                x_off = item_rect.width() * 5
                y_off = item_rect.height() * 10
                x_min = min(x_min, pos.x())
                y_min = min(y_min, pos.y()-y_off)
                x_max = max(x_max, pos.x()+x_off)
                y_max = max(y_max, pos.y())
            rect = QtCore.QRectF(x_min, y_min, x_max-x_min, y_max-y_min)

        x_adjust = GraphView.x_adjust
        y_adjust = GraphView.y_adjust

        rect.setX(rect.x() - x_adjust)
        rect.setY(rect.y() - y_adjust)
        rect.setHeight(rect.height() + y_adjust*2)
        rect.setWidth(rect.width() + x_adjust*2)

        self.fitInView(rect, Qt.KeepAspectRatio)
        self.scene().invalidate()

    def save_selection(self, event):
        if event.button() != Qt.LeftButton:
            return
        elif Qt.ShiftModifier != event.modifiers():
            return
        self.selection_list = self.selected_items()

    def restore_selection(self, event):
        if Qt.ShiftModifier != event.modifiers():
            return
        for item in self.selection_list:
            item.setSelected(True)

    def handle_event(self, event_handler, event):
        self.save_selection(event)
        event_handler(self, event)
        self.restore_selection(event)
        self.update()

    def set_selecting(self, selecting):
        self.selecting = selecting

    def pan(self, event):
        pos = event.pos()
        dx = pos.x() - self.mouse_start[0]
        dy = pos.y() - self.mouse_start[1]

        if dx == 0 and dy == 0:
            return

        rect = QtCore.QRect(0, 0, abs(dx), abs(dy))
        delta = self.mapToScene(rect).boundingRect()

        tx = delta.width()
        if dx < 0.0:
            tx = -tx

        ty = delta.height()
        if dy < 0.0:
            ty = -ty

        matrix = self.transform()
        matrix.reset()
        matrix *= self.saved_matrix
        matrix.translate(tx, ty)

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setTransform(matrix)

    def wheel_zoom(self, event):
        """Handle mouse wheel zooming."""
        delta = qtcompat.wheel_delta(event)
        zoom = math.pow(2.0, delta/512.0)
        factor = (self.transform()
                  .scale(zoom, zoom)
                  .mapRect(QtCore.QRectF(0.0, 0.0, 1.0, 1.0))
                  .width())
        if factor < 0.014 or factor > 42.0:
            return
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.zoom = zoom
        self.scale(zoom, zoom)

    def wheel_pan(self, event):
        """Handle mouse wheel panning."""
        unit = QtCore.QRectF(0.0, 0.0, 1.0, 1.0)
        factor = 1.0 / self.transform().mapRect(unit).width()
        tx, ty = qtcompat.wheel_translation(event)

        matrix = self.transform().translate(tx * factor, ty * factor)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setTransform(matrix)

    def scale_view(self, scale):
        factor = (self.transform()
                  .scale(scale, scale)
                  .mapRect(QtCore.QRectF(0, 0, 1, 1))
                  .width())
        if factor < 0.07 or factor > 100.0:
            return
        self.zoom = scale

        adjust_scrollbars = True
        scrollbar = self.verticalScrollBar()
        if scrollbar:
            value = scrollbar.value()
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            distance = value - min_
            nonzero_range = range_ > 0.1
            if nonzero_range:
                scrolloffset = distance/range_
            else:
                adjust_scrollbars = False

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.scale(scale, scale)

        scrollbar = self.verticalScrollBar()
        if scrollbar and adjust_scrollbars:
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            value = min_ + int(float(range_) * scrolloffset)
            scrollbar.setValue(value)

    def add_commits(self, commits):
        """Traverse commits and add them to the view."""
        self.commits.extend(commits)
        scene = self.scene()
        for commit in commits:
            item = Commit(commit, self.notifier)
            self.items[commit.oid] = item
            for ref in commit.tags:
                self.items[ref] = item
            scene.addItem(item)

        self.layout_commits()
        self.link(commits)

    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        for commit in commits:
            try:
                commit_item = self.items[commit.oid]
            except KeyError:
                # TODO - Handle truncated history viewing
                continue
            for parent in reversed(commit.parents):
                try:
                    parent_item = self.items[parent.oid]
                except KeyError:
                    # TODO - Handle truncated history viewing
                    continue
                edge = Edge(parent_item, commit_item)
                scene.addItem(edge)

    def layout_commits(self):
        positions = self.position_nodes()
        for oid, (x, y) in positions.items():
            item = self.items[oid]
            item.setPos(x, y)

    """Commit node layout technique

    Nodes are aligned by a mesh. Node row is generation number of
corresponding commit. Columns are distributed using the algorithm described
below.

    Column assignment algorithm

    The algorithm traverses nodes in generation ascend order. This guarantees
that a node will be visited after all its parents.

    The set of occupied columns are maintained during work. Initially it is
empty and no node occupied a column. Empty columns are selected by request in
index ascend order starting from 0. Each column has its reference counter.
Being allocated a column is assigned 1 reference. When a counter reaches 0 the
column is removed from occupied column set. Currently no counter becomes
gather than 1, but leave_column method is written in generic way.

    Initialization is performed by reset_columns method. Column allocation is
implemented in alloc_column method. Initialization and main loop are in
recompute_columns method.

    Actions for each node are follow.
    1. If the node was not assigned a column then it is assigned empty one.
    2. Handle columns occupied by parents. Handling is leaving columns of some
parents. One of parents occupies same column as the node. The column should not
be left. Hence if the node is not a merge then nothing is done during the step.
Other parents of merge node are processed in follow way.
    2.1. If parent is fork then a brother node could be at column of the
parent. So, the column cannot be left. Note that the brother itself or one of
its descendant will perform the column leaving at appropriate time.
    2.2 The parent may not occupy a column. This is possible when some commits
were not added to the DAG (during repository reading, for instance). No column
should be left.
    2.3. Leave column of the parent. The parent is a regular commit. Its
outgoing edge is turned form its column to column of the node. Hence, the
column is left.
    3. Define columns of children. If a child have a column assigned then it
should no be overridden. One of children is assigned same column as the node.
If the node is a fork then the child is chosen in generation descent order.
This is a heuristic and it only affects resulting appearance of the graph.
Other children are assigned empty columns in same order. It is the heuristic
too.

    After the algorithm was done all commit graphic items are assigned
coordinates based on its row and column multiplied by the coefficient.
    """

    def reset_columns(self):
        for node in self.commits:
            node.column = None
        self.columns = {}

    def alloc_column(self):
        columns = self.columns
        for c in count(0):
            if c not in columns:
                break
        columns[c] = 1
        return c

    def leave_column(self, column):
        count = self.columns[column]
        if count == 1:
            del self.columns[column]
        else:
            self.columns[column] = count - 1

    def recompute_columns(self):
        self.reset_columns()

        for node in self.sort_by_generation(list(self.commits)):
            if node.column is None:
                # Node is either root or its parent is not in items. The last
                # happens when tree loading is in progress. Allocate new
                # columns for such nodes.
                node.column = self.alloc_column()

            if node.is_merge():
                for parent in node.parents:
                    if parent.is_fork():
                        continue
                    if parent.column == node.column:
                        continue
                    if parent.column is None:
                        # Parent is in not among commits being layoutted, so it
                        # have no column.
                        continue
                    self.leave_column(parent.column)

            # Propagate column to children which are still without one.
            if node.is_fork():
                sorted_children = sorted(node.children,
                                         key=lambda c: c.generation,
                                         reverse=True)
                citer = iter(sorted_children)
                for child in citer:
                    if child.column is None:
                        # Top most child occupies column of parent.
                        child.column = node.column
                        break

                # Rest children are allocated new column.
                for child in citer:
                    if child.column is None:
                        child.column = self.alloc_column()
            elif node.children:
                child = node.children[0]
                if child.column is None:
                    child.column = node.column

    def position_nodes(self):
        self.recompute_columns()

        x_max = self.x_max
        x_min = self.x_min
        x_off = self.x_off
        y_off = self.y_off
        y_min = y_off

        positions = {}

        for node in self.commits:
            x_pos = x_min + node.column * x_off
            y_pos = y_off - node.generation * y_off

            positions[node.oid] = (x_pos, y_pos)

            x_max = max(x_max, x_pos)
            y_min = min(y_min, y_pos)

        self.x_max = x_max
        self.y_min = y_min

        return positions

    def update_scene_rect(self):
        y_min = self.y_min
        x_max = self.x_max
        self.scene().setSceneRect(-GraphView.x_adjust,
                                  y_min-GraphView.y_adjust,
                                  x_max + GraphView.x_adjust,
                                  abs(y_min) + GraphView.y_adjust)

    def sort_by_generation(self, commits):
        if len(commits) < 2:
            return commits
        commits.sort(key=lambda x: x.generation)
        return commits

    # Qt overrides
    def contextMenuEvent(self, event):
        self.context_menu_event(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MidButton:
            pos = event.pos()
            self.mouse_start = [pos.x(), pos.y()]
            self.saved_matrix = self.transform()
            self.is_panning = True
            return
        if event.button() == Qt.RightButton:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.pressed = True
        self.handle_event(QtWidgets.QGraphicsView.mousePressEvent, event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self.is_panning:
            self.pan(event)
            return
        self.last_mouse[0] = pos.x()
        self.last_mouse[1] = pos.y()
        self.handle_event(QtWidgets.QGraphicsView.mouseMoveEvent, event)
        if self.pressed:
            self.viewport().repaint()

    def mouseReleaseEvent(self, event):
        self.pressed = False
        if event.button() == Qt.MidButton:
            self.is_panning = False
            return
        self.handle_event(QtWidgets.QGraphicsView.mouseReleaseEvent, event)
        self.selection_list = []
        self.viewport().repaint()

    def wheelEvent(self, event):
        """Handle Qt mouse wheel events."""
        if event.modifiers() & Qt.ControlModifier:
            self.wheel_zoom(event)
        else:
            self.wheel_pan(event)


# Glossary
# ========
# oid -- Git objects IDs (i.e. SHA-1 IDs)
# ref -- Git references that resolve to a commit-ish (HEAD, branches, tags)
