from PyQt4 import QtCore

from cola.views import syntax


def create_standard_view(uiclass, qtclass, *classes):
    """create_standard_view returns a class closure of uiclass and qtclass.
    This class performs the standard setup common to all view classes.

    The reason we use a closure is because uiclass and qtclass are
    both dynamic.

    """
    class StandardView(uiclass, qtclass):
        def __init__(self, parent, *args, **kwargs):
            qtclass.__init__(self, parent)
            uiclass.__init__(self)
            self.__qtclass = qtclass
            self.setWindowFlags(QtCore.Qt.Window)
            self.parent_view = parent
            syntax.set_theme_properties(self)
            self.setupUi(self)
            for cls in classes:
                cls.__init__(self, parent, *args, **kwargs)

        def show(self):
            """Automatically centers dialogs relative to their
            parent window.

            """
            if self.parent_view:
                left = self.parent_view.x()
                width = self.parent_view.width()
                center_x = left + width/2

                x = center_x - self.width()/2
                y = self.parent_view.y()

                self.move(x, y)
            # Call the base Qt show()
            self.__qtclass.show(self)
        def get_properties(self):
            # user-definable color properties
            props = {}
            for name in syntax.default_colors:
                props[name] = getattr(self, '_'+name)
            return props
        def reset_syntax(self):
            if hasattr(self, 'syntax') and self.syntax:
                self.syntax.set_colors(self.get_properties())
                self.syntax.reset()
    syntax.install_theme_properties(StandardView)
    return StandardView
