# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2020 Antonio Valentino
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
# -----------------------------------------------------------------------------
"""Provides QtPositioning classes and functions."""

# Local imports
from . import PYQT5, PYSIDE2, PythonQtError

if PYQT5:
    from PyQt5.QtPositioning import *
elif PYSIDE2:
    from PySide2.QtPositioning import *
else:
    raise PythonQtError('No Qt bindings could be found')
