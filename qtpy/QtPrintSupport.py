# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtPrintSupport classes and functions.
"""

from qtpy import PYQT5
from qtpy import PYQT4
from qtpy import PYSIDE
from qtpy import PythonQtError


if PYQT5:
    from PyQt5.QtPrintSupport import *
elif PYQT4:
    from PyQt4.QtGui import (QAbstractPrintDialog, QPageSetupDialog,
                             QPrintDialog, QPrintEngine, QPrintPreviewDialog,
                             QPrintPreviewWidget, QPrinter, QPrinterInfo)
elif PYSIDE:
    from PySide.QtGui import (QAbstractPrintDialog, QPageSetupDialog,
                              QPrintDialog, QPrintEngine, QPrintPreviewDialog,
                              QPrintPreviewWidget, QPrinter, QPrinterInfo)
else:
    raise PythonQtError('No Qt bindings could be found')
