"""Base Command class"""
from qtpy import QtCore
from qtpy.QtCore import Qt, Signal


class Command:
    """Mixin interface for commands"""

    UNDOABLE = False

    @staticmethod
    def name():
        """Return the command's name"""
        return '(undefined)'

    @classmethod
    def is_undoable(cls):
        """Can this be undone?"""
        return cls.UNDOABLE

    def do(self):
        """Execute the command"""
        return

    def undo(self):
        """Undo the command"""
        return


class ContextCommand(Command):
    """Base class for commands that operate on a context"""

    def __init__(self, context):
        self.context = context
        self.model = context.model
        self.cfg = context.cfg
        self.git = context.git
        self.selection = context.selection
        self.fsmonitor = context.fsmonitor


class CommandBus(QtCore.QObject):
    do_command = Signal(object)
    undo_command = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.do_command.connect(lambda cmd: cmd.do(), type=Qt.QueuedConnection)
        self.undo_command.connect(lambda cmd: cmd.undo(), type=Qt.QueuedConnection)

    def do(self, cmd):
        """Run a command on the main thread"""
        self.do_command.emit(cmd)

    def undo(self, cmd):
        """Undo a command on the main thread"""
        self.undo_command.emit(cmd)
