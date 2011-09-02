import os
import sys
import math
from PyQt4 import QtGui
from PyQt4 import QtCore

if __name__ == "__main__":
    # Find the source tree
    src = os.path.join(os.path.dirname(__file__), '..', '..')
    sys.path.insert(1, os.path.join(os.path.abspath(src), 'thirdparty'))
    sys.path.insert(1, os.path.abspath(src))

from cola import observable
from cola import qtutils
from cola import signals
from cola import gitcmds
from cola.models import commit
from cola.views import standard
from cola.views import syntax


def git_dag(parent=None, log_args=None):
    """Return a pre-populated git DAG widget."""
    view = GitDAGWidget(parent=parent)
    view.resize_to_desktop()
    view.show()
    view.raise_()
    view.thread.start(QtCore.QThread.LowPriority)
    return view


class DiffWidget(QtGui.QWidget):
    def __init__(self, parent=None, nodecom=None):
        QtGui.QWidget.__init__(self, parent)

        self.diff = QtGui.QTextEdit()
        self.diff.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.diff.setReadOnly(True)
        self.diff_syn = syntax.DiffSyntaxHighlighter(self.diff.document())
        qtutils.set_diff_font(self.diff)

        self._layt = QtGui.QHBoxLayout()
        self._layt.addWidget(self.diff)
        self._layt.setMargin(2)
        self.setLayout(self._layt)

        sig = signals.sha1_selected
        nodecom.add_message_observer(sig, self._node_selected)

    def _node_selected(self, sha1):
        self.diff.setText(gitcmds.diff_info(sha1))
        qtutils.set_clipboard(sha1)


class CommitTreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, commit, parent=None):
        QtGui.QListWidgetItem.__init__(self, parent)
        self.commit = commit
        self.setText(0, commit.subject)
        self.setText(1, commit.author)
        self.setText(2, commit.authdate)


