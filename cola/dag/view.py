import os
import sys
import math
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

if __name__ == "__main__":
    # Find the source tree
    src = os.path.join(os.path.dirname(__file__), '..', '..')
    sys.path.insert(1, os.path.join(os.path.abspath(src), 'thirdparty'))
    sys.path.insert(1, os.path.abspath(src))

import cola
from cola import observable
from cola import qtutils
from cola import signals
from cola import gitcmds
from cola import difftool
from cola.controllers import createbranch
from cola.controllers import createtag
from cola.dag.model import DAG
from cola.dag.model import RepoReader
from cola.prefs import diff_font
from cola.qt import DiffSyntaxHighlighter
from cola.qt import GitRefCompleter
from cola.views import standard


def git_dag(model, parent):
    """Return a pre-populated git DAG widget."""
    dag = DAG(model.currentbranch, 1000)
    view = GitDAGWidget(dag, parent=parent)
    view.resize_to_desktop()
    view.show()
    view.raise_()
    view.thread.start(QtCore.QThread.LowPriority)
    return view


class DiffWidget(QtGui.QWidget):
    def __init__(self, notifier, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.diff = QtGui.QTextEdit()
        self.diff.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.diff.setReadOnly(True)
        self.diff.setFont(diff_font())
        self.diff_syn = DiffSyntaxHighlighter(self.diff.document())

        self._layt = QtGui.QHBoxLayout()
        self._layt.addWidget(self.diff)
        self._layt.setMargin(2)
        self.setLayout(self._layt)

        sig = signals.commits_selected
        notifier.add_message_observer(sig, self._commits_selected)

    def _commits_selected(self, commits):
        if len(commits) != 1:
            return
        commit = commits[0]
        sha1 = commit.sha1
        merge = len(commit.parents) > 1
        self.diff.setText(gitcmds.diff_info(sha1, merge=merge))
        qtutils.set_clipboard(sha1)


class CommitTreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, commit, parent=None):
        QtGui.QListWidgetItem.__init__(self, parent)
        self.commit = commit
        self.setText(0, commit.subject)
        self.setText(1, commit.author)
        self.setText(2, commit.authdate)


class CommitTreeWidget(QtGui.QTreeWidget):
    def __init__(self, notifier, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)
        self.setSelectionMode(self.ContiguousSelection)
        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(False)
        self.setHeaderLabels(['Subject', 'Author', 'Date'])

        self._sha1map = {}
        self._notifier = notifier
        self._selecting = False
        self._commits = []
        self._clicked_item = None
        self._selected_item = None
        self._actions = context_menu_actions(self)

        sig = signals.commits_selected
        notifier.add_message_observer(sig, self._commits_selected)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self._item_selection_changed)

    def contextMenuEvent(self, event):
        update_actions(self, event)
        context_menu_event(self, event)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.RightButton:
            event.accept()
            return
        QtGui.QTreeWidget.mousePressEvent(self, event)

    def selecting(self):
        return self._selecting

    def set_selecting(self, selecting):
        self._selecting = selecting

    def _item_selection_changed(self):
        items = self.selectedItems()
        if not items:
            return
        self.set_selecting(True)
        sig = signals.commits_selected
        self._notifier.notify_message_observers(sig, [i.commit for i in items])
        self.set_selecting(False)

    def _commits_selected(self, commits):
        if self.selecting():
            return
        self.select([commit.sha1 for commit in commits])

    def select(self, sha1s):
        self.clearSelection()
        for sha1 in sha1s:
            try:
                item = self._sha1map[sha1]
            except KeyError:
                continue
            self.blockSignals(True)
            self.scrollToItem(item)
            item.setSelected(True)
            self.blockSignals(False)

    def adjust_columns(self):
        width = self.width()-20
        zero = width*2/3
        onetwo = width/6
        self.setColumnWidth(0, zero)
        self.setColumnWidth(1, onetwo)
        self.setColumnWidth(2, onetwo)

    def clear(self):
        QtGui.QTreeWidget.clear(self)
        self._sha1map.clear()
        self._commits = []

    def add_commits(self,commits):
        self._commits.extend(commits)
        items = []
        for c in reversed(commits):
            item = CommitTreeWidgetItem(c)
            items.append(item)
            self._sha1map[c.sha1] = item
            for tag in c.tags:
                self._sha1map[tag] = item
        self.insertTopLevelItems(0, items)

    def _diff_this_selected(self):
        clicked_sha1 = self._clicked_item.commit.sha1
        selected_sha1 = self._selected_item.commit.sha1
        difftool.diff_commits(self, clicked_sha1, selected_sha1)

    def _diff_selected_this(self):
        clicked_sha1 = self._clicked_item.commit.sha1
        selected_sha1 = self._selected_item.commit.sha1
        difftool.diff_commits(self, selected_sha1, clicked_sha1)

    def _create_patch(self):
        items = self.selectedItems()
        if not items:
            return
        items.reverse()
        sha1s = [item.commit.sha1 for item in items]
        all_sha1s = [c.sha1 for c in self._commits]
        cola.notifier().broadcast(signals.format_patch, sha1s, all_sha1s)

    def _create_branch(self):
        sha1 = self._clicked_item.commit.sha1
        createbranch.create_new_branch(revision=sha1)

    def _create_tag(self):
        sha1 = self._clicked_item.commit.sha1
        createtag.create_tag(revision=sha1)

    def _cherry_pick(self):
        sha1 = self._clicked_item.commit.sha1
        cola.notifier().broadcast(signals.cherry_pick, [sha1])


