from __future__ import division, absolute_import, unicode_literals
import re

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import actions
from cola import cmds
from cola import core
from cola import gitcmds
from cola import gitcfg
from cola import textwrap
from cola import qtutils
from cola.cmds import Interaction
from cola.gitcmds import commit_message_path
from cola.i18n import N_
from cola.models import dag
from cola.models import prefs
from cola.models import selection
from cola.widgets import defs
from cola.widgets.selectcommits import select_commits
from cola.widgets.spellcheck import SpellCheckTextEdit
from cola.widgets.text import HintedLineEdit
from cola.compat import ustr


class CommitMessageEditor(QtGui.QWidget):
    def __init__(self, model, parent):
        QtGui.QWidget.__init__(self, parent)

        self.model = model
        self.spellcheck_initialized = False

        self._linebreak = None
        self._textwidth = None
        self._tabwidth = None

        # Actions
        self.signoff_action = qtutils.add_action(self, cmds.SignOff.name(),
                                                 cmds.run(cmds.SignOff),
                                                 cmds.SignOff.SHORTCUT)
        self.signoff_action.setToolTip(N_('Sign off on this commit'))

        self.commit_action = qtutils.add_action(self,
                                                N_('Commit@@verb'),
                                                self.commit,
                                                cmds.Commit.SHORTCUT)
        self.commit_action.setToolTip(N_('Commit staged changes'))
        self.clear_action = qtutils.add_action(self, N_('Clear...'), self.clear)

        self.launch_editor = actions.launch_editor(self)
        self.launch_difftool = actions.launch_difftool(self)
        self.stage_or_unstage = actions.stage_or_unstage(self)

        self.move_up = actions.move_up(self)
        self.move_down = actions.move_down(self)

        # Widgets
        self.summary = CommitSummaryLineEdit()
        self.summary.setMinimumHeight(defs.tool_button_height)
        self.summary.extra_actions.append(self.clear_action)
        self.summary.extra_actions.append(None)
        self.summary.extra_actions.append(self.signoff_action)
        self.summary.extra_actions.append(self.commit_action)
        self.summary.extra_actions.append(None)
        self.summary.extra_actions.append(self.launch_editor)
        self.summary.extra_actions.append(self.launch_difftool)
        self.summary.extra_actions.append(self.stage_or_unstage)
        self.summary.extra_actions.append(None)
        self.summary.extra_actions.append(self.move_up)
        self.summary.extra_actions.append(self.move_down)

        self.description = CommitMessageTextEdit()
        self.description.extra_actions.append(self.clear_action)
        self.description.extra_actions.append(None)
        self.description.extra_actions.append(self.signoff_action)
        self.description.extra_actions.append(self.commit_action)
        self.description.extra_actions.append(None)
        self.description.extra_actions.append(self.launch_editor)
        self.description.extra_actions.append(self.launch_difftool)
        self.description.extra_actions.append(self.stage_or_unstage)
        self.description.extra_actions.append(None)
        self.description.extra_actions.append(self.move_up)
        self.description.extra_actions.append(self.move_down)

        commit_button_tooltip = N_('Commit staged changes\n'
                                   'Shortcut: Ctrl+Enter')
        self.commit_button = qtutils.create_toolbutton(
                text=N_('Commit@@verb'), tooltip=commit_button_tooltip,
                icon=qtutils.save_icon())

        self.actions_menu = QtGui.QMenu()
        self.actions_button = qtutils.create_toolbutton(
                icon=qtutils.options_icon(), tooltip=N_('Actions...'))
        self.actions_button.setMenu(self.actions_menu)
        self.actions_button.setPopupMode(QtGui.QToolButton.InstantPopup)
        qtutils.hide_button_menu_indicator(self.actions_button)

        self.actions_menu.addAction(self.signoff_action)
        self.actions_menu.addAction(self.commit_action)
        self.actions_menu.addSeparator()

        # Amend checkbox
        self.amend_action = self.actions_menu.addAction(
                N_('Amend Last Commit'))
        self.amend_action.setCheckable(True)
        self.amend_action.setShortcut(cmds.AmendMode.SHORTCUT)
        self.amend_action.setShortcutContext(Qt.ApplicationShortcut)

        # Bypass hooks
        self.bypass_commit_hooks_action = self.actions_menu.addAction(
                N_('Bypass Commit Hooks'))
        self.bypass_commit_hooks_action.setCheckable(True)
        self.bypass_commit_hooks_action.setChecked(False)

        # Sign commits
        cfg = gitcfg.current()
        self.sign_action = self.actions_menu.addAction(
                N_('Create Signed Commit'))
        self.sign_action.setCheckable(True)
        self.sign_action.setChecked(cfg.get('cola.signcommits', False))

        # Spell checker
        self.check_spelling_action = self.actions_menu.addAction(
                N_('Check Spelling'))
        self.check_spelling_action.setCheckable(True)
        self.check_spelling_action.setChecked(False)

        # Line wrapping
        self.autowrap_action = self.actions_menu.addAction(
                N_('Auto-Wrap Lines'))
        self.autowrap_action.setCheckable(True)
        self.autowrap_action.setChecked(prefs.linebreak())

        # Commit message
        self.actions_menu.addSeparator()
        self.load_commitmsg_menu = self.actions_menu.addMenu(
                N_('Load Previous Commit Message'))
        self.connect(self.load_commitmsg_menu, SIGNAL('aboutToShow()'),
                     self.build_commitmsg_menu)

        self.fixup_commit_menu = self.actions_menu.addMenu(
                N_('Fixup Previous Commit'))
        self.connect(self.fixup_commit_menu, SIGNAL('aboutToShow()'),
                     self.build_fixup_menu)

        self.toplayout = qtutils.hbox(defs.no_margin, defs.spacing,
                                      self.actions_button, self.summary,
                                      self.commit_button)
        self.toplayout.setContentsMargins(defs.margin, defs.no_margin,
                                          defs.no_margin, defs.no_margin)

        self.mainlayout = qtutils.vbox(defs.no_margin, defs.spacing,
                                       self.toplayout, self.description)
        self.setLayout(self.mainlayout)

        qtutils.connect_button(self.commit_button, self.commit)

        # Broadcast the amend mode
        qtutils.connect_action_bool(self.amend_action, cmds.run(cmds.AmendMode))
        qtutils.connect_action_bool(self.check_spelling_action,
                                    self.toggle_check_spelling)

        # Handle the one-off autowrapping
        qtutils.connect_action_bool(self.autowrap_action, self.set_linebreak)

        qtutils.add_action(self.summary, N_('Move Down'),
                           self.focus_description,
                           Qt.Key_Return, Qt.Key_Enter)

        qtutils.add_action(self.summary, N_('Move Down'),
                           self.summary_cursor_down,
                           Qt.Key_Down)

        self.selection_model = selection_model = selection.selection_model()
        selection_model.add_observer(selection_model.message_selection_changed,
                                     self._update)

        self.model.add_observer(self.model.message_commit_message_changed,
                                self._set_commit_message)

        self.connect(self, SIGNAL('set_commit_message(PyQt_PyObject)'),
                     self.set_commit_message, Qt.QueuedConnection)

        self.connect(self.summary, SIGNAL('cursorPosition(int,int)'),
                     self.emit_position)

        self.connect(self.description, SIGNAL('cursorPosition(int,int)'),
                     # description starts at line 2
                     lambda row, col: self.emit_position(row + 2, col))

        # Keep model informed of changes
        self.connect(self.summary, SIGNAL('textChanged(QString)'),
                     self.commit_summary_changed)

        self.connect(self.description, SIGNAL('textChanged()'),
                     self.commit_message_changed)

        self.connect(self.description, SIGNAL('leave()'),
                     self.focus_summary)

        self.connect(self, SIGNAL('update()'),
                     self._update_callback, Qt.QueuedConnection)

        self.setFont(qtutils.diff_font())

        self.summary.hint.enable(True)
        self.description.hint.enable(True)

        self.commit_button.setEnabled(False)
        self.commit_action.setEnabled(False)

        self.setFocusProxy(self.summary)

        self.set_tabwidth(prefs.tabwidth())
        self.set_textwidth(prefs.textwidth())
        self.set_linebreak(prefs.linebreak())

        # Loading message
        commit_msg = ''
        commit_msg_path = commit_message_path()
        if commit_msg_path:
            commit_msg = core.read(commit_msg_path)
        self.set_commit_message(commit_msg)

        # Allow tab to jump from the summary to the description
        self.setTabOrder(self.summary, self.description)

    def _update(self):
        self.emit(SIGNAL('update()'))

    def _update_callback(self):
        enabled = self.model.stageable() or self.model.unstageable()
        if self.model.stageable():
            text = N_('Stage')
        else:
            text = N_('Unstage')
        self.stage_or_unstage.setEnabled(enabled)
        self.stage_or_unstage.setText(text)

    def set_initial_size(self):
        self.setMaximumHeight(133)
        QtCore.QTimer.singleShot(1, self.restore_size)

    def restore_size(self):
        self.setMaximumHeight(2 ** 13)

    def focus_summary(self):
        self.summary.setFocus()

    def focus_description(self):
        self.description.setFocus()

    def summary_cursor_down(self):
        """Handle the down key in the summary field

        If the cursor is at the end of the line then focus the description.
        Otherwise, move the cursor to the end of the line so that a
        subsequence "down" press moves to the end of the line.

        """
        cur_position = self.summary.cursorPosition()
        end_position = len(self.summary.value())
        if cur_position == end_position:
            self.focus_description()
        else:
            self.summary.setCursorPosition(end_position)

    def commit_message(self, raw=True):
        """Return the commit message as a unicode string"""
        summary = self.summary.value()
        if raw:
            description = self.description.value()
        else:
            description = self.formatted_description()
        if summary and description:
            return summary + '\n\n' + description
        elif summary:
            return summary
        elif description:
            return '\n\n' + description
        else:
            return ''

    def formatted_description(self):
        text = self.description.value()
        if not self._linebreak:
            return text
        return textwrap.word_wrap(text, self._tabwidth, self._textwidth)

    def commit_summary_changed(self, value):
        """Respond to changes to the `summary` field

        Newlines can enter the `summary` field when pasting, which is
        undesirable.  Break the pasted value apart into the separate
        (summary, description) values and move the description over to the
        "extended description" field.

        """
        value = ustr(value)
        if '\n' in value:
            summary, description = value.split('\n', 1)
            description = description.lstrip('\n')
            cur_description = self.description.value()
            if cur_description:
                description = description + '\n' + cur_description
            # this callback is triggered by changing `summary`
            # so disable signals for `summary` only.
            self.summary.set_value(summary, block=True)
            self.description.set_value(description)
        self.commit_message_changed()

    def commit_message_changed(self, value=None):
        """Update the model when values change"""
        message = self.commit_message()
        self.model.set_commitmsg(message, notify=False)
        self.refresh_palettes()
        self.update_actions()

    def clear(self):
        if not qtutils.confirm(
                N_('Clear commit message?'),
                N_('The commit message will be cleared.'),
                N_('This cannot be undone.  Clear commit message?'),
                N_('Clear commit message'),
                default=True,
                icon=qtutils.discard_icon()):
            return
        self.model.set_commitmsg('')

    def update_actions(self):
        commit_enabled = bool(self.summary.value())
        self.commit_button.setEnabled(commit_enabled)
        self.commit_action.setEnabled(commit_enabled)

    def refresh_palettes(self):
        """Update the color palette for the hint text"""
        self.summary.hint.refresh()
        self.description.hint.refresh()

    def _set_commit_message(self, message):
        self.emit(SIGNAL('set_commit_message(PyQt_PyObject)'), message)

    def set_commit_message(self, message):
        """Set the commit message to match the observed model"""
        # Parse the "summary" and "description" fields
        umsg = ustr(message)
        lines = umsg.splitlines()

        num_lines = len(lines)

        if num_lines == 0:
            # Message is empty
            summary = ''
            description = ''

        elif num_lines == 1:
            # Message has a summary only
            summary = lines[0]
            description = ''

        elif num_lines == 2:
            # Message has two lines; this is not a common case
            summary = lines[0]
            description = lines[1]

        else:
            # Summary and several description lines
            summary = lines[0]
            if lines[1]:
                # We usually skip this line but check just in case
                description_lines = lines[1:]
            else:
                description_lines = lines[2:]
            description = '\n'.join(description_lines)

        focus_summary = not summary
        focus_description = not description

        # Update summary
        if not summary and not self.summary.hasFocus():
            self.summary.hint.enable(True)
        else:
            self.summary.set_value(summary, block=True)

        # Update description
        if not description and not self.description.hasFocus():
            self.description.hint.enable(True)
        else:
            self.description.set_value(description, block=True)

        # Update text color
        self.refresh_palettes()

        # Focus the empty summary or description
        if focus_summary:
            self.summary.setFocus()
        elif focus_description:
            self.description.setFocus()
        else:
            self.summary.cursor_position.emit()

        self.update_actions()

    def set_tabwidth(self, width):
        self._tabwidth = width
        self.description.set_tabwidth(width)

    def set_textwidth(self, width):
        self._textwidth = width
        self.description.set_textwidth(width)

    def set_linebreak(self, brk):
        self._linebreak = brk
        self.description.set_linebreak(brk)
        blocksignals = self.autowrap_action.blockSignals(True)
        self.autowrap_action.setChecked(brk)
        self.autowrap_action.blockSignals(blocksignals)

    def setFont(self, font):
        """Pass the setFont() calls down to the text widgets"""
        self.summary.setFont(font)
        self.description.setFont(font)

    def set_mode(self, mode):
        can_amend = not self.model.is_merging
        checked = (mode == self.model.mode_amend)
        blocksignals = self.amend_action.blockSignals(True)
        self.amend_action.setEnabled(can_amend)
        self.amend_action.setChecked(checked)
        self.amend_action.blockSignals(blocksignals)

    def emit_position(self, row, col):
        self.emit(SIGNAL('cursorPosition(int,int)'), row, col)

    def commit(self):
        """Attempt to create a commit from the index and commit message."""
        if not bool(self.summary.value()):
            # Describe a good commit message
            error_msg = N_(''
                'Please supply a commit message.\n\n'
                'A good commit message has the following format:\n\n'
                '- First line: Describe in one sentence what you did.\n'
                '- Second line: Blank\n'
                '- Remaining lines: Describe why this change is good.\n')
            Interaction.log(error_msg)
            Interaction.information(N_('Missing Commit Message'), error_msg)
            return

        msg = self.commit_message(raw=False)

        if not self.model.staged:
            error_msg = N_(''
                'No changes to commit.\n\n'
                'You must stage at least 1 file before you can commit.')
            if self.model.modified:
                informative_text = N_('Would you like to stage and '
                                      'commit all modified files?')
                if not qtutils.confirm(
                        N_('Stage and commit?'),
                        error_msg, informative_text,
                        N_('Stage and Commit'),
                        default=True,
                        icon=qtutils.save_icon()):
                    return
            else:
                Interaction.information(N_('Nothing to commit'), error_msg)
                return
            cmds.do(cmds.StageModified)

        # Warn that amending published commits is generally bad
        amend = self.amend_action.isChecked()
        if (amend and self.model.is_commit_published() and
            not qtutils.confirm(
                        N_('Rewrite Published Commit?'),
                        N_('This commit has already been published.\n'
                           'This operation will rewrite published history.\n'
                           'You probably don\'t want to do this.'),
                        N_('Amend the published commit?'),
                        N_('Amend Commit'),
                        default=False, icon=qtutils.save_icon())):
            return
        no_verify = self.bypass_commit_hooks_action.isChecked()
        sign = self.sign_action.isChecked()
        status, out, err = cmds.do(cmds.Commit, amend, msg, sign,
                                   no_verify=no_verify)
        if status != 0:
            Interaction.critical(N_('Commit failed'),
                                 N_('"git commit" returned exit code %s') %
                                    (status,),
                                 out + err)

    def build_fixup_menu(self):
        self.build_commits_menu(cmds.LoadFixupMessage,
                                self.fixup_commit_menu,
                                self.choose_fixup_commit,
                                prefix='fixup! ')

    def build_commitmsg_menu(self):
        self.build_commits_menu(cmds.LoadCommitMessageFromSHA1,
                                self.load_commitmsg_menu,
                                self.choose_commit_message)

    def build_commits_menu(self, cmd, menu, chooser, prefix=''):
        ctx = dag.DAG('HEAD', 6)
        commits = dag.RepoReader(ctx)

        menu_commits = []
        for idx, c in enumerate(commits):
            menu_commits.insert(0, c)
            if idx > 5:
                continue

        menu.clear()
        for c in menu_commits:
            menu.addAction(prefix + c.summary, cmds.run(cmd, c.sha1))

        if len(commits) == 6:
            menu.addSeparator()
            menu.addAction(N_('More...'), chooser)


    def choose_commit(self, cmd):
        revs, summaries = gitcmds.log_helper()
        sha1s = select_commits(N_('Select Commit'), revs, summaries,
                               multiselect=False)
        if not sha1s:
            return
        sha1 = sha1s[0]
        cmds.do(cmd, sha1)

    def choose_commit_message(self):
        self.choose_commit(cmds.LoadCommitMessageFromSHA1)

    def choose_fixup_commit(self):
        self.choose_commit(cmds.LoadFixupMessage)

    def toggle_check_spelling(self, enabled):
        spellcheck = self.description.spellcheck

        if enabled and not self.spellcheck_initialized:
            # Add our name to the dictionary
            self.spellcheck_initialized = True
            cfg = gitcfg.current()
            user_name = cfg.get('user.name')
            if user_name:
                for part in user_name.split():
                    spellcheck.add_word(part)

            # Add our email address to the dictionary
            user_email = cfg.get('user.email')
            if user_email:
                for part in user_email.split('@'):
                    for elt in part.split('.'):
                        spellcheck.add_word(elt)

            # git jargon
            spellcheck.add_word('Acked')
            spellcheck.add_word('Signed')
            spellcheck.add_word('Closes')
            spellcheck.add_word('Fixes')

        self.description.highlighter.enable(enabled)


