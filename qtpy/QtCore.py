# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
# Copyright © 2009- The Spyder Development Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtCore classes and functions.
"""

import os

from qtpy import QT_API
from qtpy import PYQT5_API
from qtpy import PYQT4_API
from qtpy import PYSIDE_API
from qtpy import PythonQtError


if os.environ[QT_API] in PYQT5_API:
    from PyQt5.QtCore import *
    from PyQt5.QtCore import pyqtSignal as Signal
    from PyQt5.QtCore import pyqtSlot as Slot
    from PyQt5.QtCore import pyqtProperty as Property
    from PyQt5.QtCore import QT_VERSION_STR as __version__
elif os.environ[QT_API] in PYQT4_API:
    from PyQt4.QtCore import *
    from PyQt4.QtCore import QCoreApplication
    from PyQt4.QtCore import Qt
    from PyQt4.QtCore import pyqtSignal as Signal
    from PyQt4.QtCore import pyqtSlot as Slot
    from PyQt4.QtCore import pyqtProperty as Property
    from PyQt4.QtGui import (QItemSelection, QItemSelectionRange,
                             QSortFilterProxyModel)
    from PyQt4.QtCore import QT_VERSION_STR as __version__
elif os.environ[QT_API] in PYSIDE_API:
    from PySide.QtCore import *
    from PySide.QtGui import (QItemSelection, QItemSelectionRange,
                              QSortFilterProxyModel)
    import PySide.QtCore
    __version__ = PySide.QtCore.__version__
else:
    raise PythonQtError('No Qt bindings could be found')
