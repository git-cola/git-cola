"""Provides the main application controller."""

from cola.ctrl import Controller
from cola import guicmds
from cola import signals
from cola.views import actions


class MainController(Controller):
    def __init__(self, model, view):
        Controller.__init__(self, model, view)

        # Install UI wrappers for command objects
        actions.install_command_wrapper(self.view)
        guicmds.install_command_wrapper(self.view)

        self.add_global_command(signals.amend_mode)
        self.add_global_command(signals.diffstat)
        self.add_global_command(signals.load_commit_message)
        self.add_global_command(signals.load_commit_template)
        self.add_global_command(signals.rescan)
        self.add_global_command(signals.reset_mode)
        self.add_global_command(signals.run_config_action)
        self.add_global_command(signals.signoff)
        self.add_global_command(signals.stage_untracked)
        self.add_global_command(signals.stage_modified)
        self.add_global_command(signals.stage_untracked)
        self.add_global_command(signals.unstage_all)
        self.add_global_command(signals.unstage_selected)
        self.add_global_command(signals.visualize_all)
        self.add_global_command(signals.visualize_current)
