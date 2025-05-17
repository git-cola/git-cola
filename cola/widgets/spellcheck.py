import re

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import qtutils
from .. import spellcheck
from ..i18n import N_
from .text import event_anchor_mode, HintedTextEdit


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
            if hasattr(event, 'position'):  # Qt6
                position = event.position()
            else:
                position = event.pos()
            event = QtGui.QMouseEvent(
                QtCore.QEvent.MouseButtonPress,
                position,
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier,
            )
        HintedTextEdit.mousePressEvent(self, event)

    def create_context_menu(self, event_pos):
        popup_menu = super().create_context_menu(event_pos)

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

        return popup_menu

    def contextMenuEvent(self, event):
        """Select the current word and then show a context menu"""
        # Select the word under the cursor before calling the default contextMenuEvent.
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.WordUnderCursor)
        self.setTextCursor(cursor)
        super().contextMenuEvent(event)

    def correct(self, word):
        """Replaces the selected text with word."""
        cursor = self.textCursor()
        cursor.beginEditBlock()

        cursor.removeSelectedText()
        cursor.insertText(word)

        cursor.endEditBlock()


class SpellCheckLineEdit(SpellCheckTextEdit):
    """A fake QLineEdit that provides spellcheck capabilities

    This class emulates QLineEdit using our QPlainTextEdit base class
    so that we can leverage the existing spellcheck feature.

    """

    down_pressed = QtCore.Signal()

    # This widget is a single-line QTextEdit as described in
    # http://blog.ssokolow.com/archives/2022/07/22/a-qlineedit-replacement-with-spell-checking/
    def __init__(self, context, hint, check=None, parent=None):
        super().__init__(context, hint, check=check, parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._trim_changed_text_lines)

    def focusInEvent(self, event):
        """Select text when entering with a tab to mimic QLineEdit"""
        super().focusInEvent(event)

        if event.reason() in (
            Qt.BacktabFocusReason,
            Qt.ShortcutFocusReason,
            Qt.TabFocusReason,
        ):
            self.selectAll()

    def focusOutEvent(self, event):
        """De-select text when exiting with tab to mimic QLineEdit"""
        super().focusOutEvent(event)

        if event.reason() in (
            Qt.BacktabFocusReason,
            Qt.MouseFocusReason,
            Qt.ShortcutFocusReason,
            Qt.TabFocusReason,
        ):
            cur = self.textCursor()
            cur.movePosition(QtGui.QTextCursor.End)
            self.setTextCursor(cur)

    def keyPressEvent(self, event):
        """Handle the up/down arrow keys"""
        event_key = event.key()
        if event_key == Qt.Key_Up:
            cursor = self.textCursor()
            if cursor.position() == 0:
                cursor.clearSelection()
            else:
                mode = event_anchor_mode(event)
                cursor.setPosition(0, mode)
            self.setTextCursor(cursor)
            return

        if event_key == Qt.Key_Down:
            cursor = self.textCursor()
            cur_position = cursor.position()
            end_position = len(self.value())
            if cur_position == end_position:
                cursor.clearSelection()
                self.setTextCursor(cursor)
                self.down_pressed.emit()
            else:
                mode = event_anchor_mode(event)
                cursor.setPosition(end_position, mode)
                self.setTextCursor(cursor)
            return
        super().keyPressEvent(event)

    def minimumSizeHint(self):
        """Match QLineEdit's size behavior"""
        width = super().minimumSizeHint().width()
        height = self._get_preferred_height()
        style_opts = QtWidgets.QStyleOptionFrame()
        style_opts.initFrom(self)
        style_opts.lineWidth = self.frameWidth()

        return self.style().sizeFromContents(
            QtWidgets.QStyle.CT_LineEdit, style_opts, QtCore.QSize(width, height), self
        )

    def sizeHint(self):
        """Use the minimum size as the sizeHint()"""
        return self.minimumSizeHint()

    def setFont(self, font):
        """Set the current font"""
        self.setMinimumHeight(self._get_preferred_height(font=font))
        super().setFont(font)

    def _get_preferred_height(self, font=None):
        """Calculate the preferred height for this widget"""
        if font is None:
            font = self.font()
        block_fmt = self.document().firstBlock().blockFormat()
        height = int(
            QtGui.QFontMetricsF(font).lineSpacing()
            + block_fmt.topMargin()
            + block_fmt.bottomMargin()
            + 2 * self.document().documentMargin()
            + 2 * self.frameWidth()
        )
        return height

    def _trim_changed_text_lines(self):
        """Trim the document to a single line to enforce a maximum of one line"""
        # self.setMaximumBlockCount(1) Undo/Redo.
        if self.document().blockCount() > 1:
            self.document().setPlainText(self.document().firstBlock().text())


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
        self.triggered.connect(self.correct)

    def correct(self):
        self.result.emit(self.text())
