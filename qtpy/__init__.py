# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
**QtPy** is a shim over the various qt bindings. It is used to write
qt bindings indenpendent library or application.

The shim will automatically select the first available API (PyQt5, PyQt4 and
finally PySide).

You can force the use of one specific bindings (e.g. if your application is
using one specific bindings and you need to use library that use QtPy) by
setting up the ``QT_API`` environment variable.

PyQt5
=====

For pyqt5, you don't have to set anything as it will be used automatically::

    >>> from pyqode.qt import QtGui, QtWidgets, QtCore
    >>> print(QtWidgets.QWidget)


PyQt4
=====

Set the ``QT_API`` environment variable to 'PyQt4' (case insensitive) before
importing any python package::

    >>> import os
    >>> os.environ['QT_API'] = 'PyQt4'
    >>> from pyqode.qt import QtGui, QtWidgets, QtCore
    >>> print(QtWidgets.QWidget)


.. warning:: This requires to set the SIP api to version 2 (for strings and
    covariants). If you're using python2 you have to make sure the correct sip
    api is set before importing any PyQt4 module (pyqode.qt can take care of
    that for you but it must be imported before any PyQt4 module).


PySide
======

Set the QT_API environment variable to 'PySide' (case insensitive) before
importing pyqode::

    >>> import os
    >>> os.environ['QT_API'] = 'PySide'
    >>> from pyqode.qt import QtGui, QtWidgets, QtCore
    >>> print(QtWidgets.QWidget)

"""

import os
import sys
import logging

__version__ = '0.1.2'

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


class PythonQtError(Exception):

    """
    Error raise if no bindings could be selected
    """
    pass


def setup_apiv2():
    """
    Setup apiv2 when using PyQt4 and Python2.
    """
    # setup PyQt api to version 2
    if sys.version_info[0] == 2:
        logging.getLogger(__name__).debug(
            'setting up SIP API to version 2')
        import sip
        try:
            sip.setapi("QString", 2)
            sip.setapi("QVariant", 2)
        except ValueError:
            logging.getLogger(__name__).critical(
                "failed to set up sip api to version 2 for PyQt4")
            raise ImportError('PyQt4')


def autodetect():
    """
    Auto-detects and use the first available QT_API by importing them in the
    following order:

    1) PyQt5
    2) PyQt4
    3) PySide
    """
    logging.getLogger(__name__).debug('auto-detecting QT_API')
    try:
        logging.getLogger(__name__).debug('trying PyQt5')
        import PyQt5
        os.environ[QT_API] = PYQT5_API[0]
        logging.getLogger(__name__).debug('imported PyQt5')
    except ImportError:
        try:
            logging.getLogger(__name__).debug('trying PyQt4')
            setup_apiv2()
            import PyQt4
            os.environ[QT_API] = PYQT4_API[0]
            logging.getLogger(__name__).debug('imported PyQt4')
        except ImportError:
            try:
                logging.getLogger(__name__).debug('trying PySide')
                import PySide
                os.environ[QT_API] = PYSIDE_API[0]
                logging.getLogger(__name__).debug('imported PySide')
            except ImportError:
                raise PythonQtError('No Qt bindings could be found')


if QT_API in os.environ:
    # check if the selected QT_API is available
    try:
        if os.environ[QT_API].lower() in PYQT5_API:
            logging.getLogger(__name__).debug('importing PyQt5')
            import PyQt5
            os.environ[QT_API] = PYQT5_API[0]
            logging.getLogger(__name__).debug('imported PyQt5')
        elif os.environ[QT_API].lower() in PYQT4_API:
            logging.getLogger(__name__).debug('importing PyQt4')
            setup_apiv2()
            import PyQt4
            os.environ[QT_API] = PYQT4_API[0]
            logging.getLogger(__name__).debug('imported PyQt4')
        elif os.environ[QT_API].lower() in PYSIDE_API:
            logging.getLogger(__name__).debug('importing PySide')
            import PySide
            os.environ[QT_API] = PYSIDE_API[0]
            logging.getLogger(__name__).debug('imported PySide')
    except ImportError:
        logging.getLogger(__name__).warning(
            'failed to import the selected QT_API: %s',
            os.environ[QT_API])
        # use the auto-detected API if possible
        autodetect()
else:
    # user did not select a qt api, let's perform auto-detection
    autodetect()


logging.getLogger(__name__).info('using %s' % os.environ[QT_API])

