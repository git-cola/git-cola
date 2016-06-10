# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
# Copyright © 2009- The Spyder development Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtWebEngineWidgets classes and functions.
"""

from qtpy import API
from qtpy import PYQT5_API
from qtpy import PYQT4_API
from qtpy import PYSIDE_API
from qtpy import PythonQtError


# To test if we are using WebEngine or WebKit
WEBENGINE = True


if API in PYQT5_API:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEnginePage
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings
    except ImportError:
        from PyQt5.QtWebKitWidgets import QWebPage as QWebEnginePage
        from PyQt5.QtWebKitWidgets import QWebView as QWebEngineView
        from PyQt5.QtWebKit import QWebSettings as QWebEngineSettings
        WEBENGINE = False
elif API in PYQT4_API:
    from PyQt4.QtWebKit import QWebPage as QWebEnginePage
    from PyQt4.QtWebKit import QWebView as QWebEngineView
    from PyQt4.QtWebKit import QWebSettings as QWebEngineSettings
    WEBENGINE = False
elif API in PYSIDE_API:
    from PySide.QtWebKit import QWebPage as QWebEnginePage
    from PySide.QtWebKit import QWebView as QWebEngineView
    from PySide.QtWebKit import QWebSettings as QWebEngineSettings
    WEBENGINE = False
else:
    raise PythonQtError('No Qt bindings could be found')
