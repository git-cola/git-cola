"""Git Cola package initialization."""
from __future__ import annotations
import importlib.util
import os


def auto_select_qt_api() -> None:
    """Default to PyQt6 when QT_API is unset and PyQt6 is installed.

    QtPy defaults to PyQt5 when available, which causes regressions in modern
    desktop environments (such as KDE Plasma 6 on Wayland) where Qt5 file portal
    dialogs fail (#1625). If QT_API is not explicitly set by the user, prefer PyQt6.
    """
    if 'QT_API' not in os.environ:
        if importlib.util.find_spec('PyQt6') is not None:
            os.environ['QT_API'] = 'pyqt6'


auto_select_qt_api()
