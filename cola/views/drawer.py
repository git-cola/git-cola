import PyQt4
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

class Drawer(QtGui.QWidget):
    '''Drawers contain other widgets and show/hide them as a group
    
    Drawers is best used with a DrawerWindow but can be used as a
    standalone widget.  It has four areas it knows
    about which dictate how the child widgets are laid out an how the 
    drawer is drawn.

    You can specify a particular drawer in a stylesheet by using the name
    syntax as follows
    
    Drawer#left > DrawerHandle
    Drawer#right > DrawerHandle
    Drawer#top > DrawerHandle
    Drawer#bottom > DrawerHandle
    '''
    LOCATION_LEFT   = 0
    LOCATION_RIGHT  = 1
    LOCATION_TOP    = 2
    LOCATION_BOTTOM = 3
    LOCATION_ALL    = 4
    
    def __init__(self, parent=None, location=LOCATION_LEFT, drawersize=10):
        QtGui.QWidget.__init__(self, parent)
        # self.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Plain)
        self._location = location
        
        ## the parent of any added widgets, we set the name to 'base' so it
        ## can be referred to in a stylesheet using the 
        ## Drawer > QWidget#base { ... }
        self._widgetparent = QtGui.QWidget(self)
        self._widgetparent.setObjectName("base")

        self._widgetlayout = QtGui.QHBoxLayout(self._widgetparent)
        self._widgetlayout.setContentsMargins(0,0,0,0)
        self._widgetlayout.setSpacing(0)

        ## the 'button' for toggling the visible state of the drawer
        self._drawer = DrawerHandle(self)

        ## keeps track of the state of the drawer
        self._closed = True

        ## the width of the drawer handle
        self._drawerwidth = drawersize

        ## default open/closed pixmaps
        self._pixmap = {}
        for location in range(Drawer.LOCATION_ALL):
            self._pixmap.setdefault(location, {})

        ## grab stock icons
        iconopen   = self.style().standardPixmap(QtGui.QStyle.SP_TitleBarShadeButton).scaledToWidth(self._drawerwidth)
        iconclosed = self.style().standardPixmap(QtGui.QStyle.SP_TitleBarUnshadeButton).scaledToWidth(self._drawerwidth)
        
        if self._location == Drawer.LOCATION_LEFT:
            # if this is located on left hand side it must appear horizontal
            self._drawer.setFixedWidth(self._drawerwidth)
            self._baselayout = QtGui.QHBoxLayout(self)
 
            # widgets show up on the far left with drawer button on the right
            self._baselayout.addWidget(self._drawer)
            self._baselayout.addWidget(self._widgetparent)

            transform = QtGui.QTransform()
            transform.rotate(-90)
            iconopen   = iconopen.transformed(transform)
            iconclosed = iconclosed.transformed(transform)

            ## the parent of any added widgets, we set the name to 'left'
            ## so it can be referred to in a stylesheet using the 
            ## Drawer#left { ... }
            self.setObjectName("left")
            
        elif self._location == Drawer.LOCATION_RIGHT:
            # if this is located on right hand side it must appear horizontal
            self._drawer.setFixedWidth(self._drawerwidth)
            self._baselayout = QtGui.QHBoxLayout(self)
    
            # widgets show up on the far right with drawer button on the left
            self._baselayout.addWidget(self._widgetparent)
            self._baselayout.addWidget(self._drawer)
            
            transform = QtGui.QTransform()
            transform.rotate(90)
            iconopen   = iconopen.transformed(transform)
            iconclosed = iconclosed.transformed(transform)

            ## the parent of any added widgets, we set the name to 'right'
            ## so it can be referred to in a stylesheet using the 
            ## Drawer#right { ... }
            self.setObjectName("right")

        elif self._location == Drawer.LOCATION_TOP:
            # if this is located on top it must appear vertical
            self._drawer.setFixedHeight(self._drawerwidth)
            self._baselayout = QtGui.QVBoxLayout(self)
    
            # widgets show up on the bottom with drawer button on the top
            self._baselayout.addWidget(self._drawer)
            self._baselayout.addWidget(self._widgetparent)
        
            ## the parent of any added widgets, we set the name to 'top'
            ## so it can be referred to in a stylesheet using the 
            ## Drawer#top { ... }
            self.setObjectName("top")

        elif self._location == Drawer.LOCATION_BOTTOM:
            # if this is located on bottom it must appear vertical
            self._drawer.setFixedHeight(self._drawerwidth)
            self._baselayout = QtGui.QVBoxLayout(self)
    
            # widgets show up on the far right with drawer button on the left
            self._baselayout.addWidget(self._widgetparent)
            self._baselayout.addWidget(self._drawer)

            transform = QtGui.QTransform()
            transform.rotate(180)
            iconopen   = iconopen.transformed(transform)
            iconclosed = iconclosed.transformed(transform)
            
            ## the parent of any added widgets, we set the name to 'bottom'
            ## so it can be referred to in a stylesheet using the 
            ## Drawer#bottom { ... }
            self.setObjectName("bottom")

        # default icons
        self._drawer.set_pixmap('closed', iconclosed)
        self._drawer.set_pixmap('hover closed', iconclosed)
        self._drawer.set_pixmap('open', iconopen)
        self._drawer.set_pixmap('hover open', iconopen)
        
        # update the pixmap for the drawer
        self._drawer.update()

        self._baselayout.setSpacing(0)
        self._baselayout.setContentsMargins(0, 0, 0, 0)

        self._baselayout.setStretchFactor(self._drawer, 0)
        self._baselayout.setStretchFactor(self._widgetparent, 1)

        self._drawer.installEventFilter(self)
        self._drawer.setMouseTracking(True)
        self._widgetparent.hide()
        self.connect(self._drawer, SIGNAL('toggled(bool)'), self._close)

    def _close(self, state):
        self._closed = state
        self._widgetparent.setVisible(not self._closed)

    def close(self, state):
        '''toggles the open/closed state of the drawer
        '''
        self._close(state)
        self._drawer.close(state)

    def add_widget(self, widget, openmode=False):
        '''add a new widget to the drawer's layout
        '''
        self._widgetlayout.addWidget(widget)
        widget.show()
        self.close(not openmode)

    def isOpen(self):
        return not self._drawer.closed()


