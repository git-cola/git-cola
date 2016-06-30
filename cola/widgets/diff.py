from __future__ import division, absolute_import, unicode_literals
import re

from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from cola import actions
from cola import cmds
from cola import core
from cola import gitcfg
from cola import gitcmds
from cola import gravatar
from cola import hotkeys
from cola import icons
from cola import qtutils
from cola.i18n import N_
from cola.models import main
from cola.models import selection
from cola.qtutils import add_action
from cola.qtutils import create_action_button
from cola.qtutils import create_menu
from cola.qtutils import make_format
from cola.qtutils import RGB
from cola.widgets import defs
from cola.widgets.text import VimMonoTextView


COMMITS_SELECTED = 'COMMITS_SELECTED'
FILES_SELECTED = 'FILES_SELECTED'


class DiffSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    """Implements the diff syntax highlighting"""

    INITIAL_STATE = -1
    DIFFSTAT_STATE = 0
    DIFF_FILE_HEADER_STATE = 1
    DIFF_STATE = 2
    SUBMODULE_STATE = 3

    DIFF_FILE_HEADER_START_RGX = re.compile(r'diff --git a/.* b/.*')
    DIFF_HUNK_HEADER_RGX = re.compile(r'(?:@@ -[0-9,]+ \+[0-9,]+ @@)|'
                                      r'(?:@@@ (?:-[0-9,]+ ){2}\+[0-9,]+ @@@)')
    BAD_WHITESPACE_RGX = re.compile(r'\s+$')

    def __init__(self, doc, whitespace=True):
        QtGui.QSyntaxHighlighter.__init__(self, doc)
        self.whitespace = whitespace
        self.enabled = True

        cfg = gitcfg.current()
        self.color_text = RGB(cfg.color('text', '030303'))
        self.color_add = RGB(cfg.color('add', 'd2ffe4'))
        self.color_remove = RGB(cfg.color('remove', 'fee0e4'))
        self.color_header = RGB(cfg.color('header', 'bbbbbb'))

        self.diff_header_fmt = make_format(fg=self.color_header)
        self.bold_diff_header_fmt = make_format(fg=self.color_header, bold=True)

        self.diff_add_fmt = make_format(fg=self.color_text,
                                        bg=self.color_add)
        self.diff_remove_fmt = make_format(fg=self.color_text,
                                           bg=self.color_remove)
        self.bad_whitespace_fmt = make_format(bg=Qt.red)

    def set_enabled(self, enabled):
        self.enabled = enabled

    def highlightBlock(self, text):
        if not self.enabled or not text:
            return
        state = self.previousBlockState()
        if state == self.INITIAL_STATE:
            if text.startswith('Submodule '):
                state = self.SUBMODULE_STATE
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


