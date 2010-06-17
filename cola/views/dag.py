import os
import sys
import math
from PyQt4 import QtGui
from PyQt4 import QtCore

if __name__ == "__main__":
    # Find the source tree
    src = os.path.join(os.path.dirname(__file__), '..', '..')
    sys.path.insert(0, os.path.abspath(src))

from cola import qtutils
from cola.models import commit
from cola.views import standard
from cola.compat import set
from cola.decorators import memoize


def git_dag(log_args=None, parent=None):
    """Return a pre-populated git DAG widget."""
    view = GitDAGWidget(parent)
    view.thread.start(QtCore.QThread.LowPriority)
    view.show()
    return view


class GitDAGWidget(standard.StandardDialog):
    """The git-dag widget."""
    # Keep us in scope otherwise PyQt kills the widget
    _instances = set()

    def delete(self):
        self._instances.remove(self)

    def __init__(self, parent=None, args=None):
        standard.StandardDialog.__init__(self, parent)
        self._instances.add(self)

        self.setObjectName('dag')
        self.setWindowTitle(self.tr('git dag'))
        self.setMinimumSize(1, 1)
        self.resize(777, 666)

        self._graphview = GraphView()
        layt = QtGui.QHBoxLayout()
        layt.setMargin(1)
        layt.addWidget(self._graphview)
        self.setLayout(layt)

        qtutils.add_close_action(self)
        if not parent:
            qtutils.center_on_screen(self)

        self.thread = ReaderThread(self, args)
        self.thread.connect(self.thread,
                            self.thread.commit_ready,
                            self._add_commit)

    def _add_commit(self, sha1):
        c = self.thread.repo[sha1]
        self.add_commits([c])

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