class GitDAGWidget(standard.StandardDialog):
    """The git-dag widget."""
    # Keep us in scope otherwise PyQt kills the widget
    def __init__(self, dag, parent=None, args=None):
        standard.StandardDialog.__init__(self, parent=parent)
        self.dag = dag
        self.setObjectName('dag')
        self.setWindowTitle(self.tr('git dag'))
        self.setMinimumSize(1, 1)

        self.revlabel = QtGui.QLabel()
        self.revlabel.setText('Revision')

        self.revtext = QtGui.QLineEdit()
        self.revtext.setText(dag.ref)
        self.revcompleter = GitRefCompleter(self)
        self.revtext.setCompleter(self.revcompleter)

        self.maxresults = QtGui.QSpinBox()
        self.maxresults.setMinimum(-1)
        self.maxresults.setMaximum(2**31 - 1)
        self.maxresults.setValue(dag.count)

        self.displaybutton = QtGui.QPushButton()
        self.displaybutton.setText('Display')

        self.zoom_in = QtGui.QPushButton()
        self.zoom_in.setIcon(qtutils.theme_icon('zoom-in.png'))
        self.zoom_in.setFlat(True)

        self.zoom_out = QtGui.QPushButton()
        self.zoom_out.setIcon(qtutils.theme_icon('zoom-out.png'))
        self.zoom_out.setFlat(True)

        self._buttons_layt = QtGui.QHBoxLayout()
        self._buttons_layt.setMargin(2)
        self._buttons_layt.setSpacing(2)

        self._buttons_layt.addWidget(self.revlabel)
        self._buttons_layt.addWidget(self.revtext)
        self._buttons_layt.addWidget(self.maxresults)
        self._buttons_layt.addWidget(self.displaybutton)
        self._buttons_layt.addStretch()
        self._buttons_layt.addWidget(self.zoom_out)
        self._buttons_layt.addWidget(self.zoom_in)

        self._commits = {}
        self._notifier = notifier = observable.Observable()
        self._notifier.refs_updated = refs_updated = 'refs_updated'
        self._notifier.add_message_observer(refs_updated, self._display)

        self._graphview = GraphView(notifier)
        self._treewidget = CommitTreeWidget(notifier)
        self._diffwidget = DiffWidget(notifier)

        self._mainsplitter = QtGui.QSplitter()
        self._mainsplitter.setOrientation(QtCore.Qt.Horizontal)
        self._mainsplitter.setChildrenCollapsible(True)

        self._leftsplitter = QtGui.QSplitter()
        self._leftsplitter.setOrientation(QtCore.Qt.Vertical)
        self._leftsplitter.setChildrenCollapsible(True)
        self._leftsplitter.setStretchFactor(0, 1)
        self._leftsplitter.setStretchFactor(1, 1)
        self._leftsplitter.insertWidget(0, self._treewidget)
        self._leftsplitter.insertWidget(1, self._diffwidget)

        self._mainsplitter.insertWidget(0, self._leftsplitter)
        self._mainsplitter.insertWidget(1, self._graphview)

        self._mainsplitter.setStretchFactor(0, 1)
        self._mainsplitter.setStretchFactor(1, 1)

        self._layt = layt = QtGui.QVBoxLayout()
        layt.setMargin(0)
        layt.addLayout(self._buttons_layt)
        layt.addWidget(self._mainsplitter)
        self.setLayout(layt)

        qtutils.add_close_action(self)

        self.thread = ReaderThread(self, dag)

        self.thread.connect(self.thread, self.thread.commits_ready,
                            self.add_commits)

        self.thread.connect(self.thread, self.thread.done,
                            self.thread_done)

        self.connect(self._mainsplitter, SIGNAL('splitterMoved(int,int)'),
                     self._splitter_moved)

        self.connect(self.zoom_in, SIGNAL('pressed()'),
                     self._graphview.zoom_in)

        self.connect(self.zoom_out, SIGNAL('pressed()'),
                     self._graphview.zoom_out)

        self.connect(self.maxresults, SIGNAL('valueChanged(int)'),
                     lambda(x): self.dag.set_count(x))

        self.connect(self.displaybutton, SIGNAL('pressed()'),
                     self._display)

    def _display(self):
        new_ref = unicode(self.revtext.text())
        if not new_ref:
            return
        self.stop()
        self.clear()
        self.dag.set_ref(unicode(self.revtext.text()))
        self.dag.set_count(self.maxresults.value())
        self.start()

    def show(self):
        standard.StandardDialog.show(self)
        self._mainsplitter.setSizes([self.width()/2, self.width()/2])
        self._leftsplitter.setSizes([self.height()/3, self.height()*2/3])
        self._treewidget.adjust_columns()

    def resizeEvent(self, e):
        standard.StandardDialog.resizeEvent(self, e)
        self._treewidget.adjust_columns()

    def _splitter_moved(self, pos, idx):
        self._treewidget.adjust_columns()

    def clear(self):
        self._graphview.clear()
        self._treewidget.clear()
        self._commits.clear()

    def add_commits(self, commits):
        # Keep track of commits
        for commit_obj in commits:
            self._commits[commit_obj.sha1] = commit_obj
            for tag in commit_obj.tags:
                self._commits[tag] = commit_obj
        self._graphview.add_commits(commits)
        self._treewidget.add_commits(commits)

    def thread_done(self):
        try:
            commit_obj = self._commits[self.dag.ref]
        except KeyError:
            return
        sig = signals.commits_selected
        self._notifier.notify_message_observers(sig, [commit_obj])
        self._graphview.view_fit()

    def close(self):
        self.stop()
        standard.StandardDialog.close(self)

    def pause(self):
        self.thread.mutex.lock()
        self.thread.stop = True
        self.thread.mutex.unlock()

    def stop(self):
        self.thread.abort = True
        self.thread.wait()

    def start(self):
        self.thread.abort = False
        self.thread.stop = False
        self.thread.start()

    def resume(self):
        self.thread.mutex.lock()
        self.thread.stop = False
        self.thread.mutex.unlock()
        self.thread.condition.wakeOne()

    def resize_to_desktop(self):
        desktop = QtGui.QApplication.instance().desktop()
        width = desktop.width()
        height = desktop.height()
        self.resize(width, height)


