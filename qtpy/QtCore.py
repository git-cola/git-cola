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

from qtpy import PYQT5, PYQT4, PYSIDE, PythonQtError


if PYQT5:
    from PyQt5.QtCore import *
    from PyQt5.QtCore import pyqtSignal as Signal
    from PyQt5.QtCore import pyqtSlot as Slot
    from PyQt5.QtCore import pyqtProperty as Property
    from PyQt5.QtCore import QT_VERSION_STR as __version__
elif PYQT4:
    from PyQt4.QtCore import *
    from PyQt4.QtCore import QCoreApplication
    from PyQt4.QtCore import Qt
    from PyQt4.QtCore import pyqtSignal as Signal
    from PyQt4.QtCore import pyqtSlot as Slot
    from PyQt4.QtCore import pyqtProperty as Property
    from PyQt4.QtGui import (QItemSelection, QItemSelectionModel,
                             QItemSelectionRange, QSortFilterProxyModel)
    from PyQt4.QtCore import QT_VERSION_STR as __version__
elif PYSIDE:
    from PySide.QtCore import *
    from PySide.QtGui import (QItemSelection, QItemSelectionModel,
                              QItemSelectionRange, QSortFilterProxyModel)
    import PySide.QtCore
    __version__ = PySide.QtCore.__version__
else:
    raise PythonQtError('No Qt bindings could be found')
