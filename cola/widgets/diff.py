from __future__ import division, absolute_import, unicode_literals
import re
import math

from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..i18n import N_
from ..models import main
from ..models import selection
from ..qtutils import add_action
from ..qtutils import create_action_button
from ..qtutils import create_menu
from ..qtutils import make_format
from ..qtutils import RGB
from .. import actions
from .. import cmds
from .. import compat
from .. import core
from .. import diffparse
from .. import gitcfg
from .. import gitcmds
from .. import gravatar
from .. import hotkeys
from .. import icons
from .. import qtutils
from .text import TextDecorator
from .text import VimHintedPlainTextEdit
from . import defs


COMMITS_SELECTED = 'COMMITS_SELECTED'
FILES_SELECTED = 'FILES_SELECTED'


class DiffSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    """Implements the diff syntax highlighting"""

    INITIAL_STATE = -1
    DEFAULT_STATE = 0
    DIFFSTAT_STATE = 1
    DIFF_FILE_HEADER_STATE = 2
    DIFF_STATE = 3
    SUBMODULE_STATE = 4

    DIFF_FILE_HEADER_START_RGX = re.compile(r'diff --git a/.* b/.*')
    DIFF_HUNK_HEADER_RGX = re.compile(r'(?:@@ -[0-9,]+ \+[0-9,]+ @@)|'
                                      r'(?:@@@ (?:-[0-9,]+ ){2}\+[0-9,]+ @@@)')
    BAD_WHITESPACE_RGX = re.compile(r'\s+$')

    def __init__(self, doc, whitespace=True, is_commit=False):
        QtGui.QSyntaxHighlighter.__init__(self, doc)
        self.whitespace = whitespace
        self.enabled = True
        self.is_commit = is_commit

        QPalette = QtGui.QPalette
        cfg = gitcfg.current()
        palette = QPalette()
        disabled = palette.color(QPalette.Disabled, QPalette.Text)
        header = qtutils.rgb_hex(disabled)

        self.color_text = RGB(cfg.color('text', '030303'))
        self.color_add = RGB(cfg.color('add', 'd2ffe4'))
        self.color_remove = RGB(cfg.color('remove', 'fee0e4'))
        self.color_header = RGB(cfg.color('header', header))

        self.diff_header_fmt = make_format(fg=self.color_header)
        self.bold_diff_header_fmt = make_format(fg=self.color_header, bold=True)

        self.diff_add_fmt = make_format(fg=self.color_text,
                                        bg=self.color_add)
        self.diff_remove_fmt = make_format(fg=self.color_text,
                                           bg=self.color_remove)
        self.bad_whitespace_fmt = make_format(bg=Qt.red)
        self.setCurrentBlockState(self.INITIAL_STATE)

    def set_enabled(self, enabled):
        self.enabled = enabled

    def highlightBlock(self, text):
        if not self.enabled or not text:
            return

        state = self.previousBlockState()
        if state == self.INITIAL_STATE:
            if text.startswith('Submodule '):
                state = self.SUBMODULE_STATE
            elif text.startswith('diff --git '):
                state = self.DIFFSTAT_STATE
            elif self.is_commit:
                state = self.DEFAULT_STATE
            else:
                state = self.DIFFSTAT_STATE

        if state == self.DIFFSTAT_STATE:
            if self.DIFF_FILE_HEADER_START_RGX.match(text):
                state = self.DIFF_FILE_HEADER_STATE
                self.setFormat(0, len(text), self.diff_header_fmt)
            elif self.DIFF_HUNK_HEADER_RGX.match(text):
                state = self.DIFF_STATE
                self.setFormat(0, len(text), self.bold_diff_header_fmt)
            elif '|' in text:
                i = text.index('|')
                self.setFormat(0, i, self.bold_diff_header_fmt)
                self.setFormat(i, len(text) - i, self.diff_header_fmt)
            else:
                self.setFormat(0, len(text), self.diff_header_fmt)
        elif state == self.DIFF_FILE_HEADER_STATE:
            if self.DIFF_HUNK_HEADER_RGX.match(text):
                state = self.DIFF_STATE
                self.setFormat(0, len(text), self.bold_diff_header_fmt)
            else:
                self.setFormat(0, len(text), self.diff_header_fmt)
        elif state == self.DIFF_STATE:
            if self.DIFF_FILE_HEADER_START_RGX.match(text):
                state = self.DIFF_FILE_HEADER_STATE
                self.setFormat(0, len(text), self.diff_header_fmt)
            elif self.DIFF_HUNK_HEADER_RGX.match(text):
                self.setFormat(0, len(text), self.bold_diff_header_fmt)
            elif text.startswith('-'):
                self.setFormat(0, len(text), self.diff_remove_fmt)
            elif text.startswith('+'):
                self.setFormat(0, len(text), self.diff_add_fmt)
                if self.whitespace:
                    m = self.BAD_WHITESPACE_RGX.search(text)
                    if m is not None:
                        i = m.start()
                        self.setFormat(i, len(text) - i,
                                       self.bad_whitespace_fmt)

        self.setCurrentBlockState(state)