class ReaderThread(QtCore.QThread):

    commits_ready = QtCore.SIGNAL('commits_ready')
    done = QtCore.SIGNAL('done')

    def __init__(self, parent, dag):
        QtCore.QThread.__init__(self, parent)
        self.dag = dag
        self.abort = False
        self.stop = False
        self.mutex = QtCore.QMutex()
        self.condition = QtCore.QWaitCondition()

    def run(self):
        repo = RepoReader(self.dag)
        repo.reset()
        commits = []
        for c in repo:
            self.mutex.lock()
            if self.stop:
                self.condition.wait(self.mutex)
            self.mutex.unlock()
            if self.abort:
                repo.reset()
                return
            commits.append(c)
            if len(commits) >= 512:
                self.emit(self.commits_ready, commits)
                commits = []

        if commits:
            self.emit(self.commits_ready, commits)
        self.emit(self.done)


class Cache(object):
    pass


class Edge(QtGui.QGraphicsItem):
    _type = QtGui.QGraphicsItem.UserType + 1
    _arrow_size = 2.0
    _arrow_extra = (_arrow_size+1.0)/2.0

    def __init__(self, source, dest,
                 extra=_arrow_extra,
                 arrow_size=_arrow_size):
        QtGui.QGraphicsItem.__init__(self)

        self.source_pt = QtCore.QPointF()
        self.dest_pt = QtCore.QPointF()
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.source = source
        self.dest = dest
        self.setZValue(-2)

        # Adjust the points to leave a small margin between
        # the arrow and the commit.
        dest_pt = Commit._bbox.center()
        line = QtCore.QLineF(
                self.mapFromItem(self.source, dest_pt),
                self.mapFromItem(self.dest, dest_pt))
        # Magic
        dx = 22.
        dy = 11.
        length = line.length()
        offset = QtCore.QPointF((line.dx() * dx) / length,
                                (line.dy() * dy) / length)

        self.source_pt = line.p1() + offset
        self.dest_pt = line.p2() - offset

        line = QtCore.QLineF(self.source_pt, self.dest_pt)
        self.line = line

        self.pen = QtGui.QPen(QtCore.Qt.gray, 0,
                              QtCore.Qt.DotLine,
                              QtCore.Qt.FlatCap,
                              QtCore.Qt.MiterJoin)

        # Setup the arrow polygon
        length = line.length()
        angle = math.acos(line.dx() / length)
        if line.dy() >= 0:
            angle = 2.0 * math.pi - angle

        dest_x = (self.dest_pt +
                  QtCore.QPointF(math.sin(angle - math.pi/3.) *
                                 arrow_size,
                                 math.cos(angle - math.pi/3.) *
                                 arrow_size))
        dest_y = (self.dest_pt +
                  QtCore.QPointF(math.sin(angle - math.pi + math.pi/3.) *
                                 arrow_size,
                                 math.cos(angle - math.pi + math.pi/3.) *
                                 arrow_size))
        self.poly = QtGui.QPolygonF([line.p2(), dest_x, dest_y])

        width = self.dest_pt.x() - self.source_pt.x()
        height = self.dest_pt.y() - self.source_pt.y()
        rect = QtCore.QRectF(self.source_pt, QtCore.QSizeF(width, height))
        self._bound = rect.normalized().adjusted(-extra, -extra, extra, extra)

    def type(self, _type=_type):
        return _type

    def boundingRect(self):
        return self._bound

    def paint(self, painter, option, widget,
              arrow_size=_arrow_size,
              gray=QtCore.Qt.gray):
        # Draw the line
        painter.setPen(self.pen)
        painter.drawLine(self.line)

        # Draw the arrow
        painter.setBrush(gray)
        painter.drawPolygon(self.poly)


