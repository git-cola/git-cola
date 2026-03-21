"""Base Command class"""

from __future__ import annotations

import time
from typing import Any
from typing import TYPE_CHECKING

from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

if TYPE_CHECKING:
    from .app import ApplicationContext


class Command:
    """Mixin interface for commands"""

    UNDOABLE = False

    def __init__(self) -> None:
        """Initialize the base command"""
        self.can_undo = False

    @staticmethod
    def name() -> str:
        """Return the command's name"""
        return '(undefined)'

    @classmethod
    def is_undoable(cls) -> bool:
        """Can this be undone?"""
        return cls.UNDOABLE

    def do(self) -> Any:
        """Execute the command"""
        self.can_undo = True
        return True

    def undo(self) -> bool:
        """Undo the command"""
        return self.can_undo


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

    def do(self) -> Any:
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

    def undo(self) -> None:
        super().undo()
        self.context.timestamp = self.old_timestamp


class CommandBus(QtCore.QObject):
    do_command = Signal(object)
    undo_command = Signal(object)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)

        self.do_command.connect(lambda cmd: cmd.do(), type=Qt.QueuedConnection)
        self.undo_command.connect(lambda cmd: cmd.undo(), type=Qt.QueuedConnection)

    def do(self, cmd: str) -> None:
        """Run a command on the main thread"""
        self.do_command.emit(cmd)

    def undo(self, cmd: str) -> None:
        """Undo a command on the main thread"""
        self.undo_command.emit(cmd)
