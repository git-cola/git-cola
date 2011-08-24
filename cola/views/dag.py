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
from cola.decorators import memoize
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


class GitCommitView(QtGui.QWidget):
    def __init__(self, parent=None, nodecom=None):
        QtGui.QWidget.__init__(self, parent)

        self.diff = QtGui.QTextEdit()
        self.diff.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.diff.setReadOnly(True)
        self.diff_syn = syntax.DiffSyntaxHighlighter(self.diff.document())
        qtutils.set_diff_font(self.diff)

        self._layt = QtGui.QVBoxLayout()
        self._layt.addWidget(self.diff)
        self._layt.setMargin(2)
        self.setLayout(self._layt)

        sig = signals.sha1_selected
        nodecom.add_message_observer(sig, self._node_selected)

    def _node_selected(self, sha1):
        self.diff.setText(gitcmds.diff_info(sha1))
        qtutils.set_clipboard(sha1)


class GitDAGWidget(standard.StandardDialog):
    """The git-dag widget."""
    # Keep us in scope otherwise PyQt kills the widget
    def __init__(self, parent=None, args=None):
        standard.StandardDialog.__init__(self, parent=parent)

        self.setObjectName('dag')
        self.setWindowTitle(self.tr('git dag'))
        self.setMinimumSize(1, 1)

        self._queue = []

        self._splitter = QtGui.QSplitter()
        self._splitter.setOrientation(QtCore.Qt.Vertical)
        self._splitter.setChildrenCollapsible(True)

        self._nodecom = observable.Observable()
        self._graphview = GraphView(nodecom=self._nodecom)
        self._widget = GitCommitView(nodecom=self._nodecom)

        self._splitter.insertWidget(0, self._graphview)
        self._splitter.insertWidget(1, self._widget)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)

        self._layt = layt = QtGui.QHBoxLayout()
        layt.setMargin(0)
        layt.addWidget(self._splitter)
        self.setLayout(layt)

        self._splitter.setSizes([self.height()*2/3, self.height()/3])


        qtutils.add_close_action(self)
        if not parent:
            qtutils.center_on_screen(self)

        self.thread = ReaderThread(self, args)

        self.thread.connect(self.thread, self.thread.commit_ready,
                            self._add_commit)

        self.thread.connect(self.thread, self.thread.done,
                            self._thread_done)

    def _add_commit(self, sha1):
        self._queue.append(self.thread.repo[sha1])
        if len(self._queue) > 64:
            self.process_queue()

    def process_queue(self):
        commits = self._queue
        if not commits:
            return
        self._queue = []
        self.add_commits(commits)

    def _thread_done(self):
        self.process_queue()
        for scrollbar in (self._graphview.verticalScrollBar(),
                          self._graphview.horizontalScrollBar()):
            if scrollbar:
                scrollbar.setValue(scrollbar.minimum())
        self._graphview.select('HEAD')

    def add_commits(self, commits):
        self._graphview.add_commits(commits)

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

    commit_ready = QtCore.SIGNAL('commit_ready')
    done = QtCore.SIGNAL('done')

    def __init__(self, parent, args):
        super(ReaderThread, self).__init__(parent)
        self.repo = commit.RepoReader(args=args)
        self.abort = False
        self.stop = False
        self.mutex = QtCore.QMutex()
        self.condition = QtCore.QWaitCondition()

    def run(self):
        for commit in self.repo:
            self.mutex.lock()
            if self.stop:
                self.condition.wait(self.mutex)
            self.mutex.unlock()
            if self.abort:
                self.repo.reset()
                return
            self.emit(self.commit_ready, commit.sha1)
        self.emit(self.done)


_arrow_size = 4.0
_arrow_extra = (_arrow_size + 1.0) / 2.0

