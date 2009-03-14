import PyQt4
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola.views.drawer import Drawer

class DrawerCentralWidget(QtGui.QWidget):
    """A central widget with four collapsable regions
    
    This can contain other widgets.
    Each region is a Drawer.
    """

    LOCATION_LEFT   = Drawer.LOCATION_LEFT
    LOCATION_RIGHT  = Drawer.LOCATION_RIGHT
    LOCATION_TOP    = Drawer.LOCATION_TOP
    LOCATION_BOTTOM = Drawer.LOCATION_BOTTOM

    def __init__(self, parent=None, hide_empty=True):
        QtGui.QWidget.__init__(self, parent)

        self._layout = QtGui.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        ## hide the drawer if there is no widget in it
        self._hide_empty = hide_empty

        # create all of the drawers
        self._drawertop = Drawer(self, Drawer.LOCATION_TOP)
        self._drawerleft = Drawer(self, Drawer.LOCATION_LEFT)
        self._drawerright = Drawer(self, Drawer.LOCATION_RIGHT)
        self._drawerbottom = Drawer(self, Drawer.LOCATION_BOTTOM)

        if self._hide_empty:
            self._drawertop.hide()
            self._drawerbottom.hide()
            self._drawerright.hide()
            self._drawerleft.hide()

        # create a widget as a parent/placeholder for the center widget
        self._centerwidgetparent = QtGui.QWidget(self)
        self._centerwidgetparent.setObjectName("base")

        self._centerwidget = None
        self._centerlayout = QtGui.QVBoxLayout(self._centerwidgetparent)
        self._centerlayout.setContentsMargins(0, 0, 0, 0)
        self._centerlayout.setMargin(0)
        
        # setup the central widget, left and right drawers in same layout
        hlayout = QtGui.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(0)

        hlayout.addWidget(self._drawerleft)
        hlayout.addWidget(self._centerwidgetparent)
        hlayout.addWidget(self._drawerright)

        hlayout.setStretchFactor(self._drawerleft, 0)
        hlayout.setStretchFactor(self._centerwidgetparent, 1)
        hlayout.setStretchFactor(self._drawerright, 0)

        # finalize the main layout
        self._layout.addWidget(self._drawertop)
        self._layout.setStretchFactor(self._drawertop, 0)
        
        self._layout.addLayout(hlayout)
        self._layout.setStretchFactor(hlayout, 1)

        self._layout.addWidget(self._drawerbottom)
        self._layout.setStretchFactor(self._drawerbottom, 0)


    def add_drawer(self, location, widget, opened=False):
        """Add a widget to one of the supported regions

        'location' refers to the enumeration in DrawerCentralWidget.
        This opens the drawer in the region when opened is True.

        """

        if location == DrawerCentralWidget.LOCATION_TOP:
            self._drawertop.add_widget(widget, opened)
            self._drawertop.show()

        elif location == DrawerCentralWidget.LOCATION_BOTTOM:
            self._drawerbottom.add_widget(widget, opened)
            self._drawerbottom.show()

        elif location == DrawerCentralWidget.LOCATION_LEFT:
            self._drawerleft.add_widget(widget, opened)
            self._drawerleft.show()
        
        elif location == DrawerCentralWidget.LOCATION_RIGHT:
            self._drawerright.add_widget(widget, opened)
            self._drawerright.show()
        else:
            raise Exception("Invalid drawer location: '%s'" % str(location))

            
    def setCentralWidget(self, widget):
        """Makes widget the center widget with the four surrounding drawers"""

        # remove the current center widget
        if self._centerwidget:
            self._centerwidget.hide()
            self._centerlayout.removeWidget(self._centerwidget)

        if widget is not None:
            widget.setParent(self._centerwidgetparent)
            self._centerlayout.addWidget(widget)
            self._centerwidget = widget
            self._centerwidget.show()
        
        # update the layout 
        self._centerlayout.invalidate()

    def open_drawer(self, location, opened=True):
        """Opens a drawer"""

        if location == DrawerCentralWidget.LOCATION_TOP:
            self._drawertop.close(not opened)

        elif location == DrawerCentralWidget.LOCATION_BOTTOM:
            self._drawerbottom.close(not opened)

        elif location == DrawerCentralWidget.LOCATION_LEFT:
            self._drawerleft.close(not opened)
        
        elif location == DrawerCentralWidget.LOCATION_RIGHT:
            self._drawerright.close(not opened)


