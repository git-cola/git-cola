from PyQt4.QtCore import SIGNAL
from cola.qtutils import SLOT

from cola.cmdfactory import CommandFactory


class Controller(object):
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.commands = {}
        self.factory = CommandFactory(model)

    def add_command_directory(self, command_directory):
        for signal, cmdclass in command_directory.items():
            self.factory.add_command(signal, cmdclass)

    def add_command(self, signal, handler=None):
        if handler is None:
            handler = self.do_wrapper(signal)
        self.view.connect(self.view, SIGNAL(signal), handler)

    def add_global_command(self, signal):
        self.view.connect(self.view, SIGNAL(signal), SLOT(signal))

    def do_wrapper(self, signal):
        def do(*args, **opts):
            return self.factory.do(signal, *args, **opts)
        return do
