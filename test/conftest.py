"""Pytest configuration for Qt-based tests."""

import os


# Use an offscreen Qt backend in CI and headless local sessions.
# This prevents QApplication from aborting when the display server is unavailable
# or the active platform plugin is unstable.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