class Commit(QtGui.QGraphicsItem):
    _type = QtGui.QGraphicsItem.UserType + 2
    _width = 46.
    _height = 24.

    _shape = QtGui.QPainterPath()
    _shape.addRect(_width/-2., _height/-2., _width, _height)
    _bbox = _shape.boundingRect()

    _inner = QtGui.QPainterPath()
    _inner.addRect(_width/-2.+2., _height/-2.+2, _width-4., _height-4.)
    _inner = _inner.boundingRect()

    _selected_color = QtGui.QColor.fromRgb(255, 255, 0)
    _outline_color = QtGui.QColor.fromRgb(64, 96, 192)


    _text_options = QtGui.QTextOption()
    _text_options.setAlignment(QtCore.Qt.AlignCenter)

    _commit_pen = QtGui.QPen()
    _commit_pen.setWidth(1.0)
    _commit_pen.setColor(_outline_color)

    _commit_color = QtGui.QColor.fromRgb(128, 222, 255)
    _commit_selected_color = QtGui.QColor.fromRgb(32, 64, 255)
    _merge_color = QtGui.QColor.fromRgb(255, 255, 255)

    def __init__(self, commit,
                 notifier,
                 selectable=QtGui.QGraphicsItem.ItemIsSelectable,
                 cursor=QtCore.Qt.PointingHandCursor,
                 xpos=_width/2.+1.,
                 commit_color=_commit_color,
                 commit_selected_color=_commit_selected_color,
                 merge_color=_merge_color):

        QtGui.QGraphicsItem.__init__(self)

        self.setZValue(0)
        self.setFlag(selectable)
        self.setCursor(cursor)

        self.commit = commit
        self._notifier = notifier

        if commit.tags:
            self.label = Label(commit)
            self.label.setParentItem(self)
            self.label.setPos(xpos, 0.)
        else:
            self.label = None

        if len(commit.parents) > 1:
            self.commit_color = merge_color
        else:
            self.commit_color = commit_color
        self.text_pen = QtCore.Qt.black
        self.sha1_text = commit.sha1[:8]

        self.pressed = False
        self.dragged = False

    #
    # Overridden Qt methods
    #

    def blockSignals(self, blocked):
        self._notifier.notification_enabled = not blocked

    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemSelectedHasChanged:
            # Broadcast selection to other widgets
            selected_items = self.scene().selectedItems()
            commits = [item.commit for item in selected_items]
            self.scene().parent().set_selecting(True)
            sig = signals.commits_selected
            self._notifier.notify_message_observers(sig, commits)
            self.scene().parent().set_selecting(False)

            # Cache the pen for use in paint()
            if value.toPyObject():
                self.commit_color = self._commit_selected_color
                self.text_pen = QtCore.Qt.white
                color = self._selected_color
            else:
                self.text_pen = QtCore.Qt.black
                if len(self.commit.parents) > 1:
                    self.commit_color = self._merge_color
                else:
                    self.commit_color = self._commit_color
                color = self._outline_color
            commit_pen = QtGui.QPen()
            commit_pen.setWidth(1.0)
            commit_pen.setColor(color)
            self._commit_pen = commit_pen

        return QtGui.QGraphicsItem.itemChange(self, change, value)

    def type(self, _type=_type):
        return _type

    def boundingRect(self, _bbox=_bbox):
        return _bbox

    def shape(self, _shape=_shape):
        return _shape

    def paint(self, painter, option, widget,
              inner=_inner,
              text_options=_text_options,
              cache=Cache):

        painter.setPen(self._commit_pen)
        painter.setBrush(self.commit_color)

        # Draw ellipse
        painter.drawEllipse(inner)

        try:
            font = cache.font
        except AttributeError:
            font = cache.font = painter.font()
            font.setPointSize(5)

        painter.setFont(font)
        painter.setPen(self.text_pen)
        painter.drawText(inner, self.sha1_text, text_options)

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
                event.button() == QtCore.Qt.LeftButton):
            return
        self.pressed = False
        self.dragged = False


