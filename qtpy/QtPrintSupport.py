# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtPrintSupport classes and functions.
"""

from qtpy import API
from qtpy import PYQT5_API
from qtpy import PYQT4_API
from qtpy import PYSIDE_API
from qtpy import PythonQtError


if API in PYQT5_API:
    from PyQt5.QtPrintSupport import *
elif API in PYQT4_API:
    from PyQt4.QtGui import (QAbstractPrintDialog, QPageSetupDialog,
                             QPrintDialog, QPrintEngine, QPrintPreviewDialog,
                             QPrintPreviewWidget, QPrinter, QPrinterInfo)
elif API in PYSIDE_API:
    from PySide.QtGui import (QAbstractPrintDialog, QPageSetupDialog,
                              QPrintDialog, QPrintEngine, QPrintPreviewDialog,
                              QPrintPreviewWidget, QPrinter, QPrinterInfo)
else:
    raise PythonQtError('No Qt bindings could be found')
