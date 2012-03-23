from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import gitcmds
from cola import signals
from cola.qt import create_toolbutton
from cola.qtutils import add_action
from cola.qtutils import confirm
from cola.qtutils import connect_action
from cola.qtutils import connect_action_bool
from cola.qtutils import connect_button
from cola.qtutils import emit
from cola.qtutils import log
from cola.qtutils import relay_signal
from cola.qtutils import options_icon
from cola.qtutils import save_icon
from cola.qtutils import tr
from cola.widgets import defs
from cola.prefs import diff_font
from cola.dag.model import DAG
from cola.dag.model import RepoReader
from cola.widgets.selectcommits import select_commits
from cola.widgets.text import HintedLineEdit
from cola.widgets.text import HintedTextEdit


class CommitMessageEditor(QtGui.QWidget):
    def __init__(self, model, parent):
        QtGui.QWidget.__init__(self, parent)

        self.model = model
        self.notifying = False

        self.summary = CommitSummaryLineEdit()
        self.description = CommitMessageTextEdit()

        commit_button_tooltip = 'Commit staged changes\nShortcut: Ctrl+Enter'
        self.commit_button = create_toolbutton(text='Commit@@verb',
                                               tooltip=commit_button_tooltip,
                                               icon=save_icon())

        self.actions_menu = QtGui.QMenu()
        self.actions_button = create_toolbutton(icon=options_icon(),
                                                tooltip='Actions...')
        self.actions_button.setMenu(self.actions_menu)
        self.actions_button.setPopupMode(QtGui.QToolButton.InstantPopup)

        # Amend checkbox
        self.signoff_action = self.actions_menu.addAction(tr('Sign Off'))
        self.signoff_action.setToolTip('Sign off on this commit')
        self.signoff_action.setShortcut('Ctrl+i')

        self.commit_action = self.actions_menu.addAction(tr('Commit@@verb'))
        self.commit_action.setToolTip(tr('Commit staged changes'))
        self.commit_action.setShortcut('Ctrl+Return')

        self.actions_menu.addSeparator()
        self.amend_action = self.actions_menu.addAction(tr('Amend Last Commit'))
        self.amend_action.setCheckable(True)

        self.prev_commits_menu = self.actions_menu.addMenu(
                    'Load Previous Commit Message')
        self.connect(self.prev_commits_menu, SIGNAL('aboutToShow()'),
                     self.build_prev_commits_menu)

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

        relay_signal(self, self.description,
                     SIGNAL(signals.load_previous_message))

        connect_button(self.commit_button, self.commit)
        connect_action(self.commit_action, self.commit)
        connect_action(self.signoff_action, emit(self, signals.signoff))

        cola.notifier().connect(signals.amend, self.amend_action.setChecked)

        # Broadcast the amend mode
        connect_action_bool(self.amend_action, emit(self, signals.amend_mode))

        self.model.add_observer(self.model.message_commit_message_changed,
                                self.set_commit_message)

        self.connect(self.summary, SIGNAL('returnPressed()'),
                     self.focus_description)

        self.connect(self.summary, SIGNAL('downPressed()'),
                     self.focus_description)

        self.connect(self.summary, SIGNAL('cursorPosition(int,int)'),
                     self.emit_position)

        self.connect(self.description, SIGNAL('cursorPosition(int,int)'),
                     # description starts at line 2
                     lambda row, col: self.emit_position(row + 2, col))

        # Keep model informed of changes
        self.connect(self.summary, SIGNAL('textChanged(QString)'),
                     self.commit_message_changed)

        self.connect(self.description, SIGNAL('textChanged()'),
                     self.commit_message_changed)

        self.connect(self.description, SIGNAL('shiftTab()'),
                     self.focus_summary)

        self.setFont(diff_font())

        self.summary.enable_hint(True)
        self.description.enable_hint(True)

        self.commit_button.setEnabled(False)
        self.commit_action.setEnabled(False)

        self.setFocusProxy(self.summary)

        # Allow tab to jump from the summary to the description
        self.setTabOrder(self.summary, self.description)

    def focus_summary(self):
        self.summary.setFocus()

    def focus_description(self):
        self.description.setFocus()

    def commit_message(self):
        """Return the commit message as a unicode string"""
        summary = self.summary.value()
        description = self.description.value()
        if summary and description:
            return summary + u'\n\n' + description
        elif summary:
            return summary
        elif description:
            return u'\n\n' + description
        else:
            return u''

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
            summary = u''
            description = u''

        elif num_lines == 1:
            # Message has a summary only
            summary = lines[0]
            description = u''

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
            description = u'\n'.join(description_lines)

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

    def setFont(self, font):
        """Pass the setFont() calls down to the text widgets"""
        self.summary.setFont(font)
        self.description.setFont(font)

    def set_mode(self, mode):
        checked = (mode == self.model.mode_amend)
        blocksignals = self.amend_action.blockSignals(True)
        self.amend_action.setChecked(checked)
        self.amend_action.blockSignals(blocksignals)

    def emit_position(self, row, col):
        self.emit(SIGNAL('cursorPosition(int,int)'), row, col)

    def commit(self):
        """Attempt to create a commit from the index and commit message."""
        if not bool(self.summary.value()):
            # Describe a good commit message
            error_msg = tr(''
                'Please supply a commit message.\n\n'
                'A good commit message has the following format:\n\n'
                '- First line: Describe in one sentence what you did.\n'
                '- Second line: Blank\n'
                '- Remaining lines: Describe why this change is good.\n')
            log(1, error_msg)
            cola.notifier().broadcast(signals.information,
                                      'Missing Commit Message',
                                      error_msg)
            return

        msg = self.commit_message()

        if not self.model.staged:
            error_msg = tr(''
                'No changes to commit.\n\n'
                'You must stage at least 1 file before you can commit.')
            if self.model.modified:
                informative_text = tr('Would you like to stage and '
                                      'commit all modified files?')
                if not confirm('Stage and commit?',
                               error_msg,
                               informative_text,
                               'Stage and Commit',
                               default=False,
                               icon=save_icon()):
                    return
            else:
                cola.notifier().broadcast(signals.information,
                                          'Nothing to commit',
                                          error_msg)
                return
            cola.notifier().broadcast(signals.stage_modified)

        # Warn that amending published commits is generally bad
        amend = self.amend_action.isChecked()
        if (amend and self.model.is_commit_published() and
            not confirm('Rewrite Published Commit?',
                        'This commit has already been published.\n'
                        'This operation will rewrite published history.\n'
                        'You probably don\'t want to do this.',
                        'Amend the published commit?',
                        'Amend Commit',
                        default=False, icon=save_icon())):
            return
        # Perform the commit
        cola.notifier().broadcast(signals.commit, amend, msg)

    def build_prev_commits_menu(self):
        dag = DAG('HEAD', 6)
        commits = RepoReader(dag)

        menu_commits = []
        for idx, c in enumerate(commits):
            menu_commits.insert(0, c)
            if idx > 5:
                continue

        menu = self.prev_commits_menu
        menu.clear()
        for c in menu_commits:
            menu.addAction(c.summary,
                           lambda c=c: self.load_previous_message(c.sha1))

        if len(commits) == 6:
            menu.addSeparator()
            menu.addAction('More...', self.choose_commit)

    def choose_commit(self):
        revs, summaries = gitcmds.log_helper()
        sha1s = select_commits('Select Commit Message', revs, summaries,
                               multiselect=False)
        if not sha1s:
            return
        sha1 = sha1s[0]
        self.load_previous_message(sha1)

    def load_previous_message(self, sha1):
        self.emit(SIGNAL(signals.load_previous_message), sha1)


