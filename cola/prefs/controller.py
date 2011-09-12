from cola.ctrl import Controller
from cola.prefs.model import command_directory


class PreferencesController(Controller):
    def __init__(self, model, view):
        Controller.__init__(self, model, view)

        self.add_command_directory(command_directory)
        self.add_command(model.message_set_config)
