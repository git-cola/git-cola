from cola.prefs.model import PreferencesModel
from cola.prefs.view import PreferencesView
from cola.prefs.view import diff_font
from cola.prefs.view import tabwidth
from cola.prefs.view import textwidth
from cola.prefs.view import linebreak


def preferences(model=None, parent=None):
    if model is None:
        model = PreferencesModel()
    prefs = PreferencesView(model, parent=parent)
    prefs.show()
    prefs.raise_()
    return prefs
