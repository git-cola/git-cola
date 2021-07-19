"""Base Command class"""
from __future__ import absolute_import, division, print_function, unicode_literals


class Command(object):
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

    # pylint: disable=no-self-use
    def do(self):
        """Execute the command"""
        return

    # pylint: disable=no-self-use
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