class DiffTextEdit(VimHintedPlainTextEdit):

    def __init__(self, parent,
                 is_commit=False, whitespace=True, numbers=False):
        VimHintedPlainTextEdit.__init__(self, '', parent=parent)
        # Diff/patch syntax highlighter
        self.highlighter = DiffSyntaxHighlighter(self.document(),
                                                 is_commit=is_commit,
                                                 whitespace=whitespace)
        if numbers:
            self.numbers = DiffLineNumbers(self)
            self.numbers.hide()
        else:
            self.numbers = None

        self.cursorPositionChanged.connect(self._cursor_changed)

    def _cursor_changed(self):
        """Update the line number display when the cursor changes"""
        line_number = max(0, self.textCursor().blockNumber())
        if self.numbers:
            self.numbers.set_highlighted(line_number)

    def resizeEvent(self, event):
        super(DiffTextEdit, self).resizeEvent(event)
        if self.numbers:
            self.numbers.refresh_size()

    def set_loading_message(self):
        self.hint.set_value('+++ ' + N_('Loading...'))
        self.set_value('')

    def set_diff(self, diff):
        self.hint.set_value('')
        if self.numbers:
            self.numbers.set_diff(diff)
        self.set_value(diff)


class DiffLineNumbers(TextDecorator):

    def __init__(self, parent):
        TextDecorator.__init__(self, parent)
        self.highlight_line = -1
        self.lines = None
        self.parser = diffparse.DiffLines()
        self.formatter = diffparse.FormatDigits()

        self.setFont(qtutils.diff_font())
        self._char_width = self.fontMetrics().width('0')

        QPalette = QtGui.QPalette
        self._palette = palette = self.palette()
        self._base = palette.color(QtGui.QPalette.Base)
        self._highlight = palette.color(QPalette.Highlight)
        self._highlight_text = palette.color(QPalette.HighlightedText)
        self._window = palette.color(QPalette.Window)
        self._disabled = palette.color(QPalette.Disabled, QPalette.Text)

    def set_diff(self, diff):
        parser = self.parser
        lines = parser.parse(diff)
        if parser.valid:
            self.lines = lines
            self.formatter.set_digits(self.parser.digits())
        else:
            self.lines = None

    def set_lines(self, lines):
        self.lines = lines

    def width_hint(self):
        if not self.isVisible():
            return 0
        parser = self.parser
        if parser.valid:
            digits = parser.digits() * 2
        else:
            digits = 4

        extra = 2  # one space in-between, one space after
        return defs.margin + (self._char_width * (digits + extra))

    def set_highlighted(self, line_number):
        """Set the line to highlight"""
        self.highlight_line = line_number

    def paintEvent(self, event):
        """Paint the line number"""
        if not self.lines:
            return

        painter = QtGui.QPainter(self)
        painter.fillRect(event.rect(), self._base)

        editor = self.editor
        content_offset = editor.contentOffset()
        block = editor.firstVisibleBlock()
        current_block_number = max(0, editor.textCursor().blockNumber())
        width = self.width()
        event_rect_bottom = event.rect().bottom()

        highlight = self._highlight
        highlight_text = self._highlight_text
        window = self._window
        disabled = self._disabled

        fmt = self.formatter
        lines = self.lines
        num_lines = len(self.lines)
        painter.setPen(disabled)

        while block.isValid():
            block_number = block.blockNumber()
            if block_number >= num_lines:
                break
            block_geom = editor.blockBoundingGeometry(block)
            block_top = block_geom.translated(content_offset).top()
            if not block.isVisible() or block_top >= event_rect_bottom:
                break

            rect = block_geom.translated(content_offset).toRect()
            if block_number == self.highlight_line:
                painter.setPen(highlight_text)
                painter.fillRect(rect.x(), rect.y(),
                                 width, rect.height(), highlight)
                painter.setPen(disabled)
            elif block_number == current_block_number:
                painter.fillRect(rect.x(), rect.y(),
                                 width, rect.height(), window)

            a, b = lines[block_number]
            text = fmt.value(a, b)

            painter.drawText(rect.x(), rect.y(),
                             self.width() - (defs.margin * 2), rect.height(),
                             Qt.AlignRight | Qt.AlignVCenter, text)

            block = block.next()  # pylint: disable=next-method-called


class DiffEditorWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.editor = DiffEditor(self, parent.titleBarWidget())
        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.editor)
        self.setLayout(self.main_layout)
        self.setFocusProxy(self.editor)


class DiffEditor(DiffTextEdit):

    up = Signal()
    down = Signal()
    options_changed = Signal()
    updated = Signal()
    diff_text_changed = Signal(object)

    def __init__(self, parent, titlebar):
        DiffTextEdit.__init__(self, parent, numbers=True)
        self.model = model = main.model()

        # "Diff Options" tool menu
        self.diff_ignore_space_at_eol_action = add_action(
            self, N_('Ignore changes in whitespace at EOL'),
            self._update_diff_opts)
        self.diff_ignore_space_at_eol_action.setCheckable(True)

        self.diff_ignore_space_change_action = add_action(
            self, N_('Ignore changes in amount of whitespace'),
            self._update_diff_opts)
        self.diff_ignore_space_change_action.setCheckable(True)

        self.diff_ignore_all_space_action = add_action(
            self, N_('Ignore all whitespace'), self._update_diff_opts)
        self.diff_ignore_all_space_action.setCheckable(True)

        self.diff_function_context_action = add_action(
            self, N_('Show whole surrounding functions of changes'),
            self._update_diff_opts)
        self.diff_function_context_action.setCheckable(True)

        self.diff_show_line_numbers = add_action(
            self, N_('Show lines numbers'),
            self._update_diff_opts)
        self.diff_show_line_numbers.setCheckable(True)

        self.diffopts_button = create_action_button(
            tooltip=N_('Diff Options'), icon=icons.configure())
        self.diffopts_menu = create_menu(N_('Diff Options'),
                                         self.diffopts_button)

        self.diffopts_menu.addAction(self.diff_ignore_space_at_eol_action)
        self.diffopts_menu.addAction(self.diff_ignore_space_change_action)
        self.diffopts_menu.addAction(self.diff_ignore_all_space_action)
        self.diffopts_menu.addAction(self.diff_show_line_numbers)
        self.diffopts_menu.addAction(self.diff_function_context_action)
        self.diffopts_button.setMenu(self.diffopts_menu)
        qtutils.hide_button_menu_indicator(self.diffopts_button)

        titlebar.add_corner_widget(self.diffopts_button)

        self.action_apply_selection = qtutils.add_action(
            self, 'Apply', self.apply_selection, hotkeys.STAGE_DIFF)

        self.action_revert_selection = qtutils.add_action(
            self, 'Revert', self.revert_selection, hotkeys.REVERT)
        self.action_revert_selection.setIcon(icons.undo())

        self.launch_editor = actions.launch_editor(self, *hotkeys.ACCEPT)
        self.launch_difftool = actions.launch_difftool(self)
        self.stage_or_unstage = actions.stage_or_unstage(self)

        # Emit up/down signals so that they can be routed by the main widget
        self.move_up = actions.move_up(self)
        self.move_down = actions.move_down(self)

        diff_text_changed = model.message_diff_text_changed
        model.add_observer(diff_text_changed, self.diff_text_changed.emit)

        self.selection_model = selection_model = selection.selection_model()
        selection_model.add_observer(selection_model.message_selection_changed,
                                     self.updated.emit)
        self.updated.connect(self.refresh, type=Qt.QueuedConnection)

        self.diff_text_changed.connect(self.set_diff)

    def refresh(self):
        enabled = False
        s = self.selection_model.selection()
        if s.modified and self.model.stageable():
            if s.modified[0] in self.model.submodules:
                pass
            elif s.modified[0] not in main.model().unstaged_deleted:
                enabled = True
        self.action_revert_selection.setEnabled(enabled)

    def enable_line_numbers(self, enabled):
        """Enable/disable the diff line number display"""
        self.numbers.setVisible(enabled)
        self.diff_show_line_numbers.setChecked(enabled)

    def show_line_numbers(self):
        """Return True if we should show line numbers"""
        return self.diff_show_line_numbers.isChecked()

    def _update_diff_opts(self):
        space_at_eol = self.diff_ignore_space_at_eol_action.isChecked()
        space_change = self.diff_ignore_space_change_action.isChecked()
        all_space = self.diff_ignore_all_space_action.isChecked()
        function_context = self.diff_function_context_action.isChecked()
        self.numbers.setVisible(self.show_line_numbers())

        gitcmds.update_diff_overrides(space_at_eol,
                                      space_change,
                                      all_space,
                                      function_context)
        self.options_changed.emit()

    # Qt overrides
    def contextMenuEvent(self, event):
        """Create the context menu for the diff display."""
        menu = qtutils.create_menu(N_('Actions'), self)
        s = selection.selection()
        filename = selection.filename()

        if self.model.stageable() or self.model.unstageable():
            if self.model.stageable():
                self.stage_or_unstage.setText(N_('Stage'))
            else:
                self.stage_or_unstage.setText(N_('Unstage'))
            menu.addAction(self.stage_or_unstage)

        if s.modified and self.model.stageable():
            if s.modified[0] in main.model().submodules:
                action = menu.addAction(icons.add(), cmds.Stage.name(),
                                        cmds.run(cmds.Stage, s.modified))
                action.setShortcut(hotkeys.STAGE_SELECTION)
                menu.addAction(icons.cola(), N_('Launch git-cola'),
                               cmds.run(cmds.OpenRepo,
                                        core.abspath(s.modified[0])))
            elif s.modified[0] not in main.model().unstaged_deleted:
                if self.has_selection():
                    apply_text = N_('Stage Selected Lines')
                    revert_text = N_('Revert Selected Lines...')
                else:
                    apply_text = N_('Stage Diff Hunk')
                    revert_text = N_('Revert Diff Hunk...')

                self.action_apply_selection.setText(apply_text)
                self.action_apply_selection.setIcon(icons.add())

                self.action_revert_selection.setText(revert_text)

                menu.addAction(self.action_apply_selection)
                menu.addAction(self.action_revert_selection)

        if s.staged and self.model.unstageable():
            if s.staged[0] in main.model().submodules:
                action = menu.addAction(icons.remove(), cmds.Unstage.name(),
                                        cmds.do(cmds.Unstage, s.staged))
                action.setShortcut(hotkeys.STAGE_SELECTION)
                menu.addAction(icons.cola(), N_('Launch git-cola'),
                               cmds.do(cmds.OpenRepo,
                                       core.abspath(s.staged[0])))
            elif s.staged[0] not in main.model().staged_deleted:
                if self.has_selection():
                    apply_text = N_('Unstage Selected Lines')
                else:
                    apply_text = N_('Unstage Diff Hunk')

                self.action_apply_selection.setText(apply_text)
                self.action_apply_selection.setIcon(icons.remove())
                menu.addAction(self.action_apply_selection)

        if self.model.stageable() or self.model.unstageable():
            # Do not show the "edit" action when the file does not exist.
            # Untracked files exist by definition.
            if filename and core.exists(filename):
                menu.addSeparator()
                menu.addAction(self.launch_editor)

            # Removed files can still be diffed.
            menu.addAction(self.launch_difftool)

        # Add the Previous/Next File actions, which improves discoverability
        # of their associated shortcuts
        menu.addSeparator()
        menu.addAction(self.move_up)
        menu.addAction(self.move_down)

        menu.addSeparator()
        action = menu.addAction(icons.copy(), N_('Copy'), self.copy)
        action.setShortcut(QtGui.QKeySequence.Copy)

        action = menu.addAction(icons.select_all(), N_('Select All'),
                                self.selectAll)
        action.setShortcut(QtGui.QKeySequence.SelectAll)
        menu.exec_(self.mapToGlobal(event.pos()))

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Intercept right-click to move the cursor to the current position.
            # setTextCursor() clears the selection so this is only done when
            # nothing is selected.
            if not self.has_selection():
                cursor = self.cursorForPosition(event.pos())
                self.setTextCursor(cursor)

        return DiffTextEdit.mousePressEvent(self, event)

    def setPlainText(self, text):
        """setPlainText(str) while retaining scrollbar positions"""
        mode = self.model.mode
        highlight = (mode != self.model.mode_none and
                     mode != self.model.mode_untracked)
        self.highlighter.set_enabled(highlight)

        scrollbar = self.verticalScrollBar()
        if scrollbar:
            scrollvalue = scrollbar.value()
        else:
            scrollvalue = None

        if text is None:
            return

        offset, selection_text = self.offset_and_selection()
        old_text = self.toPlainText()

        DiffTextEdit.setPlainText(self, text)

        if selection_text and selection_text in text:
            # If the old selection exists in the new text then re-select it.
            idx = text.index(selection_text)
            cursor = self.textCursor()
            cursor.setPosition(idx)
            cursor.setPosition(idx + len(selection_text),
                               QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)

        elif text == old_text:
            # Otherwise, if the text is identical and there is no selection
            # then restore the cursor position.
            cursor = self.textCursor()
            cursor.setPosition(offset)
            self.setTextCursor(cursor)
        else:
            # If none of the above applied then restore the cursor position.
            position = max(0, min(offset, len(text) - 1))
            cursor = self.textCursor()
            cursor.setPosition(position)
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            self.setTextCursor(cursor)

        if scrollbar and scrollvalue is not None:
            scrollbar.setValue(scrollvalue)

    def has_selection(self):
        return self.textCursor().hasSelection()

    def offset_and_selection(self):
        cursor = self.textCursor()
        offset = cursor.selectionStart()
        selection_text = cursor.selection().toPlainText()
        return offset, selection_text

    def selected_lines(self):
        cursor = self.textCursor()
        selection_start = cursor.selectionStart()
        selection_end = max(selection_start, cursor.selectionEnd() - 1)

        line_start = 0
        for line_idx, line in enumerate(self.value().splitlines()):
            line_end = line_start + len(line)
            if line_start <= selection_start <= line_end:
                first_line_idx = line_idx
            if line_start <= selection_end <= line_end:
                last_line_idx = line_idx
                break
            line_start = line_end + 1

        return first_line_idx, last_line_idx

    def apply_selection(self):
        s = selection.single_selection()
        if self.model.stageable() and s.modified:
            self.process_diff_selection()
        elif self.model.unstageable():
            self.process_diff_selection(reverse=True)

    def revert_selection(self):
        """Destructively revert selected lines or hunk from a worktree file."""

        if self.has_selection():
            title = N_('Revert Selected Lines?')
            ok_text = N_('Revert Selected Lines')
        else:
            title = N_('Revert Diff Hunk?')
            ok_text = N_('Revert Diff Hunk')

        if not qtutils.confirm(title,
                               N_('This operation drops uncommitted changes.\n'
                                  'These changes cannot be recovered.'),
                               N_('Revert the uncommitted changes?'),
                               ok_text, default=True, icon=icons.undo()):
            return
        self.process_diff_selection(reverse=True, apply_to_worktree=True)

    def process_diff_selection(self, reverse=False, apply_to_worktree=False):
        """Implement un/staging of the selected line(s) or hunk."""
        if selection.selection_model().is_empty():
            return
        first_line_idx, last_line_idx = self.selected_lines()
        cmds.do(cmds.ApplyDiffSelection, first_line_idx, last_line_idx,
                self.has_selection(), reverse, apply_to_worktree)


