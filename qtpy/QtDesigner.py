# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtDesigner classes and functions.
"""

import os
from pyqode.qt import QT_API
from pyqode.qt import PYQT5_API
from pyqode.qt import PYQT4_API


if os.environ[QT_API] in PYQT5_API:
    from PyQt5.QtDesigner import *                            # analysis:ignore
elif os.environ[QT_API] in PYQT4_API:
    from PyQt4.QtDesigner import *                            # analysis:ignore
# TODO:

