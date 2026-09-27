"""Base Command class"""
from __future__ import annotations
import time
from typing import TYPE_CHECKING
from typing import Any

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

    def __init__(self) -> None:
        self.history: list[Command | list] = []
        self.cursor: list[int] = []

    def add(self, cmd: Command) -> None:
        """Add an undoable command to the history"""
        if not cmd.is_undoable():
            return
        # If the cursor is not at the end of the history, we need to fork the history
        if self.cursor != self._end_cursor():
            branch = self._get_branch(self.cursor)
            # Fork the history by appending a new list to the current branch
            branch.append([])
            # Move the cursor to the new branch
            self.cursor.append(len(branch) - 1)
        # Add the command to the current branch
        branch = self._get_branch(self.cursor)
        branch.append(cmd)
        # Move the cursor to the new command
        self.cursor[-1] = len(branch) - 1

    def is_at_tail(self):
        """Is the current command the end of the current branch history?"""
        branch = self._get_branch(self.cursor)
        return isinstance(branch, list) and (
            not self.cursor or self.cursor[-1] == len(branch) - 1
        )

    def step_backward(self):
        """Move the cursor backwards in time

        If we are at the beginning or end then the cursor does not move.
        """
        cmd = self.get_current_command()
        if len(self.cursor) > 0:
            if self.cursor[-1] > 0:
                self.cursor[-1] -= 1
            else:
                self.cursor.pop()
        return cmd

    def step_forward(self):
        """Move the cursor forwards along the timeline of the current history branch

        If we are at a branch point then the newest branch
        (ie. the branch with the highest index) is used.
        """
        branch = self._get_branch(self.cursor)
        if isinstance(branch, list):
            if len(branch) > 0:
                self.cursor.append(len(branch) - 1)
        elif isinstance(self.cursor[-1], int) and self.cursor[-1] < len(branch) - 1:
            self.cursor[-1] += 1
        return self.get_current_command()

    def get_current_command(self):
        """Return the command pointed to by the cursor"""
        branch = self._get_branch(self.cursor)
        if isinstance(branch, list) and len(branch) > 0:
            return branch[self.cursor[-1]]
        return None

    def get_next_command(self):
        """Return the "next" command when we are not at the end of the branch"""
        branch = self._get_branch(self.cursor)
        if isinstance(branch, list) and len(branch) > 0:
            if self.cursor[-1] < len(branch) - 1:
                return branch[self.cursor[-1] + 1]
        return None

    def _get_branch(self, cursor: list[int]) -> list[Command | list]:
        """Get the current branch of the history"""
        branch: Any = self.history
        for index in cursor[:-1]:
            branch = branch[index]
        return branch

    def _end_cursor(self) -> list[int]:
        """Get the cursor at the end of the history"""
        cursor = []
        branch: Any = self.history
        while isinstance(branch, list):
            cursor.append(len(branch) - 1)
            if len(branch) == 0:
                break
            branch = branch[-1]
        return cursor


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
        return not self.cmd_graph.is_at_tail()

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