class Label(QtGui.QGraphicsItem):
    _type = QtGui.QGraphicsItem.UserType + 3

    _width = 72
    _height = 18

    _shape = QtGui.QPainterPath()
    _shape.addRect(0, 0, _width, _height)

    _bbox = _shape.boundingRect()

    _text_options = QtGui.QTextOption()
    _text_options.setAlignment(QtCore.Qt.AlignCenter)
    _text_options.setAlignment(QtCore.Qt.AlignVCenter)

    _black = QtCore.Qt.black

    def __init__(self, commit,
                 other_color=QtGui.QColor.fromRgb(255, 255, 64),
                 head_color=QtGui.QColor.fromRgb(64, 255, 64),
                 width=_width,
                 height=_height):
        QtGui.QGraphicsItem.__init__(self)
        self.setZValue(-1)

        # Starts with enough space for two tags. Any more and the commit
        # needs to be taller to accomodate.

        self.commit = commit
        height = len(commit.tags) * height/2. + 4. # +6 padding

        self.label_box = QtCore.QRectF(0., -height/2., width, height)
        self.text_box = QtCore.QRectF(2., -height/2., width-4., height)
        self.tag_text = '\n'.join(commit.tags)

        if 'HEAD' in commit.tags:
            self.color = head_color
        else:
            self.color = other_color

        self.pen = QtGui.QPen()
        self.pen.setColor(self.color.darker())
        self.pen.setWidth(1.0)

    def type(self, _type=_type):
        return _type

    def boundingRect(self, _bbox=_bbox):
        return _bbox

    def shape(self, _shape=_shape):
        return _shape

    def paint(self, painter, option, widget,
              text_options=_text_options,
              black=_black,
              cache=Cache):
        # Draw tags
        painter.setBrush(self.color)
        painter.setPen(self.pen)
        painter.drawRoundedRect(self.label_box, 4, 4)
        try:
            font = cache.font
        except AttributeError:
            font = cache.font = painter.font()
            font.setPointSize(5)
        painter.setFont(font)
        painter.setPen(black)
        painter.drawText(self.text_box, self.tag_text, text_options)


