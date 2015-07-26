from __future__ import division, absolute_import, unicode_literals

import collections
import subprocess
import math

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtCore import QPointF
from PyQt4.QtCore import QRectF

from cola import cmds
from cola import difftool
from cola import observable
from cola import qtutils
from cola.i18n import N_
from cola.models import dag
from cola.widgets import archive
from cola.widgets import browse
from cola.widgets import completion
from cola.widgets import createbranch
from cola.widgets import createtag
from cola.widgets import defs
from cola.widgets import diff
from cola.widgets import filelist
from cola.widgets import standard
from cola.compat import ustr


def git_dag(model, args=None, settings=None):
    """Return a pre-populated git DAG widget."""
    branch = model.currentbranch
    # disambiguate between branch names and filenames by using '--'
    branch_doubledash = branch and (branch + ' --') or ''
    ctx = dag.DAG(branch_doubledash, 1000)
    ctx.set_arguments(args)

    view = GitDAG(model, ctx, settings=settings)
    if ctx.ref:
        view.display()
    return view


class ViewerMixin(object):
    """Implementations must provide selected_items()"""

    def __init__(self):
        self.selected = None
        self.clicked = None
        self.menu_actions = self.context_menu_actions()

    def selected_item(self):
        """Return the currently selected item"""
        selected_items = self.selected_items()
        if not selected_items:
            return None
        return selected_items[0]

    def selected_sha1(self):
        item = self.selected_item()
        if item is None:
            return None
        return item.commit.sha1

    def selected_sha1s(self):
        return [i.commit for i in self.selected_items()]

    def diff_selected_this(self):
        clicked_sha1 = self.clicked.sha1
        selected_sha1 = self.selected.sha1
        self.emit(SIGNAL('diff_commits(PyQt_PyObject,PyQt_PyObject)'),
                  selected_sha1, clicked_sha1)

    def diff_this_selected(self):
        clicked_sha1 = self.clicked.sha1
        selected_sha1 = self.selected.sha1
        self.emit(SIGNAL('diff_commits(PyQt_PyObject,PyQt_PyObject)'),
                  clicked_sha1, selected_sha1)

    def cherry_pick(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        cmds.do(cmds.CherryPick, [sha1])

    def copy_to_clipboard(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        qtutils.set_clipboard(sha1)

    def create_branch(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        createbranch.create_new_branch(revision=sha1)

    def create_tag(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        createtag.create_tag(ref=sha1)

    def create_tarball(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        short_sha1 = sha1[:7]
        archive.GitArchiveDialog.save_hashed_objects(sha1, short_sha1, self)

    def save_blob_dialog(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        return browse.BrowseDialog.browse(sha1)

    def context_menu_actions(self):
        return {
        'diff_this_selected':
            qtutils.add_action(self, N_('Diff this -> selected'),
                               self.diff_this_selected),
        'diff_selected_this':
            qtutils.add_action(self, N_('Diff selected -> this'),
                               self.diff_selected_this),
        'create_branch':
            qtutils.add_action(self, N_('Create Branch'),
                               self.create_branch),
        'create_patch':
            qtutils.add_action(self, N_('Create Patch'),
                               self.create_patch),
        'create_tag':
            qtutils.add_action(self, N_('Create Tag'),
                               self.create_tag),
        'create_tarball':
            qtutils.add_action(self, N_('Save As Tarball/Zip...'),
                               self.create_tarball),
        'cherry_pick':
            qtutils.add_action(self, N_('Cherry Pick'),
                               self.cherry_pick),
        'save_blob':
            qtutils.add_action(self, N_('Grab File...'),
                               self.save_blob_dialog),
        'copy':
            qtutils.add_action(self, N_('Copy SHA-1'),
                               self.copy_to_clipboard,
                               QtGui.QKeySequence.Copy),
        }

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

        self.menu_actions['create_branch'].setEnabled(has_single_selection)
        self.menu_actions['create_tag'].setEnabled(has_single_selection)

        self.menu_actions['cherry_pick'].setEnabled(has_single_selection)
        self.menu_actions['create_patch'].setEnabled(has_selection)
        self.menu_actions['create_tarball'].setEnabled(has_single_selection)

        self.menu_actions['save_blob'].setEnabled(has_single_selection)
        self.menu_actions['copy'].setEnabled(has_single_selection)

    def context_menu_event(self, event):
        self.update_menu_actions(event)
        menu = QtGui.QMenu(self)
        menu.addAction(self.menu_actions['diff_this_selected'])
        menu.addAction(self.menu_actions['diff_selected_this'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['create_branch'])
        menu.addAction(self.menu_actions['create_tag'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['cherry_pick'])
        menu.addAction(self.menu_actions['create_patch'])
        menu.addAction(self.menu_actions['create_tarball'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['save_blob'])
        menu.addAction(self.menu_actions['copy'])
        menu.exec_(self.mapToGlobal(event.pos()))


class CommitTreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, commit, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        self.commit = commit
        self.setText(0, commit.summary)
        self.setText(1, commit.author)
        self.setText(2, commit.authdate)


class CommitTreeWidget(ViewerMixin, standard.TreeWidget):

    def __init__(self, notifier, parent):
        standard.TreeWidget.__init__(self, parent)
        ViewerMixin.__init__(self)

        self.setSelectionMode(self.ContiguousSelection)
        self.setHeaderLabels([N_('Summary'), N_('Author'), N_('Date, Time')])

        self.sha1map = {}
        self.notifier = notifier
        self.selecting = False
        self.commits = []

        self.action_up = qtutils.add_action(self, N_('Go Up'), self.go_up,
                                            Qt.Key_K)

        self.action_down = qtutils.add_action(self, N_('Go Down'), self.go_down,
                                              Qt.Key_J)

        notifier.add_observer(diff.COMMITS_SELECTED, self.commits_selected)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.selection_changed)

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
            self.select([found.commit.sha1])

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
            self.select([commit.sha1 for commit in commits])

    def select(self, sha1s):
        if not sha1s:
            return
        self.clearSelection()
        for idx, sha1 in enumerate(sha1s):
            try:
                item = self.sha1map[sha1]
            except KeyError:
                continue
            self.scrollToItem(item)
            item.setSelected(True)

    def adjust_columns(self):
        width = self.width()-20
        zero = width*2//3
        onetwo = width//6
        self.setColumnWidth(0, zero)
        self.setColumnWidth(1, onetwo)
        self.setColumnWidth(2, onetwo)

    def clear(self):
        QtGui.QTreeWidget.clear(self)
        self.sha1map.clear()
        self.commits = []

    def add_commits(self, commits):
        self.commits.extend(commits)
        items = []
        for c in reversed(commits):
            item = CommitTreeWidgetItem(c)
            items.append(item)
            self.sha1map[c.sha1] = item
            for tag in c.tags:
                self.sha1map[tag] = item
        self.insertTopLevelItems(0, items)

    def create_patch(self):
        items = self.selectedItems()
        if not items:
            return
        sha1s = [item.commit.sha1 for item in reversed(items)]
        all_sha1s = [c.sha1 for c in self.commits]
        cmds.do(cmds.FormatPatch, sha1s, all_sha1s)

    # Qt overrides
    def contextMenuEvent(self, event):
        self.context_menu_event(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            event.accept()
            return
        QtGui.QTreeWidget.mousePressEvent(self, event)


class GitDAG(standard.MainWindow):
    """The git-dag widget."""

    def __init__(self, model, ctx, parent=None, settings=None):
        standard.MainWindow.__init__(self, parent)

        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setMinimumSize(420, 420)

        # change when widgets are added/removed
        self.widget_version = 2
        self.model = model
        self.ctx = ctx
        self.settings = settings

        self.commits = {}
        self.commit_list = []
        self.selection = []

        self.thread = ReaderThread(ctx, self)
        self.revtext = completion.GitLogLineEdit()
        self.maxresults = standard.SpinBox()

        self.zoom_out = qtutils.create_action_button(
                tooltip=N_('Zoom Out'),
                icon=qtutils.theme_icon('zoom-out.png'))

        self.zoom_in = qtutils.create_action_button(
                tooltip=N_('Zoom In'),
                icon=qtutils.theme_icon('zoom-in.png'))

        self.zoom_to_fit = qtutils.create_action_button(
                tooltip=N_('Zoom to Fit'),
                icon=qtutils.theme_icon('zoom-fit-best.png'))

        self.notifier = notifier = observable.Observable()
        self.notifier.refs_updated = refs_updated = 'refs_updated'
        self.notifier.add_observer(refs_updated, self.display)
        self.notifier.add_observer(filelist.HISTORIES_SELECTED,
                                   self.histories_selected)
        self.notifier.add_observer(diff.COMMITS_SELECTED, self.commits_selected)

        self.treewidget = CommitTreeWidget(notifier, self)
        self.diffwidget = diff.DiffWidget(notifier, self)
        self.filewidget = filelist.FileWidget(notifier, self)
        self.graphview = GraphView(notifier, self)

        self.controls_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                            self.revtext, self.maxresults)

        self.controls_widget = QtGui.QWidget()
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
                self.zoom_out, self.zoom_in, self.zoom_to_fit)

        self.graph_controls_widget = QtGui.QWidget()
        self.graph_controls_widget.setLayout(self.graph_controls_layout)

        self.graphview_dock = qtutils.create_dock(N_('Graph'), self)
        self.graphview_dock.setWidget(self.graphview)
        graph_titlebar = self.graphview_dock.titleBarWidget()
        graph_titlebar.add_corner_widget(self.graph_controls_widget)

        self.lock_layout_action = qtutils.add_action_bool(self,
                N_('Lock Layout'), self.set_lock_layout, False)

        self.refresh_action = qtutils.add_action(self,
                N_('Refresh'), self.refresh, 'Ctrl+R')

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

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

        # Update fields affected by model
        self.revtext.setText(ctx.ref)
        self.maxresults.setValue(ctx.count)
        self.update_window_title()

        # Also re-loads dag.* from the saved state
        if not self.restore_state(settings=settings):
            self.resize_to_desktop()

        qtutils.connect_button(self.zoom_out, self.graphview.zoom_out)
        qtutils.connect_button(self.zoom_in, self.graphview.zoom_in)
        qtutils.connect_button(self.zoom_to_fit,
                               self.graphview.zoom_to_fit)

        self.thread.connect(self.thread, self.thread.begin, self.thread_begin,
                            Qt.QueuedConnection)
        self.thread.connect(self.thread, self.thread.add, self.add_commits,
                            Qt.QueuedConnection)
        self.thread.connect(self.thread, self.thread.end, self.thread_end,
                            Qt.QueuedConnection)

        self.connect(self.treewidget,
                     SIGNAL('diff_commits(PyQt_PyObject,PyQt_PyObject)'),
                     self.diff_commits)

        self.connect(self.graphview,
                     SIGNAL('diff_commits(PyQt_PyObject,PyQt_PyObject)'),
                     self.diff_commits)

        self.connect(self.maxresults, SIGNAL('editingFinished()'),
                     self.display)

        self.connect(self.revtext, SIGNAL('textChanged(QString)'),
                     self.text_changed)

        self.connect(self.revtext, SIGNAL('activated()'), self.display)
        self.connect(self.revtext, SIGNAL('return()'), self.display)
        self.connect(self.revtext, SIGNAL('down()'), self.focus_tree)

        # The model is updated in another thread so use
        # signals/slots to bring control back to the main GUI thread
        self.model.add_observer(self.model.message_updated,
                                self.emit_model_updated)

        self.connect(self, SIGNAL('model_updated()'), self.model_updated,
                     Qt.QueuedConnection)

        qtutils.add_action(self, 'Focus Input', self.focus_input, 'Ctrl+L')
        qtutils.add_close_action(self)

    def focus_input(self):
        self.revtext.setFocus()

    def focus_tree(self):
        self.treewidget.setFocus()

    def text_changed(self, txt):
        self.ctx.ref = ustr(txt)
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

    def emit_model_updated(self):
        self.emit(SIGNAL('model_updated()'))

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
            self.commits[commit_obj.sha1] = commit_obj
            for tag in commit_obj.tags:
                self.commits[tag] = commit_obj
        self.graphview.add_commits(commits)
        self.treewidget.add_commits(commits)

    def thread_begin(self):
        self.clear()

    def thread_end(self):
        self.focus_tree()
        self.restore_selection()

    def restore_selection(self):
        selection = self.selection
        try:
            commit_obj = self.commit_list[-1]
        except IndexError:
            # No commits, exist, early-out
            return

        new_commits = [self.commits.get(s.sha1, None) for s in selection]
        new_commits = [c for c in new_commits if c is not None]
        if new_commits:
            # The old selection exists in the new state
            self.notifier.notify_observers(diff.COMMITS_SELECTED, new_commits)
        else:
            # The old selection is now empty.  Select the top-most commit
            self.notifier.notify_observers(diff.COMMITS_SELECTED, [commit_obj])

        self.graphview.update_scene_rect()
        self.graphview.set_initial_view()

    def resize_to_desktop(self):
        desktop = QtGui.QApplication.instance().desktop()
        width = desktop.width()
        height = desktop.height()
        self.resize(width, height)

    def diff_commits(self, a, b):
        paths = self.ctx.paths()
        if paths:
            difftool.launch([a, b, '--'] + paths)
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
        text = subprocess.list2cmdline(argv)
        self.revtext.setText(text)
        self.display()


class ReaderThread(QtCore.QThread):
    begin = SIGNAL('begin')
    add = SIGNAL('add')
    end = SIGNAL('end')

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
        self.emit(self.begin)
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
                self.emit(self.add, commits)
                commits = []

        if commits:
            self.emit(self.add, commits)
        self.emit(self.end)

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


class Edge(QtGui.QGraphicsItem):
    item_type = QtGui.QGraphicsItem.UserType + 1

    def __init__(self, source, dest):

        QtGui.QGraphicsItem.__init__(self)

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
            color = EdgeColor.next()
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

        arc_rect = 10
        connector_length = 5

        painter.setPen(self.pen)
        path = QtGui.QPainterPath()

        if self.source.x() == self.dest.x():
            path.moveTo(self.source.x(), self.source.y())
            path.lineTo(self.dest.x(), self.dest.y())
            painter.drawPath(path)

        else:

            #Define points starting from source
            point1 = QPointF(self.source.x(), self.source.y())
            point2 = QPointF(point1.x(), point1.y() - connector_length)
            point3 = QPointF(point2.x() + arc_rect, point2.y() - arc_rect)

            #Define points starting from dest
            point4 = QPointF(self.dest.x(), self.dest.y())
            point5 = QPointF(point4.x(),point3.y() - arc_rect)
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
    def next(cls):
        cls.current_color_index += 1
        cls.current_color_index %= len(cls.colors)
        color = cls.colors[cls.current_color_index]
        color.setAlpha(128)
        return color

    @classmethod
    def current(cls):
        return cls.colors[cls.current_color_index]


class Commit(QtGui.QGraphicsItem):
    item_type = QtGui.QGraphicsItem.UserType + 2
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
                 selectable=QtGui.QGraphicsItem.ItemIsSelectable,
                 cursor=Qt.PointingHandCursor,
                 xpos=commit_radius/2.0 + 1.0,
                 cached_commit_color=commit_color,
                 cached_merge_color=merge_color):

        QtGui.QGraphicsItem.__init__(self)

        self.commit = commit
        self.notifier = notifier

        self.setZValue(0)
        self.setFlag(selectable)
        self.setCursor(cursor)
        self.setToolTip(commit.sha1[:7] + ': ' + commit.summary)

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
        if change == QtGui.QGraphicsItem.ItemSelectedHasChanged:
            # Broadcast selection to other widgets
            selected_items = self.scene().selectedItems()
            commits = [item.commit for item in selected_items]
            self.scene().parent().set_selecting(True)
            self.notifier.notify_observers(diff.COMMITS_SELECTED, commits)
            self.scene().parent().set_selecting(False)

            # Cache the pen for use in paint()
            if value.toPyObject():
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

        return QtGui.QGraphicsItem.itemChange(self, change, value)

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
        QtGui.QGraphicsItem.mousePressEvent(self, event)
        self.pressed = True
        self.selected = self.isSelected()

    def mouseMoveEvent(self, event):
        if self.pressed:
            self.dragged = True
        QtGui.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)
        if (not self.dragged and
                self.selected and
                event.button() == Qt.LeftButton):
            return
        self.pressed = False
        self.dragged = False


class Label(QtGui.QGraphicsItem):
    item_type = QtGui.QGraphicsItem.UserType + 3

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
        QtGui.QGraphicsItem.__init__(self)
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
            font = cache.label_font = QtGui.QApplication.font()
            font.setPointSize(6)


        # Draw tags
        painter.setBrush(self.color)
        painter.setPen(self.pen)
        painter.setFont(font)

        current_width = 0

        for tag in self.commit.tags:
            text_rect = painter.boundingRect(
                    QRectF(current_width, 0, 0, 0), Qt.TextSingleLine, tag)
            box_rect = text_rect.adjusted(-1, -1, 1, 1)
            painter.drawRoundedRect(box_rect, 2, 2)
            painter.drawText(text_rect, Qt.TextSingleLine, tag)
            current_width += text_rect.width() + 5


class GraphView(ViewerMixin, QtGui.QGraphicsView):

    x_max = 0
    y_min = 0

    x_adjust = Commit.commit_radius*4/3
    y_adjust = Commit.commit_radius*4/3

    x_off = 18
    y_off = 24

    def __init__(self, notifier, parent):
        QtGui.QGraphicsView.__init__(self, parent)
        ViewerMixin.__init__(self)

        highlight = self.palette().color(QtGui.QPalette.Highlight)
        Commit.commit_selected_color = highlight
        Commit.selected_outline_color = highlight.darker()

        self.selection_list = []
        self.notifier = notifier
        self.commits = []
        self.items = {}
        self.saved_matrix = QtGui.QMatrix(self.matrix())

        self.x_offsets = collections.defaultdict(int)

        self.is_panning = False
        self.pressed = False
        self.selecting = False
        self.last_mouse = [0, 0]
        self.zoom = 2
        self.setDragMode(self.RubberBandDrag)

        scene = QtGui.QGraphicsScene(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        self.setScene(scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setViewportUpdateMode(self.BoundingRectViewportUpdate)
        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setBackgroundBrush(QtGui.QColor(Qt.white))

        qtutils.add_action(self, N_('Zoom In'),
                           self.zoom_in, Qt.Key_Plus, Qt.Key_Equal)

        qtutils.add_action(self, N_('Zoom Out'),
                           self.zoom_out, Qt.Key_Minus)

        qtutils.add_action(self, N_('Zoom to Fit'),
                           self.zoom_to_fit, Qt.Key_F)

        qtutils.add_action(self, N_('Select Parent'),
                           self.select_parent, 'Shift+J')

        qtutils.add_action(self, N_('Select Oldest Parent'),
                           self.select_oldest_parent, Qt.Key_J)

        qtutils.add_action(self, N_('Select Child'),
                           self.select_child, 'Shift+K')

        qtutils.add_action(self, N_('Select Newest Child'),
                           self.select_newest_child, Qt.Key_K)

        notifier.add_observer(diff.COMMITS_SELECTED, self.commits_selected)

    def clear(self):
        self.scene().clear()
        self.selection_list = []
        self.items.clear()
        self.x_offsets.clear()
        self.x_max = 0
        self.y_min = 0
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
        self.select([commit.sha1 for commit in commits])

    def select(self, sha1s):
        """Select the item for the SHA-1"""
        self.scene().clearSelection()
        for sha1 in sha1s:
            try:
                item = self.items[sha1]
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
                sha1 = commit.sha1
                generation = commit.generation
        try:
            return self.items[sha1]
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
        sha1s = [c.sha1 for c in selected_commits]
        all_sha1s = [c.sha1 for c in self.commits]
        cmds.do(cmds.FormatPatch, sha1s, all_sha1s)

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
            items = [self_items[c.sha1] for c in commits]

        self.fit_view_to_items(items)

    def zoom_to_fit(self):
        """Fit selected items into the viewport"""

        items = self.selected_items()
        self.fit_view_to_items(items)

    def fit_view_to_items(self, items):
        if not items:
            rect = self.scene().itemsBoundingRect()
        else:
            maxint = 9223372036854775807
            x_min = maxint
            y_min = maxint
            x_max = -maxint
            ymax = -maxint
            for item in items:
                pos = item.pos()
                item_rect = item.boundingRect()
                x_off = item_rect.width() * 5
                y_off = item_rect.height() * 10
                x_min = min(x_min, pos.x())
                y_min = min(y_min, pos.y()-y_off)
                x_max = max(x_max, pos.x()+x_off)
                ymax = max(ymax, pos.y())
            rect = QtCore.QRectF(x_min, y_min, x_max-x_min, ymax-y_min)
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

        matrix = QtGui.QMatrix(self.saved_matrix).translate(tx, ty)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def wheel_zoom(self, event):
        """Handle mouse wheel zooming."""
        zoom = math.pow(2.0, event.delta()/512.0)
        factor = (self.matrix()
                        .scale(zoom, zoom)
                        .mapRect(QtCore.QRectF(0.0, 0.0, 1.0, 1.0))
                        .width())
        if factor < 0.014 or factor > 42.0:
            return
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.zoom = zoom
        self.scale(zoom, zoom)

    def wheel_pan(self, event):
        """Handle mouse wheel panning."""

        if event.delta() < 0:
            s = -133.0
        else:
            s = 133.0
        pan_rect = QtCore.QRectF(0.0, 0.0, 1.0, 1.0)
        factor = 1.0/self.matrix().mapRect(pan_rect).width()

        if event.orientation() == Qt.Vertical:
            matrix = self.matrix().translate(0, s*factor)
        else:
            matrix = self.matrix().translate(s*factor, 0)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def scale_view(self, scale):
        factor = (self.matrix().scale(scale, scale)
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

        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
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
            self.items[commit.sha1] = item
            for ref in commit.tags:
                self.items[ref] = item
            scene.addItem(item)

        self.layout_commits(commits)
        self.link(commits)

    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        for commit in commits:
            try:
                commit_item = self.items[commit.sha1]
            except KeyError:
                # TODO - Handle truncated history viewing
                continue
            for parent in reversed(commit.parents):
                try:
                    parent_item = self.items[parent.sha1]
                except KeyError:
                    # TODO - Handle truncated history viewing
                    continue
                edge = Edge(parent_item, commit_item)
                scene.addItem(edge)

    def layout_commits(self, nodes):
        positions = self.position_nodes(nodes)
        for sha1, (x, y) in positions.items():
            item = self.items[sha1]
            item.setPos(x, y)

    def position_nodes(self, nodes):
        positions = {}

        x_max = self.x_max
        y_min = self.y_min
        x_off = self.x_off
        y_off = self.y_off
        x_offsets = self.x_offsets

        for node in nodes:
            generation = node.generation
            sha1 = node.sha1

            if node.is_fork():
                # This is a fan-out so sweep over child generations and
                # shift them to the right to avoid overlapping edges
                child_gens = [c.generation for c in node.children]
                maxgen = max(child_gens)
                for g in range(generation + 1, maxgen):
                    x_offsets[g] += x_off

            if len(node.parents) == 1:
                # Align nodes relative to their parents
                parent_gen = node.parents[0].generation
                parent_off = x_offsets[parent_gen]
                x_offsets[generation] = max(parent_off-x_off,
                                            x_offsets[generation])

            cur_xoff = x_offsets[generation]
            next_xoff = cur_xoff
            next_xoff += x_off
            x_offsets[generation] = next_xoff

            x_pos = cur_xoff
            y_pos = -generation * y_off

            y_pos = min(y_pos, y_min - y_off)

            #y_pos = y_off
            positions[sha1] = (x_pos, y_pos)

            x_max = max(x_max, x_pos)
            y_min = y_pos

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
            self.saved_matrix = QtGui.QMatrix(self.matrix())
            self.is_panning = True
            return
        if event.button() == Qt.RightButton:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.pressed = True
        self.handle_event(QtGui.QGraphicsView.mousePressEvent, event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self.is_panning:
            self.pan(event)
            return
        self.last_mouse[0] = pos.x()
        self.last_mouse[1] = pos.y()
        self.handle_event(QtGui.QGraphicsView.mouseMoveEvent, event)
        if self.pressed:
            self.viewport().repaint()

    def mouseReleaseEvent(self, event):
        self.pressed = False
        if event.button() == Qt.MidButton:
            self.is_panning = False
            return
        self.handle_event(QtGui.QGraphicsView.mouseReleaseEvent, event)
        self.selection_list = []
        self.viewport().repaint()

    def wheelEvent(self, event):
        """Handle Qt mouse wheel events."""
        if event.modifiers() & Qt.ControlModifier:
            self.wheel_zoom(event)
        else:
            self.wheel_pan(event)