class DiffWidget(QtWidgets.QWidget):

    def __init__(self, notifier, parent, is_commit=False):
        QtWidgets.QWidget.__init__(self, parent)

        self.runtask = qtutils.RunTask(parent=self)

        author_font = QtGui.QFont(self.font())
        author_font.setPointSize(int(author_font.pointSize() * 1.1))

        summary_font = QtGui.QFont(author_font)
        summary_font.setWeight(QtGui.QFont.Bold)

        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                       QtWidgets.QSizePolicy.Minimum)

        self.gravatar_label = gravatar.GravatarLabel()

        self.author_label = TextLabel()
        self.author_label.setTextFormat(Qt.RichText)
        self.author_label.setFont(author_font)
        self.author_label.setSizePolicy(policy)
        self.author_label.setAlignment(Qt.AlignBottom)
        self.author_label.elide()

        self.summary_label = TextLabel()
        self.summary_label.setTextFormat(Qt.PlainText)
        self.summary_label.setFont(summary_font)
        self.summary_label.setSizePolicy(policy)
        self.summary_label.setAlignment(Qt.AlignTop)
        self.summary_label.elide()

        self.oid_label = TextLabel()
        self.oid_label.setTextFormat(Qt.PlainText)
        self.oid_label.setSizePolicy(policy)
        self.oid_label.setAlignment(Qt.AlignTop)
        self.oid_label.elide()

        self.diff = DiffTextEdit(self, is_commit=is_commit, whitespace=False)

        self.info_layout = qtutils.vbox(defs.no_margin, defs.no_spacing,
                                        self.author_label, self.summary_label,
                                        self.oid_label)

        self.logo_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                        self.gravatar_label, self.info_layout)
        self.logo_layout.setContentsMargins(defs.margin, 0, defs.margin, 0)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.logo_layout, self.diff)
        self.setLayout(self.main_layout)

        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)
        notifier.add_observer(FILES_SELECTED, self.files_selected)

    def set_diff_oid(self, oid, filename=None):
        self.diff.set_loading_message()
        task = DiffInfoTask(oid, filename, self)
        task.connect(self.diff.set_value)
        self.runtask.start(task)

    def commits_selected(self, commits):
        if len(commits) != 1:
            return
        commit = commits[0]
        self.oid = commit.oid

        email = commit.email or ''
        summary = commit.summary or ''
        author = commit.author or ''

        template_args = {
                'author': author,
                'email': email,
                'summary': summary
        }

        author_text = ("""%(author)s &lt;"""
                       """<a href="mailto:%(email)s">"""
                       """%(email)s</a>&gt;"""
                       % template_args)

        author_template = '%(author)s <%(email)s>' % template_args
        self.author_label.set_template(author_text, author_template)
        self.summary_label.set_text(summary)
        self.oid_label.set_text(self.oid)

        self.set_diff_oid(self.oid)
        self.gravatar_label.set_email(email)

    def files_selected(self, filenames):
        if not filenames:
            return
        self.set_diff_oid(self.oid, filenames[0])


