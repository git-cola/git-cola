# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
# Copyright © 2009- The Spyder development Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtWebkit classes and functions.
"""

import os

from qtpy import QT_API
from qtpy import PYQT5_API
from qtpy import PYQT4_API
from qtpy import PYSIDE_API
from qtpy import PythonQtError


if os.environ[QT_API] in PYQT5_API:
    try:
        from PyQt5.QtWebKitWidgets import QWebPage, QWebView
        from PyQt5.QtWebKit import QWebSettings
    except ImportError:
        from PyQt5.QtWebEngineWidgets import QWebEnginePage as QWebPage
        from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings as QWebSettings
elif os.environ[QT_API] in PYQT4_API:
    from PyQt4.QtWebKit import QWebPage, QWebView, QWebSettings
elif os.environ[QT_API] in PYSIDE_API:
    from PySide.QtWebKit import QWebPage, QWebView, QWebSettings
else:
    raise PythonQtError('No Qt bindings could be found')