class ReaderThread(QtCore.QThread):

    commit_ready = QtCore.SIGNAL('commit_ready')

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

    def __init__(self, commit):
        QtGui.QGraphicsItem.__init__(self)
        self.setZValue(0)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
        self.commit = commit
        self._width = 180
        # Starts with enough space for two tags. Any more and the node
        # needs to be taller to accomodate.
        self._height = 18
        if len(self.commit.tags) > 1:
            self._height = len(self.commit.tags) * 9 + 6 # +6 padding
        self._edges = []

        self._colors = {}
        self._colors['bg'] = QtGui.QColor.fromRgb(16, 16, 16)
        self._colors['selected'] = QtGui.QColor.fromRgb(192, 192, 16)
        self._colors['outline'] = QtGui.QColor.fromRgb(0, 0, 0)
        self._colors['node'] = QtGui.QColor.fromRgb(255, 111, 69)
        self._colors['decorations'] = QtGui.QColor.fromRgb(255, 255, 42)

        self._grad = QtGui.QLinearGradient(0.0, 0.0, 0.0, self._height)
        self._grad.setColorAt(0, self._colors['node'])
        self._grad.setColorAt(1, self._colors['node'].darker())

        self.pressed = False
        self.dragged = False
        self.skipped = False

    @memoize
    def type(self):
        return Node._type

    def add_edge(self, edge):
        self._edges.append(edge)
        edge.adjust()

    @memoize
    def boundingRect(self):
        return self.shape().boundingRect()

    @memoize
    def shape(self):
        path = QtGui.QPainterPath()
        path.addRect(-self._width/2., -self._height/2.,
                     self._width, self._height)
        return path

    @memoize
    def glyph(self):
        """Provides location of the glyph representing this node

        The node contains a glyph (a circle or ellipse) representing the
        node, as well as other text alongside the glyph.  Knowing the
        location of the glyph, rather than the entire node allows us to
        make edges point at the center of the glyph, rather than at the
        center of the entire node.
        """
        glyph = QtCore.QRectF(-self._width/2., -9,
                              self._width/4., 18)
        return glyph

    def paint(self, painter, option, widget):
        if self.isSelected():
            self.setZValue(1)
            painter.setPen(self._colors['selected'])
        else:
            self.setZValue(0)
            painter.setPen(self._colors['outline'])
        painter.setBrush(self._grad)

        # Draw glyph
        painter.drawEllipse(self.glyph())
        sha1_text = self.commit.sha1
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
                                 self._width*(3/4.)-2, self._height)
        painter.setBrush(self._colors['decorations'])
        painter.drawRoundedRect(text_box, 4, 4)
        tag_text = "\n".join(self.commit.tags)
        text_options.setAlignment(QtCore.Qt.AlignVCenter)
        # A bit of padding for the text
        painter.translate(2.,0.)
        painter.drawText(text_box, tag_text, text_options)


    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemPositionChange:
            for edge in self._edges:
                edge.adjust()
            #self._graph.itemMoved()
        return QtGui.QGraphicsItem.itemChange(self, change, value)

    def mousePressEvent(self, event):
        self.selected = self.isSelected()
        self.pressed = True
        QtGui.QGraphicsItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.pressed:
            self.dragged = True
        QtGui.QGraphicsItem.mouseMoveEvent(self, event)

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
    def __init__(self):
        QtGui.QGraphicsView.__init__(self)

        self._xoff = 200
        self._yoff = 42
        self._xmax = 0
        self._ymax = 0

        self._items = []
        self._selected = []
        self._commits = {}
        self._children = {}
        self._nodes = {}

        self._loc = {}
        self._cols = {}

        self._panning = False
        self._last_mouse = [0, 0]

        self._zoom = 1
        self.scale(self._zoom, self._zoom)
        self.setDragMode(self.RubberBandDrag)

        size = 30000
        scene = QtGui.QGraphicsScene(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        scene.setSceneRect(-size/4, -size/2, size/2, size)
        self.setScene(scene)

        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorViewCenter)
        self.setBackgroundColor()

    def add_commits(self, commits):
        """Traverse commits and add them to the view."""
        self.add(commits)
        self.layout(commits)
        self.link(commits)

    def keyPressEvent(self, event):
        key = event.key()

        if key == QtCore.Qt.Key_Plus:
            self._scale_view(1.5)
        elif key == QtCore.Qt.Key_Minus:
            self._scale_view(1 / 1.5)
        elif key == QtCore.Qt.Key_F:
            self._view_fit()
        elif event.key() == QtCore.Qt.Key_Z:
            self._move_nodes_to_mouse_position()
        else:
            QtGui.QGraphicsView.keyPressEvent(self, event)

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
        if factor < 0.02 or factor > 42.0:
            return
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self._zoom = zoom
        self.scale(zoom, zoom)

    def _wheel_pan(self, event):
        """Handle mouse wheel panning."""

        if event.delta() < 0:
            s = -100.0
        else:
            s = 100.0

        pan_rect = QtCore.QRectF(0.0, 0.0, 1.0, 1.0)
        factor = 1.0 / self.matrix().mapRect(pan_rect).width()

        if event.orientation() == QtCore.Qt.Vertical:
            matrix = self.matrix().translate(0, s * factor)
        else:
            matrix = self.matrix().translate(s * factor, 0)

        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def _move_nodes_to_mouse_position(self):
        items = self.scene().selectedItems()
        if not items:
            return
        dx = 0
        dy = 0
        min_distance = sys.maxint
        for item in items:
            width = item.boundingRect().width()
            pos = item.pos()
            tmp_dx = self._last_mouse[0] - pos.x() - width/2.0
            tmp_dy = self._last_mouse[1] - pos.y() - width/2.0
            distance = math.sqrt(tmp_dx ** 2 + tmp_dy ** 2)
            if distance < min_distance:
                min_distance = distance
                dx = tmp_dx
                dy = tmp_dy
        for item in items:
            pos = item.pos()
            x = pos.x();
            y = pos.y()
            item.setPos( x + dx, y + dy )

    def setBackgroundColor(self, color=None):
        # To set a gradient background brush we need to use StretchToDeviceMode
        # but that seems to be segfaulting. Use a solid background.
        if not color:
            color = QtGui.QColor(50,50,50)
        self.setBackgroundBrush(color)

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
            self._commits[commit.sha1] = commit
            for p in commit.parents:
                children = self._children.setdefault(p, [])
                children.append(commit.sha1)
            node = Node(commit)
            scene.addItem(node)
            self._nodes[commit.sha1] = node
            self._items.append(node)

    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        for commit in commits:
            children = self._children.get(commit.sha1, None)
            # root commit
            if children is None:
                continue
            commit_node = self._nodes[commit.sha1]
            for child_sha1 in children:
                child_node = self._nodes[child_sha1]
                edge = Edge(commit_node, child_node)
                scene.addItem(edge)

    def layout(self, commits):
        gxmax = self._xmax
        gymax = self._ymax

        xpos = 0
        ypos = 0
        for commit in commits:
            if commit.sha1 not in self._children:
                self._loc[commit.sha1] = (xpos, ypos)
                node = self._nodes.get(commit.sha1, None)
                node.setPos(xpos, ypos)
                xpos += self._xoff
                gxmax = max(xpos, gxmax)
                continue
            ymax = 0
            xmax = None
            for sha1 in self._children[commit.sha1]:
                loc = self._loc[sha1]
                if xmax is None:
                    xmax = loc[0]
                xmax = min(xmax, loc[0])
                ymax = max(ymax, loc[1])
                gxmax = max(gxmax, xmax)
                gymax = max(gymax, ymax)
            if xmax is None:
                xmax = 0
            ymax += self._yoff
            gymax = max(gymax, ymax)
            if ymax in self._cols:
                xmax = max(xmax, self._cols[ymax] + self._xoff)
                gxmax = max(gxmax, xmax)
                self._cols[ymax] = xmax
            else:
                xmax = max(0, xmax)
                self._cols[ymax] = xmax

            sha1 = commit.sha1
            self._loc[sha1] = (xmax, ymax)
            node = self._nodes[sha1]
            node.setPos(xmax, ymax)

        xpad = 200
        ypad = 66
        self._xmax = gxmax
        self._ymax = gymax
        self.scene().setSceneRect(-xpad, -ypad, gxmax+xpad, gymax+ypad)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    view = git_dag()
    sys.exit(app.exec_())
