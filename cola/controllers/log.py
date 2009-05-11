"""This module provides the controller for the log display

"""
from PyQt4 import QtCore

from cola import qtutils
from cola.views import LogView

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def logger(model, parent):
    """Returns an instance of a log controller."""
    return LogController(model, parent)

class LogController(object):
    """The output log controller."""

    def __init__(self, model, parent):
        self.model = model
        self.view = LogView(parent)
        self.parent = parent

    def clear(self):
        """Clears the log."""
        self.view.output_text.clear()

    def log(self, status, output):
        """Appends output into the log window"""
        if not output:
            return
        self.view.log(output)
        if self.model.should_display_log(status):
            self.parent.display_log()
