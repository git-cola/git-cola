from PyQt4 import QtCore

from cola.views import syntax


def create_standard_view(uiclass, qtclass, *classes):
    """Return a class closure of uiclass and qtclass.

    This class performs the standard setup common to all view classes.

    """
    widgetbase = create_standard_widget(qtclass)
    class StandardView(uiclass, widgetbase):
        def __init__(self, parent, *args, **kwargs):
            widgetbase.__init__(self, parent)
            uiclass.__init__(self)
            self.setupUi(self)
            for cls in classes:
                cls.__init__(self, parent, *args, **kwargs)
    return StandardView


def create_standard_widget(qtclass):
    """Create a standard widget derived from a qt class.
    """
    class StandardWidget(qtclass):
        # Mix-in for standard view operations
        def __init__(self, parent=None):
            self._qtclass = qtclass
            self._qtclass.__init__(self, parent)
            syntax.set_theme_properties(self)

        def show(self):
            """Automatically centers and raises dialogs"""
            if self.parent():
                left = self.parent().x()
                width = self.parent().width()
                center_x = left + width/2

                x = center_x - self.width()/2
                y = self.parent().y() + 22 # room for parent's titlebar

                self.move(x, y)
            # Call the base Qt show()
            self._qtclass.show(self)
            self.raise_()

        def name(self):
            """Returns the name of the view class"""
            return self.__class__.__name__.lower()

        def import_state(self, settings):
            """Imports data for view save/restore"""
            if 'width' in settings and 'height' in settings:
                w = settings.get('width')
                h = settings.get('height')
                try:
                    self.resize(w, h)
                except:
                    pass

            if 'x' in settings and 'y' in settings:
                x = settings.get('x')
                y = settings.get('y')
                try:
                    self.move(x, y)
                except:
                    pass

        def export_state(self):
            """Exports data for view save/restore"""
            state = {}
            for funcname in ('width', 'height', 'x', 'y'):
                state[funcname] = getattr(self, funcname)()
            return state

        def style_properties(self):
            # user-definable color properties
            props = {}
            for name in syntax.default_colors:
                props[name] = getattr(self, '_'+name)
            return props

        def reset_syntax(self):
            if hasattr(self, 'syntax') and self.syntax:
                self.syntax.set_colors(self.style_properties())
                self.syntax.reset()

    syntax.install_style_properties(StandardWidget)
    return StandardWidget
