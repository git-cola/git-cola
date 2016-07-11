#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals
import collections
import re
import sys

from qtpy.QtCore import Qt
from qtpy.QtCore import QEvent
from qtpy.QtCore import Signal
from qtpy.QtGui import QMouseEvent
from qtpy.QtGui import QSyntaxHighlighter
from qtpy.QtGui import QTextCharFormat
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QAction
from qtpy.QtWidgets import QApplication

from cola import qtutils
from cola.i18n import N_
from cola.widgets.text import HintedTextEdit


__copyright__ = """
2012, Peter Norvig (http://norvig.com/spell-correct.html)
2013, David Aguilar <davvid@gmail.com>
"""

alphabet = 'abcdefghijklmnopqrstuvwxyz'


def train(features, model):
    for f in features:
        model[f] += 1
    return model


def edits1(word):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
    replaces = [a + c + b[1:] for a, b in splits for c in alphabet if b]
    inserts = [a + c + b for a, b in splits for c in alphabet]
    return set(deletes + transposes + replaces + inserts)


def known_edits2(word, words):
    return set(e2 for e1 in edits1(word)
               for e2 in edits1(e1) if e2 in words)


def known(word, words):
    return set(w for w in word if w in words)


def suggest(word, words):
    candidates = (known([word], words) or
                  known(edits1(word), words) or
                  known_edits2(word, words) or [word])
    return candidates


def correct(word, words):
    candidates = suggest(word, words)
    return max(candidates, key=words.get)


class NorvigSpellCheck(object):
    def __init__(self):
        self.words = collections.defaultdict(lambda: 1)
        self.extra_words = set()
        self.initialized = False

    def init(self):
        if self.initialized:
            return
        self.initialized = True
        train(self.read(), self.words)
        train(self.extra_words, self.words)

    def add_word(self, word):
        self.extra_words.add(word)

    def suggest(self, word):
        self.init()
        return suggest(word, self.words)

    def check(self, word):
        self.init()
        return word.replace('.', '') in self.words

    def read(self):
        for (path, title) in (('/usr/share/dict/words', True),
                              ('/usr/share/dict/propernames', False)):
            try:
                with open(path, 'r') as f:
                    for word in f:
                        yield word.rstrip()
                        if title:
                            yield word.rstrip().title()
            except IOError:
                pass
        raise StopIteration


class SpellCheckTextEdit(HintedTextEdit):

    def __init__(self, hint, parent=None):
        HintedTextEdit.__init__(self, hint, parent)

        # Default dictionary based on the current locale.
        self.spellcheck = NorvigSpellCheck()
        self.highlighter = Highlighter(self.document(), self.spellcheck)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Rewrite the mouse event to a left button event so the cursor is
            # moved to the location of the pointer.
            event = QMouseEvent(QEvent.MouseButtonPress,
                                event.pos(),
                                Qt.LeftButton,
                                Qt.LeftButton,
                                Qt.NoModifier)
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
                if len(spell_menu.actions()) > 0:
                    popup_menu.addSeparator()
                    popup_menu.addMenu(spell_menu)

        return popup_menu, spell_menu

    def contextMenuEvent(self, event):
        popup_menu, _spell_menu = self.context_menu()
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

    def __init__(self, doc, spellcheck):
        QSyntaxHighlighter.__init__(self, doc)
        self.spellcheck = spellcheck
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
                self.setFormat(word_object.start(),
                               word_object.end() - word_object.start(), fmt)


class SpellAction(QAction):
    """QAction that returns the text in a signal.
    """
    result = Signal(object)

    def __init__(self, *args):
        QAction.__init__(self, *args)
        self.triggered.connect(self.correct)

    def correct(self):
        self.result.emit(self.text())


def main(args=sys.argv):
    app = QApplication(args)

    widget = SpellCheckTextEdit('Type here')
    widget.show()
    widget.raise_()

    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
