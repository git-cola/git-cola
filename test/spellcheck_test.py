import sys
from unittest.mock import MagicMock

import pytest

from cola import compat
from cola import qtutils
from cola import spellcheck
from cola.widgets.spellcheck import SpellCheckLineEdit
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import QEvent
from qtpy.QtCore import Qt

from . import helper


def test_spellcheck_generator():
    check = spellcheck.NorvigSpellCheck()
    assert_spellcheck(check)


def test_spellcheck_unicode():
    path = helper.fixture('unicode.txt')
    check = spellcheck.NorvigSpellCheck(words=path)
    assert_spellcheck(check)


def assert_spellcheck(check):
    for word in check.read():
        assert word is not None
        assert isinstance(word, compat.ustr)


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for the widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


def _make_line_edit(text):
    """Build a SpellCheckLineEdit pre-filled with text and the cursor at start"""
    context = MagicMock()
    # diff_font() reads this to construct the widget's font.
    context.cfg.get.return_value = qtutils.default_monospace_font().toString()
    widget = SpellCheckLineEdit(context, 'hint', check=MagicMock())
    widget.setPlainText(text)
    _move_cursor_to_start(widget)
    return widget


def _move_cursor_to_start(widget):
    cursor = widget.textCursor()
    cursor.movePosition(QtGui.QTextCursor.Start)
    widget.setTextCursor(cursor)


def _send_focus_in(widget, reason):
    widget.focusInEvent(QtGui.QFocusEvent(QEvent.FocusIn, reason))


def test_focus_in_other_reason_moves_cursor_to_end(qapp):
    """Programmatic setFocus() (Ctrl+L) moves the cursor to the end of the line.

    Regression test: the very first programmatic focus used to leave the cursor
    at the start of the line because the cursor was only moved to the end on
    focus-out. OtherFocusReason now moves it to the end on the way in.
    """
    text = 'hello world'
    widget = _make_line_edit(text)
    assert widget.textCursor().position() == 0

    _send_focus_in(widget, Qt.OtherFocusReason)

    assert widget.textCursor().position() == len(text)
    assert not widget.textCursor().hasSelection()


def test_focus_in_other_reason_with_empty_text_is_a_noop(qapp):
    """An empty line stays at position zero when focused programmatically."""
    widget = _make_line_edit('')

    _send_focus_in(widget, Qt.OtherFocusReason)

    assert widget.textCursor().position() == 0


@pytest.mark.parametrize(
    'reason',
    [Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason],
)
def test_focus_in_tab_like_reasons_select_all(qapp, reason):
    """Tab/Backtab/Shortcut focus selects the whole line to mimic QLineEdit."""
    text = 'hello world'
    widget = _make_line_edit(text)

    _send_focus_in(widget, reason)

    assert widget.textCursor().hasSelection()
    assert widget.textCursor().selectedText() == text


def test_focus_in_mouse_reason_leaves_cursor_untouched(qapp):
    """A mouse click must not move the cursor or select text.

    Guards against OtherFocusReason handling leaking into mouse clicks, which
    would steal the click position the user actually clicked on.
    """
    widget = _make_line_edit('hello world')

    _send_focus_in(widget, Qt.MouseFocusReason)

    assert widget.textCursor().position() == 0
    assert not widget.textCursor().hasSelection()
