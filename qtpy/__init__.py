# -*- coding: utf-8 -*-
"""
**QtPyqt** is a shim over the various qt bindings. It is used to write
qt bindings indenpendent library or application.

The shim will automatically select the first available API (PyQt5, PyQt4 and
finally PySide).

You can force the use of one specific bindings (e.g. if your application is
using one specific bindings and you need to use library that use pyqode.qt) by
setting up the `QT_API` environment variable.

PyQt5
=====

For pyqt5, you don't have to set anything as it will be used automatically::
    >>> from qtpy import QtGui, QtWidgets, QtCore
    >>> print(QtWidgets.QWidget)

"""


import os

__version__ = '1.0.1'


os.environ.setdefault('QT_API', 'pyqt')
assert os.environ['QT_API'] in ('pyqt5', 'pyqt', 'pyside')

API = os.environ['QT_API']
API_NAME = {'pyqt5': 'PyQt5', 'pyqt': 'PyQt4', 'pyside': 'PySide'}[API]

PYQT5 = False

if API == 'pyqt5':
    try:
        from PyQt5.QtCore import PYQT_VERSION_STR as __version__
        is_old_pyqt = False
        is_pyqt46 = False
        PYQT5 = True
    except ImportError:
        pass
elif API == 'pyqt':
    # QtPy 1.0 is compatible with both #1 and #2 PyQt API,
    # but to avoid issues with IPython and other Qt plugins
    # we choose to support only API #2
    import sip
    try:
        sip.setapi('QString', 2)
        sip.setapi('QVariant', 2)
    except AttributeError:
        # PyQt < v4.6. The actual check is done by requirements.check_qt()
        # call from spyder.py
        pass

    try:
        from PyQt4.QtCore import PYQT_VERSION_STR as __version__ # analysis:ignore
    except ImportError:
        # Switching to PySide
        API = os.environ['QT_API'] = 'pyside'
        API_NAME = 'PySide'
    else:
        is_old_pyqt = __version__.startswith(('4.4', '4.5', '4.6', '4.7'))
        is_pyqt46 = __version__.startswith('4.6')
        import sip
        try:
            API_NAME += (" (API v%d)" % sip.getapi('QString'))
        except AttributeError:
            pass


if API == 'pyside':
    try:
        from PySide import __version__  # analysis:ignore
    except ImportError:
        raise ImportError("QtPy requires PySide or PyQt to be installed")
    else:
        is_old_pyqt = is_pyqt46 = False

