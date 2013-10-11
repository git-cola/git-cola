class BaseCommand(object):
    """Base class for all commands; provides the command pattern"""

    DISABLED = False

    def __init__(self):
        self.undoable = False

    def is_undoable(self):
        """Can this be undone?"""
        return self.undoable

    @staticmethod
    def name(cls):
        return 'Unknown'

    def do(self):
        raise NotImplementedError('%s.do() is unimplemented' % self.__class__.__name__)

    def undo(self):
        raise NotImplementedError('%s.undo() is unimplemented' % self.__class__.__name__)
