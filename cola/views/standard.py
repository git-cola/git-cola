from PyQt4 import QtGui


def create_standard_widget(qtclass):
    """Create a standard widget derived from a qt class.
    """
    class StandardWidget(qtclass):
        # Mix-in for standard view operations
        def __init__(self, parent=None):
            self._qtclass = qtclass
            self._qtclass.__init__(self, parent)

        def show(self):
            """Automatically centers dialogs"""
            if self.parent():
                left = self.parent().x()
                width = self.parent().width()
                center_x = left + width/2

                x = center_x - self.width()/2
                y = self.parent().y()

                self.move(x, y)
            # Call the base Qt show()
            self._qtclass.show(self)

        def name(self):
            """Returns the name of the view class"""
            return self.__class__.__name__.lower()

        def apply_state(self, state):
            """Imports data for view save/restore"""
            try:
                self.resize(state['width'], state['height'])
            except:
                pass
            try:
                self.move(state['x'], state['y'])
            except:
                pass

        def export_state(self):
            """Exports data for view save/restore"""
            return {
                'x': self.x(),
                'y': self.y(),
                'width': self.width(),
                'height': self.height(),
            }

    return StandardWidget


# The base class for all cola QDialogs.
Dialog = create_standard_widget(QtGui.QDialog)
MainWindow = create_standard_widget(QtGui.QMainWindow)
