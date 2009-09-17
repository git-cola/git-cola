from PyQt4 import QtCore

from cola import signals

_instance = None
def notifier():
    global _instance
    if _instance:
        return _instance
    _instance = QNotifier()
    return _instance


class QNotifier(QtCore.QObject):
    def broadcast(self, signal, *args, **kwargs):
        print ('broadcast: %s(%s, %s)' %
                (signals.name(signal), args or '<empty>', kwargs or '<empty>'))
        self.emit(signal, *args, **kwargs)
