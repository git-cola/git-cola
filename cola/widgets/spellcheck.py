from __future__ import absolute_import, division, print_function, unicode_literals
import re

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import qtutils
from .. import spellcheck
from ..i18n import N_
from .text import HintedTextEdit


# pylint: disable=too-many-ancestors
class SpellCheckTextEdit(HintedTextEdit):
    def __init__(self, context, hint, check=None, parent=None):
        HintedTextEdit.__init__(self, context, hint, parent)

        # Default dictionary based on the current locale.
        self.spellcheck = check or spellcheck.NorvigSpellCheck()
        self.highlighter = Highlighter(self.document(), self.spellcheck)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Rewrite the mouse event to a left button event so the cursor is
            # moved to the location of the pointer.
            event = QtGui.QMouseEvent(
                QtCore.QEvent.MouseButtonPress,
                event.pos(),
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier,
            )
        HintedTextEdit.mousePressEvent(self, event)

    def context_menu(self):
        popup_menu = HintedTextEdit.createStandardContextMenu(self)

        # Select the word under the cursor.
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.WordUnderCursor)
        self.setTextCursor(cursor)

        # Check if the selected word is misspelled and offer spelling
        # suggestions if it is.
        spell_menu = None
        if self.textCursor().hasSelection():
            text = self.textCursor().selectedText()
            if not self.spellcheck.check(text):
                title = N_('Spelling Suggestions')
                spell_menu = qtutils.create_menu(title, self)
                for word in self.spellcheck.suggest(text):
                    action = SpellAction(word, spell_menu)
                    action.result.connect(self.correct)
                    spell_menu.addAction(action)
                # Only add the spelling suggests to the menu if there are
                # suggestions.
                if spell_menu.actions():
                    popup_menu.addSeparator()
                    popup_menu.addMenu(spell_menu)

        return popup_menu, spell_menu

    def contextMenuEvent(self, event):
        popup_menu, _ = self.context_menu()
        popup_menu.exec_(self.mapToGlobal(event.pos()))

    def correct(self, word):
        """Replaces the selected text with word."""
        cursor = self.textCursor()
        cursor.beginEditBlock()

        cursor.removeSelectedText()
        cursor.insertText(word)

        cursor.endEditBlock()


class Highlighter(QtGui.QSyntaxHighlighter):

    WORDS = r"(?iu)[\w']+"

    def __init__(self, doc, spellcheck_widget):
        QtGui.QSyntaxHighlighter.__init__(self, doc)
        self.spellcheck = spellcheck_widget
        self.enabled = False

    def enable(self, enabled):
        self.enabled = enabled
        self.rehighlight()

    def highlightBlock(self, text):
        if not self.enabled:
            return
        fmt = QtGui.QTextCharFormat()
        fmt.setUnderlineColor(Qt.red)
        fmt.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)

        for word_object in re.finditer(self.WORDS, text):
            if not self.spellcheck.check(word_object.group()):
                self.setFormat(
                    word_object.start(), word_object.end() - word_object.start(), fmt
                )


class SpellAction(QtWidgets.QAction):
    """QAction that returns the text in a signal."""

    result = QtCore.Signal(object)

    def __init__(self, *args):
        QtWidgets.QAction.__init__(self, *args)
        # pylint: disable=no-member
        self.triggered.connect(self.correct)

    def correct(self):
        self.result.emit(self.text())
