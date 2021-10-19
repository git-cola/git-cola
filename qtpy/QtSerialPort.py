# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © 2020 Marcin Stano
# Copyright © 2009- The Spyder Development Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
# -----------------------------------------------------------------------------
"""Provides QtSerialPort classes and functions."""

# Local imports
from . import PYQT5, PythonQtError

if PYQT5:
    from PyQt5.QtSerialPort import *
else:
    raise PythonQtError('No Qt bindings could be found')
