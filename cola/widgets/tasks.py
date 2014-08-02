from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola import cmds


class TaskRunner(QtCore.QObject):
    """Runs QRunnable instances and transfers control when they finish"""

    def __init__(self, parent):
        QtCore.QObject.__init__(self, parent)
        self.tasks = []
        self.task_callbacks = {}
        self.connect(self, Task.FINISHED, self.finish)

    def start(self, task, callback):
        """Start the task and register a callback"""
        self.tasks.append(task)
        if callback is not None:
            task_id = id(task)
            self.task_callbacks[task_id] = callback
        QtCore.QThreadPool.globalInstance().start(task)

    def finish(self, task, *args, **kwargs):
        task_id = id(task)
        try:
            self.tasks.remove(task)
        except:
            pass
        try:
            callback = self.task_callbacks[task_id]
            del self.task_callbacks[task_id]
        except KeyError:
            return
        callback(task, *args, **kwargs)


class Task(QtCore.QRunnable):
    """Base class for concrete tasks"""

    FINISHED = SIGNAL('finished')

    def __init__(self, sender):
        QtCore.QRunnable.__init__(self)
        self.sender = sender

    def finish(self, *args, **kwargs):
        self.sender.emit(self.FINISHED, self, *args, **kwargs)


class CloneTask(Task):
    """Clones a Git repository"""

    def __init__(self, sender, url, destdir, spawn):
        Task.__init__(self, sender)
        self.url = url
        self.destdir = destdir
        self.spawn = spawn
        self.cmd = None

    def run(self):
        """Runs the model action and captures the result"""
        self.cmd = cmds.do(cmds.Clone, self.url, self.destdir,
                           spawn=self.spawn)
        self.finish()
