import cola
from cola import signals


class Command(object):
    def __init__(self, model=None):
        if not model:
            model = cola.model()
        self.model = model

    def do(self):
        pass

    def is_undoable(self):
        return False

    def name(self):
        return self.__class__.__name__

    def undo(self):
        pass


class Diffstat(Command):
    def __init__(self):
        Command.__init__(self)
        self.old_text = self.model.current_text

    def do(self):
        cola.notifier().broadcast(signals.text, self.model.diffstat())

    def is_undoable(self):
        return True

    def undo(self):
        notifier().broadcast(signals.text, self.old_text)