class DrawerMainWindow(QtGui.QMainWindow):
    """Subclasses QMainWindow to provide four drawer regions"""

    LOCATION_LEFT   = Drawer.LOCATION_LEFT
    LOCATION_RIGHT  = Drawer.LOCATION_RIGHT
    LOCATION_TOP    = Drawer.LOCATION_TOP
    LOCATION_BOTTOM = Drawer.LOCATION_BOTTOM

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self._centralwidget = DrawerCentralWidget(self)
        QtGui.QMainWindow.setCentralWidget(self, self._centralwidget)

    def setCentralWidget(self, widget):
        self._centralwidget.setCentralWidget(widget)

    def add_drawer(self, region, widget, opened=False):
        self._centralwidget.add_drawer(region, widget, opened)

    def open_drawer(self, region, opened=True):
        self._centralwidget.open_drawer(region, opened)


if __name__ == "__main__":
    # visual unit test
    app = QtGui.QApplication([])
    
    dialog = DrawerMainWindow()

    ctr = QtGui.QLabel("MY CENTER WIDGET", dialog)
    lft = QtGui.QLabel("LEFT WIDGET", dialog)
    rgt = QtGui.QLabel("RIGHT WIDGET", dialog)
    top = QtGui.QLabel("TOP WIDGET", dialog)
    bot = QtGui.QLabel("BOTTOM WIDGET", dialog)
    
    dialog.add_drawer(DrawerMainWindow.LOCATION_LEFT, lft)
    dialog.add_drawer(DrawerMainWindow.LOCATION_RIGHT, rgt)
    dialog.add_drawer(DrawerMainWindow.LOCATION_TOP, top)
    dialog.add_drawer(DrawerMainWindow.LOCATION_BOTTOM, bot)

    dialog.setCentralWidget(ctr)

    # Stylesheet example
    dialog.setStyleSheet('''
    DrawerHandle {
        background: #000000;
    }
    Drawer > QWidget#base {
        background: #FFFFFF;
    }
    DrawerCentralWidget > QWidget#base {
        background: #FF0000;
    }
    Drawer#left > DrawerHandle { 
        qproperty-open_pixmap : url(leftarrow.png);
        qproperty-closed_pixmap : url(rightarrow.png); 
        qproperty-hover_open_pixmap : url(leftarrowHL.png); 
        qproperty-hover_closed_pixmap : url(rightarrowHL.png); 
    }
    Drawer#right > DrawerHandle { 
        qproperty-open_pixmap : url(rightarrow.png);
        qproperty-closed_pixmap : url(leftarrow.png); 
        qproperty-hover_open_pixmap : url(rightarrowHL.png); 
        qproperty-hover_closed_pixmap : url(leftarrowHL.png); 
    }
    Drawer#bottom > DrawerHandle { 
        qproperty-open_pixmap : url(downarrow.png);
        qproperty-closed_pixmap : url(uparrow.png); 
        qproperty-hover_open_pixmap : url(downarrowHL.png); 
        qproperty-hover_closed_pixmap : url(uparrowHL.png); 
    }
    Drawer#top > DrawerHandle { 
        qproperty-open_pixmap : url(uparrow.png);
        qproperty-closed_pixmap : url(downarrow.png); 
        qproperty-hover_open_pixmap : url(uparrowHL.png); 
        qproperty-hover_closed_pixmap : url(downarrowHL.png); 
    }
    ''')
    dialog.show()
    app.exec_()