class Edge(QtGui.QGraphicsItem):
    _type = QtGui.QGraphicsItem.UserType + 2

    def __init__(self, source, dest):
        QtGui.QGraphicsItem.__init__(self)

        self.source_pt = QtCore.QPointF()
        self.dest_pt = QtCore.QPointF()
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.source = source
        self.dest = dest
        self.source.add_edge(self)
        self.dest.add_edge(self)
        self.setZValue(-2)
        self.adjust()

    def type(self, _type=_type):
        return _type

    def adjust(self):
        if not self.source or not self.dest:
            return

        dest_glyph_pt = self.dest.glyph().center()
        line = QtCore.QLineF(
                self.mapFromItem(self.source, dest_glyph_pt),
                self.mapFromItem(self.dest, dest_glyph_pt))

        length = line.length()
        if length == 0.0:
            return

        offset = QtCore.QPointF((line.dx() * 23) / length,
                                (line.dy() * 9) / length)

        self.prepareGeometryChange()
        self.source_pt = line.p1() + offset
        self.dest_pt = line.p2() - offset

    @memoize
    def boundingRect(self, _extra=_arrow_extra):
        if not self.source or not self.dest:
            return QtCore.QRectF()
        width = self.dest_pt.x() - self.source_pt.x()
        height = self.dest_pt.y() - self.source_pt.y()
        rect = QtCore.QRectF(self.source_pt, QtCore.QSizeF(width, height))
        return rect.normalized().adjusted(-_extra, -_extra, _extra, _extra)

    def paint(self, painter, option, widget, _arrow_size=_arrow_size):
        if not self.source or not self.dest:
            return
        # Draw the line itself.
        line = QtCore.QLineF(self.source_pt, self.dest_pt)
        length = line.length()
        if length > 2 ** 13:
            return

        painter.setPen(QtGui.QPen(QtCore.Qt.gray, 0,
                                  QtCore.Qt.DotLine,
                                  QtCore.Qt.FlatCap,
                                  QtCore.Qt.MiterJoin))
        painter.drawLine(line)

        # Draw the arrows if there's enough room.
        angle = math.acos(line.dx() / length)
        if line.dy() >= 0:
            angle = 2.0 * math.pi - angle

        dest_x = (self.dest_pt +
                  QtCore.QPointF(math.sin(angle - math.pi/3.) *
                                 _arrow_size,
                                 math.cos(angle - math.pi/3.) *
                                 _arrow_size))
        dest_y = (self.dest_pt +
                  QtCore.QPointF(math.sin(angle - math.pi + math.pi/3.) *
                                 _arrow_size,
                                 math.cos(angle - math.pi + math.pi/3.) *
                                 _arrow_size))

        painter.setBrush(QtCore.Qt.gray)
        painter.drawPolygon(QtGui.QPolygonF([line.p2(), dest_x, dest_y]))


