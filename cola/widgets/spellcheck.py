from __future__ import absolute_import, division, print_function, unicode_literals
import re

from qtpy.QtCore import Qt
from qtpy.QtCore import QEvent
from qtpy.QtCore import Signal
from qtpy.QtGui import QMouseEvent
from qtpy.QtGui import QSyntaxHighlighter
from qtpy.QtGui import QTextCharFormat
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QAction

from .. import qtutils
from .. import spellcheck
from ..i18n import N_
from .text import HintedTextEdit


# pylint: disable=too-many-ancestors
class SpellCheckTextEdit(HintedTextEdit):
    def __init__(self, context, hint, parent=None):
        HintedTextEdit.__init__(self, context, hint, parent)

        # Default dictionary based on the current locale.
        self.spellcheck = spellcheck.NorvigSpellCheck()
        self.highlighter = Highlighter(self.document(), self.spellcheck)

    def set_dictionary(self, dictionary):
        self.spellcheck.set_dictionary(dictionary)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Rewrite the mouse event to a left button event so the cursor is
            # moved to the location of the pointer.
            event = QMouseEvent(
                QEvent.MouseButtonPress,
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
        cursor.select(QTextCursor.WordUnderCursor)
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


class Highlighter(QSyntaxHighlighter):

    WORDS = r"(?iu)[\w']+"

    def __init__(self, doc, spellcheck_widget):
        QSyntaxHighlighter.__init__(self, doc)
        self.spellcheck = spellcheck_widget
        self.enabled = False

    def enable(self, enabled):
        self.enabled = enabled
        self.rehighlight()

    def highlightBlock(self, text):
        if not self.enabled:
            return
        fmt = QTextCharFormat()
        fmt.setUnderlineColor(Qt.red)
        fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)

        for word_object in re.finditer(self.WORDS, text):
            if not self.spellcheck.check(word_object.group()):
                self.setFormat(
                    word_object.start(), word_object.end() - word_object.start(), fmt
                )


class SpellAction(QAction):
    """QAction that returns the text in a signal."""

    result = Signal(object)

    def __init__(self, *args):
        QAction.__init__(self, *args)
        # pylint: disable=no-member
        self.triggered.connect(self.correct)

    def correct(self):
        self.result.emit(self.text())