class CommitSummaryLineEdit(HintedLineEdit):
    def __init__(self, parent=None):
        hint = u'Commit summary'
        HintedLineEdit.__init__(self, hint, parent)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            position = self.cursorPosition()
            curtext = unicode(self.text())
            if position == len(curtext):
                self.emit(SIGNAL('downPressed()'))
                event.ignore()
                return
        HintedLineEdit.keyPressEvent(self, event)


class CommitMessageTextEdit(HintedTextEdit):
    def __init__(self, parent=None):
        hint = u'Extended description...'
        HintedTextEdit.__init__(self, hint, parent)
        self.setMinimumSize(QtCore.QSize(1, 1))

        self.action_emit_shift_tab = add_action(self,
                'Shift Tab', self.emit_shift_tab, 'Shift+tab')

        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.FocusIn:
            height = QtGui.QFontMetrics(self.font()).height() * 3
            height += defs.spacing * 4
            self.setMinimumSize(QtCore.QSize(1, height))

        elif event.type() == QtCore.QEvent.FocusOut:
            self.setMinimumSize(QtCore.QSize(1, 1))

        return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            position = cursor.position()
            if position == 0:
                if cursor.hasSelection():
                    cursor.setPosition(0)
                    self.setTextCursor(cursor)
                else:
                    self.emit_shift_tab()
                event.ignore()
                return
            text_before = unicode(self.toPlainText())[:position]
            lines_before = text_before.count('\n')
            if lines_before == 0:
                if event.modifiers() & Qt.ShiftModifier:
                    mode = QtGui.QTextCursor.KeepAnchor
                else:
                    mode = QtGui.QTextCursor.MoveAnchor
                cursor.setPosition(0, mode)
                self.setTextCursor(cursor)
                event.ignore()
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
                event.ignore()
                return
        HintedTextEdit.keyPressEvent(self, event)

    def emit_shift_tab(self):
        self.emit(SIGNAL('shiftTab()'))
