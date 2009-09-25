"""
Maps Qt signals to Command objects.

The command factory listens to the global notifier and
creates commands objects as registered signals are
encountered.

The factory itself is undoable in that it responds to
the undo and redo signals and manages the undo/redo stack.

"""
import cola
from cola import signals


_factory = None
def factory():
    """Return a static instance of the command factory."""
    global _factory
    if _factory:
        return _factory
    _factory = CommandFactory()
    return _factory


def SLOT(signal, *args, **opts):
    """
    Returns a callback that broadcasts a message over the notifier.
    
    """
    def broadcast(*local_args, **opts):
        cola.notifier().broadcast(signal, *args, **opts)
    return broadcast


class CommandFactory(object):
    def __init__(self):
        """Setup the undo/redo stacks and register for notifications."""
        self.undostack = []
        self.redostack = []
        self.signal_to_command = {}

        cola.notifier().listen(signals.undo, self.undo)
        cola.notifier().listen(signals.redo, self.redo)

        self.model = cola.model()
        self.model.add_observer(self)

    def add_command(self, signal, command):
        """Register a signal/command pair."""
        self.signal_to_command[signal] = command
        cola.notifier().listen(signal, self.cmdrunner(signal))

    def notify(self, *params):
        """
        Observe model changes.

        This captures model parameters and maps them to signals that
        are observed by the UIs.

        """
        actions = {
            'diff_text': SLOT(signals.diff_text, self.model.diff_text),
            'commitmsg': SLOT(signals.editor_text, self.model.commitmsg),
            'mode': SLOT(signals.mode, self.model.mode),
        }
        for param in params:
            action = actions.get(param, lambda: None)
            action()

    def clear(self):
        """Clear the undo and redo stacks."""
        self.undostack = []
        self.redostack = []

    def cmdrunner(self, signal):
        """Return a function to create and run a signal's command."""
        def run(*args, **opts):
            return self.do(signal, *args, **opts)
        return run

    def do(self, signal, *args, **opts):
        """Given a signal and arguments, run its corresponding command."""
        cmdclass = self.signal_to_command[signal]
        cmdobj = cmdclass(*args, **opts)
        if cmdobj.is_undoable():
            self.undostack.append(cmdobj)
        return cmdobj.do()

    def undo(self):
        """Undo the last command and add it to the redo stack."""
        if self.undostack:
            cmdobj = self.undostack.pop()
            cmdobj.undo()
            self.redostack.append(cmdobj)
        else:
            print 'warning: undo stack is empty, doing nothing'

    def redo(self):
        """Redo the last command and add it to the undo stack."""
        if self.redostack:
            cmdobj = self.redostack.pop()
            cmdobj.do()
            self.undo.append(cmd)
        else:
            print 'warning: redo stack is empty, doing nothing'

    def is_undoable(self):
        """Does the undo stack contain any commands?"""
        return bool(self.undostack)

    def is_redoable(self):
        """Does the redo stack contain any commands?"""
        return bool(self.redostack)
