"""
Maps Qt signals to Command objects.

The command factory listens to the global notifier and
creates commands objects as registered signals are
encountered.

The factory itself is undoable in that it responds to
the undo and redo signals and manages the undo/redo stack.

"""

import cola
from cola import qtutils
from cola import signals


_factory = None
def factory():
    global _factory
    if _factory:
        return _factory
    _factory = CommandFactory()
    return _factory


class CommandFactory(object):
    def __init__(self):
        self.undostack = []
        self.redostack = []
        self.signal_to_command = {}

        cola.notifier().listen(signals.undo, self.undo)
        cola.notifier().listen(signals.redo, self.redo)
        cola.notifier().listen(signals.information, qtutils.information)

        self.model = cola.model()
        self.model.add_observer(self)

    def add_command(self, signal, command):
        """Register a signal/command pair."""
        self.signal_to_command[signal] = command
        cola.notifier().listen(signal, self.cmdrunner(signal))

    def notify(self, *params):
        """
        Observe model changes to current_text.

        'current_text' is the model param that maps to the diff disply,
        so broadcast notifier messages whenever it changes.

        """
        actions = {
        'current_text':
            lambda: cola.notifier()
                        .broadcast(signals.text, self.model.current_text),
        }
        for param in params:
            action = actions.get(param, lambda: None)
            action()

    def clear(self):
        self.undostack = []
        self.redostack = []

    def cmdrunner(self, signal):
        def run(*args, **opts):
            return self.do(signal, *args, **opts)
        return run

    def do(self, signal, *args, **opts):
        cmdclass = self.signal_to_command[signal]
        cmdobj = cmdclass(*args, **opts)
        if cmdobj.is_undoable():
            self.undostack.append(cmdobj)
        return cmdobj.do()

    def undo(self):
        if self.undostack:
            cmdobj = self.undostack.pop()
            cmdobj.undo()
            self.redostack.append(cmdobj)
        else:
            print 'warning: undo stack is empty, doing nothing'

    def redo(self):
        if self.redostack:
            cmdobj = self.redostack.pop()
            cmdobj.do()
            self.undo.append(cmd)
        else:
            print 'warning: redo stack is empty, doing nothing'

    def is_undoable(self):
        return bool(self.undostack)

    def is_redoable(self):
        return bool(self.redostack)
