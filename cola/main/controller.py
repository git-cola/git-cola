"""Provides the main application controller."""

from cola.ctrl import Controller
from cola import signals


class MainController(Controller):
    def __init__(self, model, view):
        Controller.__init__(self, model, view)

        self.add_global_command(signals.run_config_action)
