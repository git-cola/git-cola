"""This controller handles the stash dialog."""

from cola import signals
from cola.ctrl import Controller


class StashController(Controller):
    def __init__(self, model, view):
        Controller.__init__(self, model, view)

        self.add_global_command(signals.rescan)
