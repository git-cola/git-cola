"""This controller handles the stash dialog."""

from cola.ctrl import Controller
from cola.stash.model import command_directory

class StashController(Controller):
    def __init__(self, model, view):
        Controller.__init__(self, model, view)
        self.add_commands(command_directory)
