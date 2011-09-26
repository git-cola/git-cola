"""Translate signals from the merge dialog."""

from cola import signals
from cola.ctrl import Controller
from cola.merge.model import command_directory


class MergeController(Controller):
    def __init__(self, model, view):
        Controller.__init__(self, model, view)

        self.add_command_directory(command_directory)
        self.add_command(model.message_merge)
        self.add_global_command(signals.visualize_revision)