class DiffTextEdit(VimMonoTextView):

    def __init__(self, parent, whitespace=True):
        VimMonoTextView.__init__(self, parent)
        # Diff/patch syntax highlighter
        self.highlighter = DiffSyntaxHighlighter(self.document(),
                                                 whitespace=whitespace)


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
        DiffTextEdit.__init__(self, parent)
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

        self.diffopts_button = create_action_button(
            tooltip=N_('Diff Options'), icon=icons.configure())
        self.diffopts_menu = create_menu(N_('Diff Options'),
                                         self.diffopts_button)

        self.diffopts_menu.addAction(self.diff_ignore_space_at_eol_action)
        self.diffopts_menu.addAction(self.diff_ignore_space_change_action)
        self.diffopts_menu.addAction(self.diff_ignore_all_space_action)
        self.diffopts_menu.addAction(self.diff_function_context_action)
        self.diffopts_button.setMenu(self.diffopts_menu)
        qtutils.hide_button_menu_indicator(self.diffopts_button)

        titlebar.add_corner_widget(self.diffopts_button)

        self.action_apply_selection = qtutils.add_action(
            self, 'Apply', self.apply_selection, hotkeys.STAGE_DIFF)

        self.action_revert_selection = qtutils.add_action(
            self, 'Revert', self.revert_selection, hotkeys.REVERT)
        self.action_revert_selection.setIcon(icons.undo())

        self.launch_editor = actions.launch_editor(self, 'Return', 'Enter')
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

        self.diff_text_changed.connect(self.setPlainText)

    def refresh(self):
        enabled = False
        s = self.selection_model.selection()
        if s.modified and self.model.stageable():
            if s.modified[0] in self.model.submodules:
                pass
            elif s.modified[0] not in main.model().unstaged_deleted:
                enabled = True
        self.action_revert_selection.setEnabled(enabled)

    def _update_diff_opts(self):
        space_at_eol = self.diff_ignore_space_at_eol_action.isChecked()
        space_change = self.diff_ignore_space_change_action.isChecked()
        all_space = self.diff_ignore_all_space_action.isChecked()
        function_context = self.diff_function_context_action.isChecked()

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

    def wheelEvent(self, event):
        ev = event
        if event.modifiers() & Qt.ControlModifier:
            event.accept()
            # Intercept the Control modifier to not resize the text
            # when doing control+mousewheel
            if hasattr(event, 'angleDelta'):
                angle = event.angleDelta()
                if abs(angle.x()) > abs(angle.y()):
                    delta = angle.x()
                    orientation = Qt.Horizontal
                else:
                    delta = angle.y()
                    orientation = Qt.Vertical

                ev = QtGui.QWheelEvent(event.pos(),
                                       event.globalPos(),
                                       event.pixelDelta(),
                                       event.angleDelta(),
                                       delta,
                                       orientation,
                                       Qt.NoButton,
                                       Qt.NoModifier)
            else:
                ev = QtGui.QWheelEvent(event.pos(),
                                       event.delta(),
                                       Qt.NoButton,
                                       Qt.NoModifier,
                                       event.orientation())

        return DiffTextEdit.wheelEvent(self, ev)

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
        selection_end = cursor.selectionEnd()

        line_start = 0
        for line_idx, line in enumerate(self.toPlainText().split('\n')):
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

    def __init__(self, notifier, parent):
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

        self.sha1_label = TextLabel()
        self.sha1_label.setTextFormat(Qt.PlainText)
        self.sha1_label.setSizePolicy(policy)
        self.sha1_label.setAlignment(Qt.AlignTop)
        self.sha1_label.elide()

        self.diff = DiffTextEdit(self, whitespace=False)

        self.info_layout = qtutils.vbox(defs.no_margin, defs.no_spacing,
                                        self.author_label, self.summary_label,
                                        self.sha1_label)

        self.logo_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                        self.gravatar_label, self.info_layout)
        self.logo_layout.setContentsMargins(defs.margin, 0, defs.margin, 0)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.logo_layout, self.diff)
        self.setLayout(self.main_layout)

        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)
        notifier.add_observer(FILES_SELECTED, self.files_selected)

    def set_diff_sha1(self, sha1, filename=None):
        self.diff.setText('+++ ' + N_('Loading...'))
        task = DiffInfoTask(sha1, filename, self)
        task.connect(self.diff.setText)
        self.runtask.start(task)

    def commits_selected(self, commits):
        if len(commits) != 1:
            return
        commit = commits[0]
        self.sha1 = commit.sha1

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
        self.sha1_label.set_text(self.sha1)

        self.set_diff_sha1(self.sha1)
        self.gravatar_label.set_email(email)

    def files_selected(self, filenames):
        if not filenames:
            return
        self.set_diff_sha1(self.sha1, filenames[0])


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

    def __init__(self, sha1, filename, parent):
        qtutils.Task.__init__(self, parent)
        self.sha1 = sha1
        self.filename = filename

    def task(self):
        return gitcmds.diff_info(self.sha1, filename=self.filename)
