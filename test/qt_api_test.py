from __future__ import annotations
import importlib.machinery
import os
from unittest.mock import patch

from cola import auto_select_qt_api


def test_auto_select_qt_api_prefers_pyqt6(monkeypatch):
    monkeypatch.delenv('QT_API', raising=False)
    fake_spec = importlib.machinery.ModuleSpec('PyQt6', None)
    with patch('importlib.util.find_spec', return_value=fake_spec):
        auto_select_qt_api()
    assert os.environ.get('QT_API') == 'pyqt6'


def test_auto_select_qt_api_preserves_explicit_qt_api(monkeypatch):
    monkeypatch.setenv('QT_API', 'pyqt5')
    fake_spec = importlib.machinery.ModuleSpec('PyQt6', None)
    with patch('importlib.util.find_spec', return_value=fake_spec):
        auto_select_qt_api()
    assert os.environ.get('QT_API') == 'pyqt5'


def test_auto_select_qt_api_noop_when_pyqt6_missing(monkeypatch):
    monkeypatch.delenv('QT_API', raising=False)
    with patch('importlib.util.find_spec', return_value=None):
        auto_select_qt_api()
    assert 'QT_API' not in os.environ
