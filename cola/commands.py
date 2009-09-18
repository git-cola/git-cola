import cola
from cola import signals


class Command(object):
    """Base class for all commands; provides the command pattern."""
    def __init__(self, model=None):
        """Initialize the command and stash away values for use in do()"""
        if not model:
            model = cola.model()
        self.model = model

    def do(self):
        """Perform the operation."""
        pass

    def is_undoable(self):
        """Can this be undone?"""
        return False

    def undo(self):
        """Undo the operation."""
        pass

    def name(self):
        """Return this command's name."""
        return self.__class__.__name__

    def undo(self):
        pass


class Diffstat(Command):
    """Perform a diffstat and set the model's current text."""
    def __init__(self):
        Command.__init__(self)
        self.old_text = self.model.current_text

    def do(self):
        self.model.set_current_text(self.model.diffstat())

    def undo(self):
        self.model.set_current_text(self.old_text)

    def is_undoable(self):
        return True

    def undo(self):
        notifier().broadcast(signals.text, self.old_text)