class DrawerHandle(QtGui.QWidget):
    '''DrawerHandle is the 'button'/'handle' of a Drawer
    and is ment to be used exclusively by a Drawer.  It has several
    properties that are accessible through a stylesheet.  They are as follows

    qproperty-open_pixmap : url(path)
    qproperty-closed_pixmap : url(path)
    qproperty-hover_open_pixmap : url(path)
    qproperty-hover_closed_pixmap : url(path)

    It also includes all properties you can set on a normal QWidget.
    '''
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        openpixmap   = self.style().standardPixmap(QtGui.QStyle.SP_TitleBarShadeButton)
        closedpixmap = self.style().standardPixmap(QtGui.QStyle.SP_TitleBarUnshadeButton)

        self._closed = True
        self._hover  = False

        self._pixmap = {}

        self.set_pixmap('hover open', openpixmap)
        self.set_pixmap('hover closed', closedpixmap)
        self.set_pixmap('open', openpixmap)
        self.set_pixmap('closed', closedpixmap)

    def closed(self):
        return self._closed

    def close(self, close):
        self._closed = close
        self.update()

    def pixmap(self, state):
        if state not in self._pixmap:
            return QtGui.QPixmap()
        return self._pixmap[state]

    def set_pixmap(self, state, pixmap):
        self._pixmap[state] = pixmap
        self.update()

    def sethover_open_pixmap(self, pixmap):
        self._pixmap['hover open'] = pixmap
        self.update()

    def setopen_pixmap(self, pixmap):
        self._pixmap['open'] = pixmap
        self.update()

    def sethover_closed_pixmap(self, pixmap):
        self._pixmap['hover closed'] = pixmap
        self.update()

    def setclosed_pixmap(self, pixmap):
        self._pixmap['closed'] = pixmap
        self.update()

    def _current_pixmap(self):
        if self._closed:
            if self._hover:
                return self._pixmap['hover closed']
            return self._pixmap['closed']
        if self._hover:
            return self._pixmap['hover open']
        return self._pixmap['open']
    
    def event(self, event):
        etype = event.type()
        if etype in [ QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonDblClick]:
            self._closed = not self._closed
            self.emit(SIGNAL("toggled(bool)"), self._closed)
        elif etype == QtCore.QEvent.Enter:
            self._hover = True
            self.update()
        elif etype == QtCore.QEvent.Leave:
            self._hover = False
            self.update()
        return QtGui.QWidget.event(self, event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(event.rect(), self.palette().brush(self.backgroundRole()))
        
        pixmap  = self._current_pixmap()
        centery = float(self.height())/2.0 - float(pixmap.height())/2.0
        centerx = float(self.width())/2.0 - float(pixmap.width())/2.0
        pixmaprect = QtCore.QRectF(centerx, centery, pixmap.width(), pixmap.height())
        painter.drawPixmap(pixmaprect, pixmap, QtCore.QRectF(pixmap.rect()))

        painter.end()

    open_pixmap = QtCore.pyqtProperty('QPixmap',
            lambda x    : DrawerHandle.pixmap(x, 'open'),
            lambda x, y : DrawerHandle.set_pixmap(x, 'open', y))

    closed_pixmap = QtCore.pyqtProperty('QPixmap',
            lambda x    : DrawerHandle.pixmap(x, 'closed'),
            lambda x, y : DrawerHandle.set_pixmap(x, 'closed', y))

    hover_open_pixmap = QtCore.pyqtProperty('QPixmap',
            lambda x    : DrawerHandle.pixmap(x, 'hover open'),
            lambda x, y : DrawerHandle.set_pixmap(x, 'hover open', y))

    hover_closed_pixmap = QtCore.pyqtProperty('QPixmap',
            lambda x    : DrawerHandle.pixmap(x, 'hover closed'),
            lambda x, y : DrawerHandle.set_pixmap(x, 'hover closed', y))


if __name__ == "__main__":
    # visual unit test
    app = QtGui.QApplication([])
    dialog = QtGui.QDialog()
    layout = QtGui.QHBoxLayout(dialog)
    layout.setContentsMargins(0,0,0,0)
    drawer = Drawer(dialog)
    drawer.add_widget(QtGui.QLabel("MY WIDGET", drawer))
    drawer.setStyleSheet('''
    Drawer > QWidget#base {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #343434, stop:1 #202020);
    }
    DrawerHandle { background-color: #FF0000; }''')
    layout.addWidget(drawer)
    dialog.setMinimumSize(320, 180)
    dialog.show()
    app.exec_()
