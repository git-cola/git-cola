import os
from PyQt4 import QtCore

from cola.compat import set

debug = os.environ.get('COLA_NOTIFIER_DEBUG', False)
_instance = None
def notifier():
    global _instance
    if _instance:
        return _instance
    _instance = Notifier()
    return _instance


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
