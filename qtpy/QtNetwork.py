# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
# Copyright © 2011 Pierre Raybaut
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtNetwork classes and functions.
"""
import os
from pyqode.qt import QT_API
from pyqode.qt import PYQT5_API
from pyqode.qt import PYQT4_API
from pyqode.qt import PYSIDE_API

if os.environ[QT_API] in PYQT5_API:
    from PyQt5.QtNetwork import *                             # analysis:ignore
elif os.environ[QT_API] in PYQT4_API:
    from PyQt4.QtNetwork import *                             # analysis:ignore
elif os.environ[QT_API] in PYSIDE_API:
    from PySide.QtNetwork import *                            # analysis:ignore
else:
    # Raise error

