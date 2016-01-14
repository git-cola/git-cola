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

import os

from qtpy import QT_API
from qtpy import PYQT5_API
from qtpy import PYQT4_API
from qtpy import PYSIDE_API
from qtpy import PythonQtError


if os.environ[QT_API] in PYQT5_API:
    from PyQt5.QtTest import QTest
elif os.environ[QT_API] in PYQT4_API:
    from PyQt4.QtTest import QTest as OldQTest

    class QTest(OldQTest):
        @staticmethod
        def qWaitForWindowActive(QWidget):
            OldQTest.qWaitForWindowShown(QWidget)
elif os.environ[QT_API] in PYSIDE_API:
    raise ImportError('QtTest support is incomplete for PySide')
else:
    raise PythonQtError('No Qt bindings could be found')
