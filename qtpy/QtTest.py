# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
# Copyright © 2009- The Spyder Developmet Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtTest and functions
.. warning:: PySide is not supported here, that's why there is not unit tests
    running with PySide.
"""

from qtpy import PYQT5, PYQT4, PYSIDE, PythonQtError


if PYQT5:
    from PyQt5.QtTest import QTest
elif PYQT4:
    from PyQt4.QtTest import QTest as OldQTest

    class QTest(OldQTest):
        @staticmethod
        def qWaitForWindowActive(QWidget):
            OldQTest.qWaitForWindowShown(QWidget)
elif PYSIDE:
    raise ImportError('QtTest support is incomplete for PySide')
else:
    raise PythonQtError('No Qt bindings could be found')
