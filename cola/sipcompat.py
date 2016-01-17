from __future__ import absolute_import, division, unicode_literals

import sip


class _PyQtSipApi(object):

    def __init__(self):
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        sip.setapi('QDate', 2)
        sip.setapi('QDateTime', 2)
        sip.setapi('QString', 2)
        sip.setapi('QTextStream', 2)
        sip.setapi('QTime', 2)
        sip.setapi('QUrl', 2)
        sip.setapi('QVariant', 2)

        self._initialized = True

# It's a global, but in this case the API compat level truly
# is a global that can only be set once before PyQt4 is imported.
_pyqt_api = _PyQtSipApi()


def initialize():
    _pyqt_api.initialize()
