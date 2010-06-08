import os
from PyQt4 import QtCore

from cola.compat import set
from cola.decorators import memoize


debug = os.environ.get('COLA_NOTIFIER_DEBUG', False)


@memoize
def notifier():
    return Notifier()


class Notifier(object):
    """A pure-python re-implementation of QObject."""
    def __init__(self):
        self.channels = {}

    def broadcast(self, signal, *args, **opts):
        if debug:
            print ('broadcast: %s(%s, %s)' % (name,
                                              args or '<empty>',
                                              kwargs or '<empty>'))
        self.emit(signal, *args, **opts)

    def emit(self, signal, *args, **opts):
        subscribers = self.channels.get(signal, None)
        if subscribers:
            for fxn in subscribers:
                fxn(*args, **opts)

    def connect(self, signal, callback):
        subscribers = self.channels.setdefault(signal, set())
        subscribers.add(callback)
