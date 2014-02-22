from __future__ import division, absolute_import

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import gitcmds
from cola import gitcfg
from cola import textwrap
from cola.cmds import Interaction
from cola.gitcmds import commit_message_path
from cola.i18n import N_
from cola.models.dag import DAG
from cola.models.dag import RepoReader
from cola.models.prefs import tabwidth
from cola.models.prefs import textwidth
from cola.models.prefs import linebreak
from cola.qtutils import add_action
from cola.qtutils import confirm
from cola.qtutils import connect_action_bool
from cola.qtutils import connect_button
from cola.qtutils import create_toolbutton
from cola.qtutils import diff_font
from cola.qtutils import hide_button_menu_indicator
from cola.qtutils import options_icon
from cola.qtutils import save_icon
from cola.widgets import defs
from cola.widgets.selectcommits import select_commits
from cola.widgets.spellcheck import SpellCheckTextEdit
from cola.widgets.text import HintedLineEdit


class CommitMessageEditor(QtGui.QWidget):
    def __init__(self, model, parent):
        QtGui.QWidget.__init__(self, parent)

        self.model = model
        self.notifying = False
        self.spellcheck_initialized = False

        self._linebreak = None
        self._textwidth = None
        self._tabwidth = None

        # Actions
        self.signoff_action = add_action(self, cmds.SignOff.name(),
                                         cmds.run(cmds.SignOff),
                                         cmds.SignOff.SHORTCUT)
        self.signoff_action.setToolTip(N_('Sign off on this commit'))

        self.commit_action = add_action(self,
                                        N_('Commit@@verb'),
                                        self.commit,
                                        cmds.Commit.SHORTCUT)
        self.commit_action.setToolTip(N_('Commit staged changes'))

        # Widgets
        self.summary = CommitSummaryLineEdit()
        self.summary.extra_actions.append(self.signoff_action)
        self.summary.extra_actions.append(self.commit_action)

        self.description = CommitMessageTextEdit()
        self.description.extra_actions.append(self.signoff_action)
        self.description.extra_actions.append(self.commit_action)

        commit_button_tooltip = N_('Commit staged changes\n'
                                   'Shortcut: Ctrl+Enter')
        self.commit_button = create_toolbutton(text=N_('Commit@@verb'),
                                               tooltip=commit_button_tooltip,
                                               icon=save_icon())

        self.actions_menu = QtGui.QMenu()
        self.actions_button = create_toolbutton(icon=options_icon(),
                                                tooltip=N_('Actions...'))
        self.actions_button.setMenu(self.actions_menu)
        self.actions_button.setPopupMode(QtGui.QToolButton.InstantPopup)
        hide_button_menu_indicator(self.actions_button)

        self.actions_menu.addAction(self.signoff_action)
        self.actions_menu.addAction(self.commit_action)
        self.actions_menu.addSeparator()

        # Amend checkbox
        self.amend_action = self.actions_menu.addAction(
                N_('Amend Last Commit'))
        self.amend_action.setCheckable(True)
        self.amend_action.setShortcut(cmds.AmendMode.SHORTCUT)
        self.amend_action.setShortcutContext(Qt.ApplicationShortcut)

        # Spell checker
        self.check_spelling_action = self.actions_menu.addAction(
                N_('Check Spelling'))
        self.check_spelling_action.setCheckable(True)
        self.check_spelling_action.setChecked(False)

        # Line wrapping
        self.autowrap_action = self.actions_menu.addAction(
                N_('Auto-Wrap Lines'))
        self.autowrap_action.setCheckable(True)
        self.autowrap_action.setChecked(linebreak())

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

        self.toplayout = QtGui.QHBoxLayout()
        self.toplayout.setMargin(0)
        self.toplayout.setSpacing(defs.spacing)
        self.toplayout.addWidget(self.actions_button)
        self.toplayout.addWidget(self.summary)
        self.toplayout.addWidget(self.commit_button)

        self.mainlayout = QtGui.QVBoxLayout()
        self.mainlayout.setMargin(defs.margin)
        self.mainlayout.setSpacing(defs.spacing)
        self.mainlayout.addLayout(self.toplayout)
        self.mainlayout.addWidget(self.description)
        self.setLayout(self.mainlayout)

        connect_button(self.commit_button, self.commit)

        # Broadcast the amend mode
        connect_action_bool(self.amend_action, cmds.run(cmds.AmendMode))
        connect_action_bool(self.check_spelling_action,
                            self.toggle_check_spelling)

        # Handle the one-off autowrapping
        connect_action_bool(self.autowrap_action, self.set_linebreak)

        add_action(self.summary, N_('Move Down'), self.focus_description,
                Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter)

        self.model.add_observer(self.model.message_commit_message_changed,
                                self.set_commit_message)

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

        self.setFont(diff_font())

        self.summary.enable_hint(True)
        self.description.enable_hint(True)

        self.commit_button.setEnabled(False)
        self.commit_action.setEnabled(False)

        self.setFocusProxy(self.summary)

        self.set_tabwidth(tabwidth())
        self.set_textwidth(textwidth())
        self.set_linebreak(linebreak())

        # Loading message
        commit_msg = ''
        commit_msg_path = commit_message_path()
        if commit_msg_path:
            commit_msg = core.read(commit_msg_path)
        self.set_commit_message(commit_msg)

        # Allow tab to jump from the summary to the description
        self.setTabOrder(self.summary, self.description)

    def set_initial_size(self):
        self.setMaximumHeight(133)
        QtCore.QTimer.singleShot(1, self.restore_size)

    def restore_size(self):
        self.setMaximumHeight(2 ** 13)

    def focus_summary(self):
        self.summary.setFocus()

    def focus_description(self):
        self.description.setFocus()

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
        value = unicode(value)
        if '\n' in value:
            summary, description = value.split('\n', 1)
            description = description.lstrip('\n')
            cur_description = self.description.value()
            if cur_description:
                description = description + '\n' + cur_description
            # this callback is triggered by changing `summary`
            # so disable signals for `summary` only.
            self.summary.blockSignals(True)
            self.summary.set_value(summary)
            self.summary.blockSignals(False)
            self.description.set_value(description)
        self.commit_message_changed()

    def commit_message_changed(self, value=None):
        """Update the model when values change"""
        self.notifying = True
        message = self.commit_message()
        self.model.set_commitmsg(message)
        self.refresh_palettes()
        self.notifying = False
        self.update_actions()

    def update_actions(self):
        commit_enabled = bool(self.summary.value())
        self.commit_button.setEnabled(commit_enabled)
        self.commit_action.setEnabled(commit_enabled)

    def refresh_palettes(self):
        """Update the color palette for the hint text"""
        self.summary.refresh_palette()
        self.description.refresh_palette()

    def set_commit_message(self, message):
        """Set the commit message to match the observed model"""
        if self.notifying:
            # Calling self.model.set_commitmsg(message) causes us to
            # loop around so break the loop
            return

        # Parse the "summary" and "description" fields
        umsg = unicode(message)
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
            summary = self.summary.hint()

        blocksignals = self.summary.blockSignals(True)
        self.summary.setText(summary)
        self.summary.setCursorPosition(0)
        self.summary.blockSignals(blocksignals)

        # Update description
        if not description and not self.description.hasFocus():
            description = self.description.hint()

        blocksignals = self.description.blockSignals(True)
        self.description.setPlainText(description)
        self.description.blockSignals(blocksignals)

        # Update text color
        self.refresh_palettes()

        # Focus the empty summary or description
        if focus_summary:
            self.summary.setFocus()
            self.summary.emit_position()
        elif focus_description:
            self.description.setFocus()
            self.description.emit_position()
        else:
            self.summary.emit_position()

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
                if not confirm(N_('Stage and commit?'),
                               error_msg,
                               informative_text,
                               N_('Stage and Commit'),
                               default=True,
                               icon=save_icon()):
                    return
            else:
                Interaction.information(N_('Nothing to commit'), error_msg)
                return
            cmds.do(cmds.StageModified)

        # Warn that amending published commits is generally bad
        amend = self.amend_action.isChecked()
        if (amend and self.model.is_commit_published() and
            not confirm(N_('Rewrite Published Commit?'),
                        N_('This commit has already been published.\n'
                           'This operation will rewrite published history.\n'
                           'You probably don\'t want to do this.'),
                        N_('Amend the published commit?'),
                        N_('Amend Commit'),
                        default=False, icon=save_icon())):
            return
        status, out, err = cmds.do(cmds.Commit, amend, msg)
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
        dag = DAG('HEAD', 6)
        commits = RepoReader(dag)

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
            cfg = gitcfg.instance()
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

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        if self.extra_actions:
            menu.addSeparator()
        for action in self.extra_actions:
            menu.addAction(action)
        menu.exec_(self.mapToGlobal(event.pos()))


class CommitMessageTextEdit(SpellCheckTextEdit):

    def __init__(self, parent=None):
        hint = N_('Extended description...')
        SpellCheckTextEdit.__init__(self, hint, parent)
        self.extra_actions = []

        self.action_emit_leave = add_action(self,
                'Shift Tab', self.emit_leave, 'Shift+tab')

    def contextMenuEvent(self, event):
        menu, spell_menu = self.context_menu()
        if self.extra_actions:
            menu.addSeparator()
        for action in self.extra_actions:
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
            text_before = unicode(self.toPlainText())[:position]
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
            all_text = unicode(self.toPlainText())
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
