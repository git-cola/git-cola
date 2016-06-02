# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Copyright © 2014-2015 Colin Duquesnoy
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
**QtPy** is a shim over the various Python Qt bindings. It is used to write
Qt binding indenpendent libraries or applications.

The shim will automatically select the first available API (PyQt5, PyQt4 and
finally PySide).

You can force the use of one specific bindings (e.g. if your application is
using one specific bindings and you need to use library that use QtPy) by
setting up the ``QT_API`` environment variable.

PyQt5
=====

For PyQt5, you don't have to set anything as it will be used automatically::

    >>> from qtpy import QtGui, QtWidgets, QtCore
    >>> print(QtWidgets.QWidget)


PyQt4
=====

Set the ``QT_API`` environment variable to 'pyqt' before importing any python
package::

    >>> import os
    >>> os.environ['QT_API'] = 'pyqt'
    >>> from qtpy import QtGui, QtWidgets, QtCore
    >>> print(QtWidgets.QWidget)

PySide
======

Set the QT_API environment variable to 'pyside' before importing other
packages::

    >>> import os
    >>> os.environ['QT_API'] = 'pyside'
    >>> from qtpy import QtGui, QtWidgets, QtCore
    >>> print(QtWidgets.QWidget)

"""

import os

#: Qt API environment variable name
QT_API = 'QT_API'
#: names of the expected PyQt5 api
PYQT5_API = ['pyqt5']
#: names of the expected PyQt4 api
PYQT4_API = [
    'pyqt',  # name used in IPython.qt
    'pyqt4'  # pyqode.qt original name
]
#: names of the expected PySide api
PYSIDE_API = ['pyside']

os.environ.setdefault(QT_API, 'pyqt5')
assert os.environ[QT_API] in (PYQT5_API + PYQT4_API + PYSIDE_API)

API = os.environ[QT_API]
API_NAME = {'pyqt5': 'PyQt5', 'pyqt': 'PyQt4', 'pyqt4': 'PyQt4',
            'pyside': 'PySide'}[API]

is_old_pyqt = is_pyqt46 = False
PYQT5 = True
PYQT4 = PYSIDE = False


class PythonQtError(Exception):
    """Error raise if no bindings could be selected"""
    pass


if API in PYQT5_API:
    try:
        from PyQt5.QtCore import PYQT_VERSION_STR as __version__
        from PyQt5 import uic                                     # analysis:ignore
    except ImportError:
        API = os.environ['QT_API'] = 'pyqt'
        API_NAME = 'PyQt4'

if API in PYQT4_API:
    try:
        import sip
        try:
            sip.setapi('QString', 2)
            sip.setapi('QVariant', 2)
            sip.setapi('QDate', 2)
            sip.setapi('QDateTime', 2)
            sip.setapi('QTextStream', 2)
            sip.setapi('QTime', 2)
            sip.setapi('QUrl', 2)
        except AttributeError:
            # PyQt < v4.6
            pass

        from PyQt4.QtCore import PYQT_VERSION_STR as __version__  # analysis:ignore
        from PyQt4 import uic                                     # analysis:ignore
        PYQT5 = False
        PYQT4 = True
    except ImportError:
        API = os.environ['QT_API'] = 'pyside'
        API_NAME = 'PySide'
    else:
        is_old_pyqt = __version__.startswith(('4.4', '4.5', '4.6', '4.7'))
        is_pyqt46 = __version__.startswith('4.6')
        import sip
        try:
            API_NAME += (" (API v{0})".format(sip.getapi('QString')))
        except AttributeError:
            pass

if API in PYSIDE_API:
    try:
        from PySide import __version__                            # analysis:ignore
        PYQT5 = False
        PYSIDE = True
    except ImportError:
        raise PythonQtError('No Qt bindings could be found')
