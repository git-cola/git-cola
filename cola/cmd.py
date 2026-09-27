"""Base Command class"""
from __future__ import annotations
import time
from typing import TYPE_CHECKING

from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

if TYPE_CHECKING:
    from .app import ApplicationContext


class Command:
    """Mixin interface for commands"""

    UNDOABLE = False

    @classmethod
    def name(cls) -> str:
        """Return the command's display name"""
        # NOTE: subclasses should implement this.
        return cls.__name__

    @classmethod
    def is_undoable(cls) -> bool:
        """Can this be undone?"""
        return cls.UNDOABLE

    def do(self) -> bool:
        """Execute the command

        Returns False to signal that an operation should be aborted.
        """
        return True

    def undo(self) -> bool:
        """Undo the command

        Returns False to signal that an operation should be aborted.
        """
        return True

    def refresh(self) -> None:
        """Refresh a command so that it can be rerun"""
        pass


class ContextCommand(Command):
    """Base class for commands that operate on a context"""

    def __init__(self, context: ApplicationContext) -> None:
        super().__init__()
        self.timestamp = time.time()
        self.context = context
        self.model = context.model
        self.cfg = context.cfg
        self.git = context.git
        self.selection = context.selection
        self.fsmonitor = context.fsmonitor
        self.old_timestamp = context.timestamp

    def do(self) -> bool:
        """Update the context"""
        # Commands can get executed in the background, and completion of one command may
        # happen *after* another Diff and similar commands have been fired. We prevent
        # the delayed background lookup from overwriting a newer command by checking the
        # context's timestamp.
        if self.context.timestamp > self.timestamp:
            return False
        super().do()
        self.context.timestamp = self.timestamp
        return True

    def undo(self) -> bool:
        result = super().undo()
        self.context.timestamp = self.old_timestamp
        return result

    def refresh(self) -> None:
        super().refresh()
        self.timestamp = time.time()


class CommandNode:
    def __init__(self, cmd, parent=None):
        self.cmd = cmd
        self.parent = parent
        # Commands along the first child chain are the newer / active commands.
        # Later we can add UI to allow selecting other branches.
        self.children = []


class CommandGraph:
    """Maintain a graph of undo/redo commands

    Provides multiple undo branching histories, a current cursor, and methods
    for querying the undo history.

    The undo history is represented as a DAG of commands.
    Undoing into the past and then issuing new commands forks the undo history,
    such that multiple dimensions of history can exist.

    The history is a list of commands, with forks are represented as nested lists
    contained commands and further nested lists along each constituent branch.

    """

    def __init__(self):
        self.root = None
        self.cursor = None

    def add(self, cmd):
        if not cmd.is_undoable():
            return

        if self.root is None:
            self.root = CommandNode(cmd)
            self.cursor = self.root
            return

        new_node = CommandNode(cmd, parent=self.cursor)

        # If the cursor is None then are replacing the root.
        if self.cursor is None:
            self.root = new_node
            self.cursor = new_node
        else:
            self.cursor.children.insert(0, new_node)
            self.cursor = new_node

    def step_forward(self):
        # No cursor so the next step is the root.
        if not self.cursor:
            self.cursor = self.root
            if self.cursor:
                return self.cursor.cmd
            return None

        if self.cursor and self.cursor.children:
            self.cursor = self.cursor.children[0]
            return self.cursor.cmd

        return None

    def step_backward(self):
        if self.cursor:
            cmd = self.cursor.cmd
            self.cursor = self.cursor.parent
        else:
            cmd = None
        return cmd

    def get_next_command(self):
        if self.cursor:
            if self.cursor.children:
                return self.cursor.children[0].cmd
            return None
        if self.root:
            return self.root.cmd
        return None

    def get_current_command(self):
        if self.cursor:
            return self.cursor.cmd
        return None


class CommandBus(QtCore.QObject):
    do_command = Signal(object)
    undo_command = Signal(object)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.cmd_graph = CommandGraph()
        self.do_command.connect(lambda cmd: cmd.do(), type=Qt.QueuedConnection)
        self.undo_command.connect(lambda cmd: cmd.undo(), type=Qt.QueuedConnection)

    def do(self, cmd: Command, queued=True) -> None:
        """Run a command on the main thread"""
        self.cmd_graph.add(cmd)
        if queued:
            self.do_command.emit(cmd)
        else:
            cmd.do()

    def redo(self) -> bool:
        cmd = self.cmd_graph.step_forward()
        if cmd is not None:
            cmd.refresh()
            self.do_command.emit(cmd)
            return True
        return False

    def undo(self) -> bool:
        """Undo a command on the main thread"""
        cmd = self.cmd_graph.step_backward()
        if cmd is not None:
            cmd.refresh()
            self.undo_command.emit(cmd)
            return True
        return False

    def can_redo(self):
        """Can we perform a redo operation?"""
        return self.cmd_graph.get_next_command() is not None

    def can_undo(self):
        """Can we perform an undo?"""
        cmd = self.cmd_graph.get_current_command()
        return cmd is not None

    def get_undo_command_name(self):
        """Get the name of the command that will be undone"""
        cmd = self.cmd_graph.get_current_command()
        if cmd is not None:
            return cmd.name()
        return ''

    def get_redo_command_name(self):
        """Get the name of the command that will be redone"""
        cmd = self.cmd_graph.get_next_command()
        if cmd is not None:
            return cmd.name()
        return ''


def undo(context):
    context.command_bus.undo()


def redo(context):
    context.command_bus.redo()
