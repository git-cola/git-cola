"""
Maps Qt signals to Command objects.

The command factory connects to the global notifier and
creates commands objects as registered signals are
encountered.

The factory itself is undoable in that it responds to
the undo and redo signals and manages the undo/redo stack.

"""
import cola
from cola import signals
from cola import errors
from cola.decorators import memoize


@memoize
def factory():
    """Return a static instance of the command factory."""
    return CommandFactory()


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
        self.undoable = True
        self.undostack = []
        self.redostack = []
        self.signal_to_command = {}
        self.callbacks = {}

        cola.notifier().connect(signals.undo, self.undo)
        cola.notifier().connect(signals.redo, self.redo)

        self.model = cola.model()
        self.model.add_observer(self)

    def add_command(self, signal, command):
        """Register a signal/command pair."""
        self.signal_to_command[signal] = command
        cola.notifier().connect(signal, self.cmdrunner(signal))

    def add_command_wrapper(self, cmd_wrapper):
        self.callbacks.update(cmd_wrapper.callbacks)

    def prompt_user(self, name, *args, **opts):
        try:
            return self.callbacks[name](*args, **opts)
        except KeyError:
            raise NotImplementedError('No callback for "%s' % name)

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
        # TODO we disable undo/redo for now; views just need to
        # inspect the stack and add menu entries when we enable it.
        ok, result = self._do(cmdobj)
        if ok and self.undoable and cmdobj.is_undoable():
            self.undostack.append(cmdobj)
        return result

    def _do(self, cmdobj):
        try:
            result = cmdobj.do()
        except errors.UsageError, e:
            self.prompt_user(signals.information, e.title, e.message)
            return False, None
        else:
            return True, result

    def undo(self):
        """Undo the last command and add it to the redo stack."""
        if self.undostack:
            cmdobj = self.undostack.pop()
            result = cmdobj.undo()
            self.redostack.append(cmdobj)
            return result
        else:
            print 'warning: undo stack is empty, doing nothing'
            return None

    def redo(self):
        """Redo the last command and add it to the undo stack."""
        if self.redostack:
            cmdobj = self.redostack.pop()
            ok, result = self._do(cmdobj)
            if ok and cmdobj.is_undoable():
                self.undo.append(cmdobj)
            else:
                self.redostack.push(cmdobj)
            return result
        else:
            print 'warning: redo stack is empty, doing nothing'

    def is_undoable(self):
        """Does the undo stack contain any commands?"""
        return bool(self.undostack)

    def is_redoable(self):
        """Does the redo stack contain any commands?"""
        return bool(self.redostack)
