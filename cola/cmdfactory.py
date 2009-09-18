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
from cola import commands


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
        self.signal_to_command = {
            signals.diffstat: commands.Diffstat,
            signals.modified_summary: commands.Diffstat,
        }

        for signal in self.signal_to_command:
            cola.notifier().listen(signal, self.cmdrunner(signal))

        cola.notifier().listen(signals.undo, self.undo)
        cola.notifier().listen(signals.redo, self.redo)

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
