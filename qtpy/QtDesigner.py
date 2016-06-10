# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtDesigner classes and functions.
"""

from qtpy import API
from qtpy import PYQT5_API
from qtpy import PYQT4_API
from qtpy import PythonQtError


if API in PYQT5_API:
    from PyQt5.QtDesigner import *
elif API in PYQT4_API:
    from PyQt4.QtDesigner import *
else:
    raise PythonQtError('No Qt bindings could be found')