class GraphView(QtGui.QGraphicsView):
    def __init__(self, notifier):
        QtGui.QGraphicsView.__init__(self)

        self._xoff = 132
        self._yoff = 32
        self._xmax = 0
        self._ymin = 0

        self._selected = []
        self._notifier = notifier
        self._commits = []
        self._items = {}
        self._selected_item = None
        self._clicked_item = None

        self._rows = {}

        self._panning = False
        self._pressed = False
        self._selecting = False
        self._last_mouse = [0, 0]

        self._zoom = 2
        self.scale(self._zoom, self._zoom)
        self.setDragMode(self.RubberBandDrag)

        scene = QtGui.QGraphicsScene(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        self.setScene(scene)

        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setBackgroundBrush(QtGui.QColor.fromRgb(0, 0, 0))

        self._action_zoom_in = (
            qtutils.add_action(self, 'Zoom In',
                               self.zoom_in,
                               QtCore.Qt.Key_Plus,
                               QtCore.Qt.Key_Equal))

        self._action_zoom_out = (
            qtutils.add_action(self, 'Zoom Out',
                               self.zoom_out,
                               QtCore.Qt.Key_Minus))

        self._action_zoom_fit = (
            qtutils.add_action(self, 'Zoom to Fit',
                               self.view_fit,
                               QtCore.Qt.Key_F))

        self._action_select_parent = (
            qtutils.add_action(self, 'Select Parent',
                               self._select_parent,
                               QtCore.Qt.Key_J))

        self._action_select_oldest_parent = (
            qtutils.add_action(self, 'Select Oldest Parent',
                               self._select_oldest_parent,
                               'Shift+J'))

        self._action_select_child = (
            qtutils.add_action(self, 'Select Child',
                               self._select_child,
                               QtCore.Qt.Key_K))

        self._action_select_child = (
            qtutils.add_action(self, 'Select Nth Child',
                               self._select_nth_child,
                               'Shift+K'))

        self._actions = context_menu_actions(self)

        sig = signals.commits_selected
        notifier.add_message_observer(sig, self._commits_selected)

    def zoom_in(self):
        self._scale_view(1.5)

    def zoom_out(self):
        self._scale_view(1.0/1.5)

    def _commits_selected(self, commits):
        if self.selecting():
            return
        self.select([commit.sha1 for commit in commits])

    def contextMenuEvent(self, event):
        update_actions(self, event)
        context_menu_event(self, event)

    def select(self, sha1s):
        """Select the item for the SHA-1"""
        self.scene().clearSelection()
        for sha1 in sha1s:
            try:
                item = self._items[sha1]
            except KeyError:
                continue
            item.blockSignals(True)
            item.setSelected(True)
            item.blockSignals(False)
            self.ensureVisible(item.mapRectToScene(item.boundingRect()))

    def selected_item(self):
        """Return the currently selected item"""
        selected_items = self.selectedItems()
        if not selected_items:
            return None
        return selected_items[0]

    def selectedItems(self):
        """Return the currently selected items"""
        return self.scene().selectedItems()

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
            return self._items[sha1]
        except KeyError:
            return None

    def oldest_item(self, commits):
        """Return the item for the commit with the oldest generation number"""
        return self.get_item_by_generation(commits, lambda a, b: a > b)

    def newest_item(self, commits):
        """Return the item for the commit with the newest generation number"""
        return self.get_item_by_generation(commits, lambda a, b: a < b)

    def _diff_this_selected(self):
        clicked_sha1 = self._clicked_item.commit.sha1
        selected_sha1 = self._selected_item.commit.sha1
        difftool.diff_commits(self, clicked_sha1, selected_sha1)

    def _diff_selected_this(self):
        clicked_sha1 = self._clicked_item.commit.sha1
        selected_sha1 = self._selected_item.commit.sha1
        difftool.diff_commits(self, selected_sha1, clicked_sha1)

    def _create_patch(self):
        items = self.selectedItems()
        if not items:
            return
        selected_commits = sort_by_generation([n.commit for n in items])
        sha1s = [c.sha1 for c in selected_commits]
        all_sha1s = [c.sha1 for c in self._commits]
        cola.notifier().broadcast(signals.format_patch, sha1s, all_sha1s)

    def _create_branch(self):
        sha1 = self._clicked_item.commit.sha1
        createbranch.create_new_branch(revision=sha1)

    def _create_tag(self):
        sha1 = self._clicked_item.commit.sha1
        createtag.create_tag(revision=sha1)

    def _cherry_pick(self):
        sha1 = self._clicked_item.commit.sha1
        cola.notifier().broadcast(signals.cherry_pick, [sha1])
        self._notifier.notify_message_observers(self._notifier.refs_updated)

    def _select_parent(self):
        """Select the parent with the newest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self.newest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        self.ensureVisible(parent_item.mapRectToScene(parent_item.boundingRect()))

    def _select_oldest_parent(self):
        """Select the parent with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self.oldest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        self.ensureVisible(parent_item.mapRectToScene(parent_item.boundingRect()))

    def _select_child(self):
        """Select the child with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        child_item = self.oldest_item(selected_item.commit.children)
        if child_item is None:
            return
        selected_item.setSelected(False)
        child_item.setSelected(True)
        self.ensureVisible(child_item.mapRectToScene(child_item.boundingRect()))

    def _select_nth_child(self):
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
        self.ensureVisible(child_item.mapRectToScene(child_item.boundingRect()))

    def view_fit(self):
        """Fit selected items into the viewport"""

        items = self.scene().selectedItems()
        if not items:
            rect = self.scene().itemsBoundingRect()
        else:
            xmin = sys.maxint
            ymin = sys.maxint
            xmax = -sys.maxint
            ymax = -sys.maxint
            for item in items:
                pos = item.pos()
                item_rect = item.boundingRect()
                xoff = item_rect.width()
                yoff = item_rect.height()
                xmin = min(xmin, pos.x())
                ymin = min(ymin, pos.y())
                xmax = max(xmax, pos.x()+xoff)
                ymax = max(ymax, pos.y()+yoff)
            rect = QtCore.QRectF(xmin, ymin, xmax-xmin, ymax-ymin)
        adjust = Commit._width
        rect.setX(rect.x() - adjust)
        rect.setY(rect.y() - adjust)
        rect.setHeight(rect.height() + adjust)
        rect.setWidth(rect.width() + adjust)
        self.fitInView(rect, QtCore.Qt.KeepAspectRatio)
        self.scene().invalidate()

    def _save_selection(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        elif QtCore.Qt.ShiftModifier != event.modifiers():
            return
        self._selected = self.selectedItems()

    def _restore_selection(self, event):
        if QtCore.Qt.ShiftModifier != event.modifiers():
            return
        for item in self._selected:
            item.setSelected(True)

    def _handle_event(self, eventhandler, event):
        self.update()
        self._save_selection(event)
        eventhandler(self, event)
        self._restore_selection(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MidButton:
            pos = event.pos()
            self._mouse_start = [pos.x(), pos.y()]
            self._saved_matrix = QtGui.QMatrix(self.matrix())
            self._panning = True
            return
        if event.button() == QtCore.Qt.RightButton:
            event.ignore()
            return
        if event.button() == QtCore.Qt.LeftButton:
            self._pressed = True
        self._handle_event(QtGui.QGraphicsView.mousePressEvent, event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self._panning:
            self._pan(event)
            return
        self._last_mouse[0] = pos.x()
        self._last_mouse[1] = pos.y()
        self._handle_event(QtGui.QGraphicsView.mouseMoveEvent, event)

    def selecting(self):
        return self._selecting

    def set_selecting(self, selecting):
        self._selecting = selecting

    def mouseReleaseEvent(self, event):
        self._pressed = False
        if event.button() == QtCore.Qt.MidButton:
            self._panning = False
            return
        self._handle_event(QtGui.QGraphicsView.mouseReleaseEvent, event)
        self._selected = []

    def _pan(self, event):
        pos = event.pos()
        dx = pos.x() - self._mouse_start[0]
        dy = pos.y() - self._mouse_start[1]

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

        matrix = QtGui.QMatrix(self._saved_matrix).translate(tx, ty)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def wheelEvent(self, event):
        """Handle Qt mouse wheel events."""
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self._wheel_zoom(event)
        else:
            self._wheel_pan(event)

    def _wheel_zoom(self, event):
        """Handle mouse wheel zooming."""
        zoom = math.pow(2.0, event.delta() / 512.0)
        factor = (self.matrix()
                        .scale(zoom, zoom)
                        .mapRect(QtCore.QRectF(0.0, 0.0, 1.0, 1.0))
                        .width())
        if factor < 0.014 or factor > 42.0:
            return
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self._zoom = zoom
        self.scale(zoom, zoom)

    def _wheel_pan(self, event):
        """Handle mouse wheel panning."""

        if event.delta() < 0:
            s = -133.
        else:
            s = 133.
        pan_rect = QtCore.QRectF(0.0, 0.0, 1.0, 1.0)
        factor = 1.0 / self.matrix().mapRect(pan_rect).width()

        if event.orientation() == QtCore.Qt.Vertical:
            matrix = self.matrix().translate(0, s * factor)
        else:
            matrix = self.matrix().translate(s * factor, 0)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def _scale_view(self, scale):
        factor = (self.matrix().scale(scale, scale)
                               .mapRect(QtCore.QRectF(0, 0, 1, 1))
                               .width())
        if factor < 0.07 or factor > 100:
            return
        self._zoom = scale

        scrollbar = self.verticalScrollBar()
        if scrollbar:
            value = scrollbar.value()
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            distance = value - min_
            scrolloffset = distance/float(range_)

        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.scale(scale, scale)

        scrollbar = self.verticalScrollBar()
        if scrollbar:
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            value = min_ + int(float(range_) * scrolloffset)
            scrollbar.setValue(value)

    def clear(self):
        self.scene().clear()
        self._selected = []
        self._items.clear()
        self._rows.clear()
        self._xmax = 0
        self._ymin = 0
        self._commits = []

    def add_commits(self, commits):
        """Traverse commits and add them to the view."""
        self._commits.extend(commits)
        scene = self.scene()
        for commit in commits:
            item = Commit(commit, self._notifier)
            self._items[commit.sha1] = item
            for ref in commit.tags:
                self._items[ref] = item
            scene.addItem(item)

        self.layout(commits)
        self.link(commits)

    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        for commit in commits:
            try:
                commit_item = self._items[commit.sha1]
            except KeyError:
                # TODO - Handle truncated history viewing
                pass
            for parent in commit.parents:
                try:
                    parent_item = self._items[parent.sha1]
                except KeyError:
                    # TODO - Handle truncated history viewing
                    continue
                edge = Edge(parent_item, commit_item)
                scene.addItem(edge)

    def layout(self, commits):
        xmax = self._xmax
        ymin = self._ymin
        for commit in commits:
            generation = commit.generation
            sha1 = commit.sha1
            try:
                row = self._rows[generation]
            except KeyError:
                row = self._rows[generation] = []

            xpos = (len(commit.parents)-1) * self._xoff
            if row:
                xpos += row[-1] + self._xoff
            ypos = -commit.generation * self._yoff

            item = self._items[sha1]
            item.setPos(xpos, ypos)

            row.append(xpos)
            xmax = max(xmax, xpos)
            ymin = min(ymin, ypos)

        self._xmax = xmax
        self._ymin = ymin
        self.scene().setSceneRect(self._xoff*-2, ymin-self._yoff*2,
                                  xmax+self._xoff*3, abs(ymin)+self._yoff*4)

def sort_by_generation(commits):
    commits.sort(cmp=lambda a, b: cmp(a.generation, b.generation))
    return commits


def context_menu_actions(self):
    return {
    'diff_this_selected':
        qtutils.add_action(self, 'Diff this -> selected',
                           self._diff_this_selected),
    'diff_selected_this':
        qtutils.add_action(self, 'Diff selected -> this',
                           self._diff_selected_this),
    'create_patch':
        qtutils.add_action(self, 'Create Patch',
                           self._create_patch),
    'create_branch':
        qtutils.add_action(self, 'Create Branch',
                           self._create_branch),
    'create_tag':
        qtutils.add_action(self, 'Create Tag',
                           self._create_tag),
    'cherry_pick':
        qtutils.add_action(self, 'Cherry Pick',
                           self._cherry_pick),
    }


def update_actions(self, event):
    clicked_item = self.itemAt(event.pos())
    selected_items = self.selectedItems()
    has_single_selection = len(selected_items) == 1

    has_selection = bool(selected_items)
    can_diff = bool(clicked_item and has_single_selection and
                    clicked_item is not selected_items[0])

    self._clicked_item = clicked_item
    if can_diff:
        self._selected_item = selected_items[0]
    else:
        self._selected_item = None

    self._actions['diff_this_selected'].setEnabled(can_diff)
    self._actions['diff_selected_this'].setEnabled(can_diff)
    self._actions['create_patch'].setEnabled(has_selection)
    self._actions['create_branch'].setEnabled(has_single_selection)
    self._actions['create_tag'].setEnabled(has_single_selection)
    self._actions['cherry_pick'].setEnabled(has_single_selection)


def context_menu_event(self, event):
    menu = QtGui.QMenu(self)
    menu.addAction(self._actions['diff_this_selected'])
    menu.addAction(self._actions['diff_selected_this'])
    menu.addSeparator()
    menu.addAction(self._actions['create_patch'])
    menu.addAction(self._actions['create_branch'])
    menu.addAction(self._actions['create_tag'])
    menu.addAction(self._actions['cherry_pick'])
    menu.exec_(self.mapToGlobal(event.pos()))


if __name__ == "__main__":
    from cola import app

    model = cola.model()
    model.use_worktree(os.getcwd())
    model.update_status()

    app = app.ColaApplication(sys.argv)
    view = git_dag(model, app.activeWindow())
    sys.exit(app.exec_())
