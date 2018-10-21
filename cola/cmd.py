"""Base Command class"""
from __future__ import division, absolute_import, unicode_literals


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

    def do(self):
        """Execute the command"""
        pass

    def undo(self):
        """Undo the command"""
        pass


class ContextCommand(Command):
    """Base class for commands that operate on a context"""

    def __init__(self, context):
        self.context = context
        self.model = context.model
        self.cfg = context.cfg
        self.git = context.git
        self.selection = context.selection
        self.fsmonitor = context.fsmonitor
