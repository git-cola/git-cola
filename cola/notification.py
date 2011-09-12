import os

from cola.compat import set
from cola.decorators import memoize


debug = os.environ.get('COLA_NOTIFIER_DEBUG', False)


@memoize
def notifier():
    return Notifier()


class Notifier(object):
    """Object for sending and receiving notification messages"""

    def __init__(self):
        self.channels = {}

    def broadcast(self, signal, *args, **opts):
        if debug:
            print ('broadcast: %s(%s, %s)' % (signal,
                                              args or '<empty>',
                                              opts or '<empty>'))
        self.emit(signal, *args, **opts)

    def emit(self, signal, *args, **opts):
        subscribers = self.channels.get(signal, None)
        if not subscribers:
            return
        for fxn in subscribers:
            fxn(*args, **opts)

    def connect(self, signal, callback):
        subscribers = self.channels.setdefault(signal, set())
        subscribers.add(callback)