class CommitSummaryLineEdit(HintedLineEdit):

    def __init__(self, parent=None):
        hint = N_('Commit summary')
        HintedLineEdit.__init__(self, hint, parent)
        self.extra_actions = []

        comment_char = prefs.comment_char()
        re_comment_char = re.escape(comment_char)
        regex = QtCore.QRegExp(r'^[^%s \t].*' % re_comment_char)
        self._validator = QtGui.QRegExpValidator(regex, self)
        self.setValidator(self._validator)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        if self.extra_actions:
            menu.addSeparator()
        for action in self.extra_actions:
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)
        menu.exec_(self.mapToGlobal(event.pos()))


class CommitMessageTextEdit(SpellCheckTextEdit):

    def __init__(self, parent=None):
        hint = N_('Extended description...')
        SpellCheckTextEdit.__init__(self, hint, parent)
        self.extra_actions = []

        self.action_emit_leave = qtutils.add_action(self,
                'Shift Tab', self.emit_leave, 'Shift+Tab')

    def contextMenuEvent(self, event):
        menu, spell_menu = self.context_menu()
        if self.extra_actions:
            menu.addSeparator()
        for action in self.extra_actions:
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            position = cursor.position()
            if position == 0:
                # The cursor is at the beginning of the line.
                # If we have selection then simply reset the cursor.
                # Otherwise, emit a signal so that the parent can
                # change focus.
                if cursor.hasSelection():
                    cursor.setPosition(0)
                    self.setTextCursor(cursor)
                else:
                    self.emit_leave()
                event.accept()
                return
            text_before = ustr(self.toPlainText())[:position]
            lines_before = text_before.count('\n')
            if lines_before == 0:
                # If we're on the first line, but not at the
                # beginning, then move the cursor to the beginning
                # of the line.
                if event.modifiers() & Qt.ShiftModifier:
                    mode = QtGui.QTextCursor.KeepAnchor
                else:
                    mode = QtGui.QTextCursor.MoveAnchor
                cursor.setPosition(0, mode)
                self.setTextCursor(cursor)
                event.accept()
                return
        elif event.key() == Qt.Key_Down:
            cursor = self.textCursor()
            position = cursor.position()
            all_text = ustr(self.toPlainText())
            text_after = all_text[position:]
            lines_after = text_after.count('\n')
            if lines_after == 0:
                if event.modifiers() & Qt.ShiftModifier:
                    mode = QtGui.QTextCursor.KeepAnchor
                else:
                    mode = QtGui.QTextCursor.MoveAnchor
                cursor.setPosition(len(all_text), mode)
                self.setTextCursor(cursor)
                event.accept()
                return
        SpellCheckTextEdit.keyPressEvent(self, event)

    def emit_leave(self):
        self.emit(SIGNAL('leave()'))

    def setFont(self, font):
        SpellCheckTextEdit.setFont(self, font)
        fm = self.fontMetrics()
        self.setMinimumSize(QtCore.QSize(1, fm.height() * 2))
