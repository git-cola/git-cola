from cola.ctrl import Controller
from cola.dag.model import command_directory


class GitDAGController(Controller):
    def __init__(self, model, view):
        Controller.__init__(self, model, view)
        self.add_commands(command_directory)
