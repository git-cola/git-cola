"""Tests for runtime appearance refresh behavior."""
import sys
from unittest.mock import MagicMock

import pytest

from cola import app as cola_app
from cola.widgets.diff import DiffSyntaxHighlighter
from qtpy import QtGui
from qtpy import QtWidgets


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


def _make_palette(*, dark: bool) -> QtGui.QPalette:
    palette = QtGui.QPalette()
    base = QtGui.QColor('#202025' if dark else '#ffffff')
    palette.setColor(QtGui.QPalette.Base, base)
    return palette


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )


def _make_context():
    context = MagicMock()
    context.cfg.color.side_effect = lambda _key, default: _hex_to_rgb(default)
    return context


def test_refresh_system_appearance_rebuilds_default_theme():
    """The default theme follows the system palette and must be rebuilt."""
    cola = cola_app.ColaApplication.__new__(cola_app.ColaApplication)
    cola.context = MagicMock()
    cola.context.cfg.get.return_value = 'default'
    cola._install_style = MagicMock()

    cola._refresh_system_appearance()

    cola._install_style.assert_called_once_with(None)


def test_refresh_system_appearance_skips_non_default_theme():
    """User-selected themes replace the palette and must not be overridden."""
    cola = cola_app.ColaApplication.__new__(cola_app.ColaApplication)
    cola.context = MagicMock()
    cola.context.cfg.get.return_value = 'flat-dark-blue'
    cola._install_style = MagicMock()

    cola._refresh_system_appearance()

    cola._install_style.assert_not_called()


def test_diff_syntax_highlighter_uses_light_palette_defaults(qapp):
    context = _make_context()
    doc = QtGui.QTextDocument()
    highlighter = DiffSyntaxHighlighter(context, doc)

    highlighter._configure_colors(context, _make_palette(dark=False))

    assert highlighter.color_add.red() == 0xD2
    assert highlighter.color_add.green() == 0xFF
    assert highlighter.color_add.blue() == 0xE4
    assert highlighter.color_remove.red() == 0xFE
    assert highlighter.color_remove.green() == 0xE0
    assert highlighter.color_remove.blue() == 0xE4


def test_diff_syntax_highlighter_uses_dark_palette_defaults(qapp):
    context = _make_context()
    doc = QtGui.QTextDocument()
    highlighter = DiffSyntaxHighlighter(context, doc)

    highlighter._configure_colors(context, _make_palette(dark=True))

    assert highlighter.color_add.red() == 0x77
    assert highlighter.color_add.green() == 0xAA
    assert highlighter.color_add.blue() == 0x77
    assert highlighter.color_remove.red() == 0xAA
    assert highlighter.color_remove.green() == 0x77
    assert highlighter.color_remove.blue() == 0x77


def test_diff_syntax_highlighter_refresh_palette_rehighlights(qapp):
    context = _make_context()
    doc = QtGui.QTextDocument()
    highlighter = DiffSyntaxHighlighter(context, doc)
    highlighter.rehighlight = MagicMock()

    highlighter.refresh_palette(context)

    highlighter.rehighlight.assert_called_once()