class CommitTreeWidget(QtGui.QTreeWidget):
    def __init__(self, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setIndentation(0)
        self.setHeaderLabels(['Subject', 'Author', 'Date'])

    def adjust_columns(self):
        width = self.width()-20
        zero = width*2/3
        onetwo = width/6
        self.setColumnWidth(0, zero)
        self.setColumnWidth(1, onetwo)
        self.setColumnWidth(2, onetwo)


class GitDAGWidget(standard.StandardDialog):
    """The git-dag widget."""
    # Keep us in scope otherwise PyQt kills the widget
    def __init__(self, parent=None, args=None):
        standard.StandardDialog.__init__(self, parent=parent)

        self.setObjectName('dag')
        self.setWindowTitle(self.tr('git dag'))
        self.setMinimumSize(1, 1)

        self.revlabel = QtGui.QLabel()
        self.revlabel.setText('Revision')

        self.revtext = QtGui.QLineEdit()
        self.revtext.setText('HEAD')

        self.maxlabel = QtGui.QLabel()
        self.maxlabel.setText('Max Results')

        self.maxresults = QtGui.QSpinBox()
        self.maxresults.setMinimum(-1)
        self.maxresults.setMaximum(2**31 - 1)
        self.maxresults.setValue(3000)

        self.displaybutton = QtGui.QPushButton()
        self.displaybutton.setText('Display')

        self._buttons_layt = QtGui.QHBoxLayout()
        self._buttons_layt.setMargin(2)
        self._buttons_layt.setSpacing(2)

        self._buttons_layt.addWidget(self.revlabel)
        self._buttons_layt.addWidget(self.revtext)
        self._buttons_layt.addWidget(self.displaybutton)
        self._buttons_layt.addStretch()
        self._buttons_layt.addWidget(self.maxlabel)
        self._buttons_layt.addWidget(self.maxresults)


        self._mainsplitter = QtGui.QSplitter()
        self._mainsplitter.setOrientation(QtCore.Qt.Vertical)
        self._mainsplitter.setChildrenCollapsible(True)

        self._nodecom = observable.Observable()

        self._graphview = GraphView(nodecom=self._nodecom)
        self._treewidget = CommitTreeWidget()
        self._diffwidget = DiffWidget(nodecom=self._nodecom)

        self._bottomsplitter = QtGui.QSplitter()
        self._bottomsplitter.setOrientation(QtCore.Qt.Horizontal)
        self._bottomsplitter.setChildrenCollapsible(True)
        self._bottomsplitter.setStretchFactor(0, 1)
        self._bottomsplitter.setStretchFactor(1, 1)
        self._bottomsplitter.insertWidget(0, self._treewidget)
        self._bottomsplitter.insertWidget(1, self._diffwidget)

        self._mainsplitter.insertWidget(0, self._graphview)
        self._mainsplitter.insertWidget(1, self._bottomsplitter)

        self._mainsplitter.setStretchFactor(0, 1)
        self._mainsplitter.setStretchFactor(1, 1)

        self._layt = layt = QtGui.QVBoxLayout()
        layt.setMargin(0)
        layt.addItem(self._buttons_layt)
        layt.addWidget(self._mainsplitter)
        self.setLayout(layt)

        qtutils.add_close_action(self)
        if not parent:
            qtutils.center_on_screen(self)

        self._bottomsplitter.setSizes([self.width()/3, self.width()*2/3])
        self._mainsplitter.setSizes([self.height()*2/3, self.height()/3])

        self._queue = []
        self.thread = ReaderThread(self, args)

        self.thread.connect(self.thread, self.thread.commits_ready,
                            self.add_commits)

        self.thread.connect(self.thread, self.thread.done,
                            self.thread_done)

    def add_commits(self, commits):
        self._graphview.add_commits(commits)
        items = [CommitTreeWidgetItem(c) for c in reversed(commits)]
        self._treewidget.insertTopLevelItems(0, items)

    def thread_done(self):
        self._graphview.select('HEAD')
        self._treewidget.adjust_columns()

    def close(self):
        self.thread.abort = True
        self.thread.wait()
        standard.StandardDialog.close(self)

    def pause(self):
        self.thread.mutex.lock()
        self.thread.stop = True
        self.thread.mutex.unlock()

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

    def __init__(self, parent, args):
        super(ReaderThread, self).__init__(parent)
        self.repo = commit.RepoReader(args=args)
        self.abort = False
        self.stop = False
        self.mutex = QtCore.QMutex()
        self.condition = QtCore.QWaitCondition()

    def run(self):
        commits = []
        for commit in self.repo:
            self.mutex.lock()
            if self.stop:
                self.condition.wait(self.mutex)
            self.mutex.unlock()
            if self.abort:
                self.repo.reset()
                return
            commits.append(commit)
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
        dest_pt = Node._bbox.center()
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


class Node(QtGui.QGraphicsItem):
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

    _node_pen = QtGui.QPen()
    _node_pen.setWidth(1.0)
    _node_pen.setColor(_outline_color)

    def __init__(self, commit,
                 nodecom,
                 selectable=QtGui.QGraphicsItem.ItemIsSelectable,
                 cursor=QtCore.Qt.PointingHandCursor,
                 xpos=_width/2.+1.,
                 commit_color=QtGui.QColor.fromRgb(128, 222, 255),
                 merge_color=QtGui.QColor.fromRgb(255, 255, 255)):

        QtGui.QGraphicsItem.__init__(self)

        self.setZValue(0)
        self.setFlag(selectable)
        self.setCursor(cursor)

        self.commit = commit
        self.nodecom = nodecom

        if commit.tags:
            self.label = Label(commit)
            self.label.setParentItem(self)
            self.label.setPos(xpos, 0.)
        else:
            self.label = None

        if len(commit.parents) > 1:
            self.node_color = merge_color
        else:
            self.node_color = commit_color
        self.sha1_text = commit.sha1[:8]

        self.pressed = False
        self.dragged = False

    #
    # Overridden Qt methods
    #

    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemSelectedHasChanged:
            if value.toPyObject():
                if not self.scene().parent().selecting():
                    sig = signals.commit_selected
                    self.nodecom.notify_message_observers(sig, self.commit)
                color = self._selected_color
            else:
                color = self._outline_color
            node_pen = QtGui.QPen()
            node_pen.setWidth(1.0)
            node_pen.setColor(color)
            self._node_pen = node_pen
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
              black_pen=QtCore.Qt.black,
              cache=Cache):

        painter.setPen(self._node_pen)
        painter.setBrush(self.node_color)

        # Draw ellipse
        painter.drawEllipse(inner)

        try:
            font = cache.font
        except AttributeError:
            font = cache.font = painter.font()
            font.setPointSize(5)

        painter.setFont(font)
        painter.setPen(black_pen)
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

        # Starts with enough space for two tags. Any more and the node
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
    def __init__(self, nodecom):
        QtGui.QGraphicsView.__init__(self)

        self._xoff = 132
        self._yoff = 32
        self._xmax = 0
        self._ymin = 0

        self._items = []
        self._selected = []
        self._nodes = {}
        self._nodecom = nodecom

        self._loc = {}
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
                               lambda: self._scale_view(1.5),
                               QtCore.Qt.Key_Plus,
                               QtCore.Qt.Key_Equal))

        self._action_zoom_out = (
            qtutils.add_action(self, 'Zoom Out',
                               lambda: self._scale_view(1.0/1.5),
                               QtCore.Qt.Key_Minus))

        self._action_zoom_fit = (
            qtutils.add_action(self, 'Zoom to Fit',
                               self._view_fit,
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

        self._action_export_patches = (
            qtutils.add_action(self, 'Export Patches',
                               self._export_patches))

    def contextMenuEvent(self, event):
        menu = QtGui.QMenu(self)
        menu.addAction(self._action_export_patches)
        menu.exec_(self.mapToGlobal(event.pos()))

    def add_commits(self, commits):
        """Traverse commits and add them to the view."""
        self.add(commits)
        self.layout(commits)
        self.link(commits)

    def select(self, sha1):
        """Select the node for the SHA-1"""
        try:
            node = self._nodes[sha1]
        except KeyError:
            return
        node.setSelected(True)
        self.ensureVisible(node.mapRectToScene(node.boundingRect()))

    def selected_node(self):
        """Return the currently selected node"""
        selected_nodes = self.selected_nodes()
        if not selected_nodes:
            return None
        return selected_nodes[0]

    def selected_nodes(self):
        """Return the currently selected node"""
        return self.scene().selectedItems()

    def get_node_by_generation(self, commits, criteria_fn):
        """Return the node for the commit matching criteria"""
        if not commits:
            return None
        generation = None
        for commit in commits:
            if (generation is None or
                    criteria_fn(generation, commit.generation)):
                sha1 = commit.sha1
                generation = commit.generation
        try:
            return self._nodes[sha1]
        except KeyError:
            return None

    def oldest_node(self, commits):
        """Return the node for the commit with the oldest generation number"""
        return self.get_node_by_generation(commits, lambda a, b: a > b)

    def newest_node(self, commits):
        """Return the node for the commit with the newest generation number"""
        return self.get_node_by_generation(commits, lambda a, b: a < b)

    def _export_patches(self):
        nodes = self.selected_nodes()
        for node in nodes:
            print node.commit.sha1

    def _select_parent(self):
        """Select the parent with the newest generation number"""
        selected_node = self.selected_node()
        if selected_node is None:
            return
        parent_node = self.newest_node(selected_node.commit.parents)
        if parent_node is None:
            return
        selected_node.setSelected(False)
        parent_node.setSelected(True)
        self.ensureVisible(parent_node.mapRectToScene(parent_node.boundingRect()))

    def _select_oldest_parent(self):
        """Select the parent with the oldest generation number"""
        selected_node = self.selected_node()
        if selected_node is None:
            return
        parent_node = self.oldest_node(selected_node.commit.parents)
        if parent_node is None:
            return
        selected_node.setSelected(False)
        parent_node.setSelected(True)
        self.ensureVisible(parent_node.mapRectToScene(parent_node.boundingRect()))

    def _select_child(self):
        """Select the child with the oldest generation number"""
        selected_node = self.selected_node()
        if selected_node is None:
            return
        child_node = self.oldest_node(selected_node.commit.children)
        if child_node is None:
            return
        selected_node.setSelected(False)
        child_node.setSelected(True)
        self.ensureVisible(child_node.mapRectToScene(child_node.boundingRect()))

    def _select_nth_child(self):
        """Select the Nth child with the newest generation number (N > 1)"""
        selected_node = self.selected_node()
        if selected_node is None:
            return
        if len(selected_node.commit.children) > 1:
            children = selected_node.commit.children[1:]
        else:
            children = selected_node.commit.children
        child_node = self.newest_node(children)
        if child_node is None:
            return
        selected_node.setSelected(False)
        child_node.setSelected(True)
        self.ensureVisible(child_node.mapRectToScene(child_node.boundingRect()))

    def _view_fit(self):
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
        adjust = 42.0
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
        self._selected = [i for i in self._items if i.isSelected()]

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
        if self._pressed:
            self._selecting = True
        self._last_mouse[0] = pos.x()
        self._last_mouse[1] = pos.y()
        self._handle_event(QtGui.QGraphicsView.mouseMoveEvent, event)

    def selecting(self):
        return self._selecting

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self._selecting = False
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
        self.scale(scale, scale)

    def add(self, commits):
        scene = self.scene()
        for commit in commits:
            node = Node(commit, self._nodecom)
            scene.addItem(node)
            self._nodes[commit.sha1] = node
            for ref in commit.tags:
                self._nodes[ref] = node
            self._items.append(node)

    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        for commit in commits:
            try:
                commit_node = self._nodes[commit.sha1]
            except KeyError:
                # TODO - Handle truncated history viewing
                pass
            for parent in commit.parents:
                parent_node = self._nodes[parent.sha1]
                edge = Edge(parent_node, commit_node)
                scene.addItem(edge)

    def layout(self, commits):
        if not self._loc:
            commit = commits[0]
            sha1 = commit.sha1
            node = self._nodes[sha1]
            self._loc[sha1] = (0, 0)
            self._rows[commit.generation] = [0]
            node.setPos(0, 0)
            commits = commits[1:]

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

            self._loc[sha1] = (xpos, ypos)
            node = self._nodes[sha1]
            node.setPos(xpos, ypos)

            row.append(xpos)
            xmax = max(xmax, xpos)
            ymin = min(ymin, ypos)

        self._xmax = xmax
        self._ymin = ymin
        self.scene().setSceneRect(self._xoff*-2, ymin-self._yoff*2,
                                  xmax+self._xoff*3, abs(ymin)+self._yoff*4)


if __name__ == "__main__":
    from cola.models import main

    model = main.model()
    model._init_config_data()
    app = QtGui.QApplication(sys.argv)
    view = git_dag(app.activeWindow())
    sys.exit(app.exec_())