class Node(QtGui.QGraphicsItem):
    _type = QtGui.QGraphicsItem.UserType + 1
    _width = 150
    _height = 16

    _shape = QtGui.QPainterPath()
    _shape.addRect(_width/-2., _height/-2., _width, _height)

    _bound = _shape.boundingRect()
    _glyph = QtCore.QRectF(-_width/2., -_height/2, _width/4., _height)

    _colors_selected = QtGui.QColor.fromRgb(255, 255, 0)
    _colors_outline = QtGui.QColor.fromRgb(64, 96, 192)
    _colors_decorations = QtGui.QColor.fromRgb(255, 255, 64)

    _colors_commit = QtGui.QColor.fromRgb(128, 222, 255)
    _colors_merge = QtGui.QColor.fromRgb(255, 255, 255)

    def __init__(self, commit, nodecom):
        QtGui.QGraphicsItem.__init__(self)
        self.setZValue(0)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)

        self.commit = commit
        self._nodecom = nodecom

        # Starts with enough space for two tags. Any more and the node
        # needs to be taller to accomodate.
        if len(self.commit.tags) > 1:
            self._height = len(self.commit.tags) * self._height/2 + 6 # +6 padding
        self._edges = []

        if len(commit.parents) > 1:
            self._colors_node = self._colors_merge
        else:
            self._colors_node = self._colors_commit

        self.pressed = False
        self.dragged = False
        self.skipped = False

    def itemChange(self, change, value):
        if (change == QtGui.QGraphicsItem.ItemSelectedHasChanged and
                value.toPyObject()):
            sig = signals.sha1_selected
            self._nodecom.notify_message_observers(sig, self.commit.sha1)
        return QtGui.QGraphicsItem.itemChange(self, change, value)

    def type(self, _type=_type):
        return _type

    def add_edge(self, edge):
        self._edges.append(edge)

    def boundingRect(self, _bound=_bound):
        return _bound

    def shape(self, _shape=_shape):
        return _shape

    def glyph(self, _glyph=_glyph):
        """Provides location of the glyph representing this node

        The node contains a glyph (a circle or ellipse) representing the
        node, as well as other text alongside the glyph.  Knowing the
        location of the glyph, rather than the entire node allows us to
        make edges point at the center of the glyph, rather than at the
        center of the entire node.
        """
        return _glyph

    def paint(self, painter, option, widget):
        pen = QtGui.QPen()
        pen.setWidth(1.5)
        if self.isSelected():
            pen.setColor(self._colors_selected)
        else:
            pen.setColor(self._colors_outline)
        painter.setPen(pen)
        painter.setBrush(self._colors_node)

        # Draw glyph
        painter.drawEllipse(self.glyph())
        sha1_text = self.commit.sha1[:8]
        font = painter.font()
        font.setPointSize(5)
        painter.setFont(font)
        painter.setPen(QtCore.Qt.black)

        text_options = QtGui.QTextOption()
        text_options.setAlignment(QtCore.Qt.AlignCenter)
        painter.drawText(self.glyph(), sha1_text, text_options)

        # Draw tags
        if not self.commit.tags:
            return
        # Those 2's affecting width are just for padding
        text_box = QtCore.QRectF(-self._width/4.+2, -self._height/2.,
                                 self._width/2.2-2, self._height)
        painter.setBrush(self._colors_decorations)
        painter.drawRoundedRect(text_box, 4, 4)
        tag_text = "\n".join(self.commit.tags)
        text_options.setAlignment(QtCore.Qt.AlignVCenter)
        # A bit of padding for the text
        painter.translate(2.,0.)
        painter.drawText(text_box, tag_text, text_options)

    def mousePressEvent(self, event):
        self.pressed = True
        self.selected = self.isSelected()
        QtGui.QGraphicsItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.pressed:
            self.dragged = True
        QtGui.QGraphicsItem.mouseMoveEvent(self, event)
        for node in self.scene().selectedItems():
            for edge in node._edges:
                edge.adjust()
        self.scene().update()

    def mouseReleaseEvent(self, event):
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)
        if (not self.dragged
                and self.selected
                and event.button() == QtCore.Qt.LeftButton):
            self.setSelected(False)
            self.skipped = True
            return
        self.skipped = False
        self.pressed = False
        self.dragged = False


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

    def selected_node(self):
        """Return the currently selected node"""
        selected_nodes = self.scene().selectedItems()
        if not selected_nodes:
            return None
        return selected_nodes[0]

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
        self._selected = [ i for i in self._items if i.isSelected() ]

    def _restore_selection(self, event):
        if QtCore.Qt.ShiftModifier != event.modifiers():
            return
        for item in self._selected:
            if item.skipped:
                item.skipped = False
                continue
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
        self._handle_event(QtGui.QGraphicsView.mousePressEvent, event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self._panning:
            self._pan(event)
            return
        self._last_mouse[0] = pos.x()
        self._last_mouse[1] = pos.y()
        self._handle_event(QtGui.QGraphicsView.mouseMoveEvent, event)

    def mouseReleaseEvent(self, event):
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