class TextLabel(QtWidgets.QLabel):

    def __init__(self, parent=None):
        QtWidgets.QLabel.__init__(self, parent)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse |
                                     Qt.LinksAccessibleByMouse)
        self._display = ''
        self._template = ''
        self._text = ''
        self._elide = False
        self._metrics = QtGui.QFontMetrics(self.font())
        self.setOpenExternalLinks(True)

    def elide(self):
        self._elide = True

    def set_text(self, text):
        self.set_template(text, text)

    def set_template(self, text, template):
        self._display = text
        self._text = text
        self._template = template
        self.update_text(self.width())
        self.setText(self._display)

    def update_text(self, width):
        self._display = self._text
        if not self._elide:
            return
        text = self._metrics.elidedText(self._template,
                                        Qt.ElideRight, width-2)
        if text != self._template:
            self._display = text

    # Qt overrides
    def setFont(self, font):
        self._metrics = QtGui.QFontMetrics(font)
        QtWidgets.QLabel.setFont(self, font)

    def resizeEvent(self, event):
        if self._elide:
            self.update_text(event.size().width())
            block = self.blockSignals(True)
            self.setText(self._display)
            self.blockSignals(block)
        QtWidgets.QLabel.resizeEvent(self, event)


class DiffInfoTask(qtutils.Task):

    def __init__(self, oid, filename, parent):
        qtutils.Task.__init__(self, parent)
        self.oid = oid
        self.filename = filename

    def task(self):
        return gitcmds.diff_info(self.oid, filename=self.filename)
