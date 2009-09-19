import os

import cola
from cola import signals
from cola import cmdfactory


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


class Diff(Command):
    """Perform a diff and set the model's current text."""
    def __init__(self, filenames):
        Command.__init__(self)
        self.filenames = filenames 
        self.old_mode = self.model.mode
        self.old_text = self.model.current_text

    def do(self):
        if not self.filenames:
            print 'no filenames:', self.filenames
            return
        self.model.set_mode(self.model.mode_worktree)
        filename = self.filenames[0]
        diff = self.model.diff_helper(filename=filename,
                                      ref=self.model.head,
                                      cached=False)
        self.model.set_current_text(diff)

    def undo(self):
        self.model.set_mode(self.old_mode)
        self.model.set_current_text(self.old_text)

    def is_undoable(self):
        return True


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


class ResetMode(Command):
    def __init__(self, model=None):
        Command.__init__(self, model=model)
        self.old_mode = self.model.mode
        self.old_text = self.model.current_text

    def do(self):
        self.model.set_mode(self.model.mode_none)
        self.model.set_current_text('')

    def undo(self):
        self.model.set_mode(self.old_mode)
        self.model.set_current_text(self.old_text)

    def is_undoable(self):
        return True

def register():
    """
    Register signal mappings with the factory.

    These commands are automatically created and run when
    their corresponding signal is broadcast by the notifier.

    """
    signal_to_command_map = {
        signals.diff: Diff,
        signals.diffstat: Diffstat,
        signals.modified_summary: Diffstat,
        signals.reset_mode: ResetMode,
    }

    factory = cmdfactory.factory()
    for signal, cmd in signal_to_command_map.iteritems():
        factory.add_command(signal, cmd)
