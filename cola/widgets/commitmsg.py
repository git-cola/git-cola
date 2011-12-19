from PyQt4 import QtGui
from PyQt4 import QtCore
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


class CommitMessageEditor(QtGui.QWidget):
    def __init__(self, model, parent):
        QtGui.QWidget.__init__(self, parent)

        self.model = model
        self.notifying = False
        self.summary_placeholder = u'Commit summary'
        self.description_placeholder = u'Extended description...'

        # Palette for normal text
        self.default_palette = QtGui.QPalette(self.palette())

        # Palette used for the placeholder text
        self.placeholder_palette = pal = QtGui.QPalette(self.palette())
        color = pal.text().color()
        color.setAlpha(128)
        pal.setColor(QtGui.QPalette.Active, QtGui.QPalette.Text, color)
        pal.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.Text, color)

        self.summary = QtGui.QLineEdit()
        self.description = CommitMessageTextEdit()

        self.commit_button = create_toolbutton(text='Commit@@verb',
                                               tooltip='Commit staged changes',
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
                     self.summary_return_pressed)

        self.connect(self.summary, SIGNAL('cursorPositionChanged(int,int)'),
                     lambda x, y: self.emit_summary_position())

        # Keep model informed of changes
        self.connect(self.summary, SIGNAL('textChanged(QString)'),
                     self.commit_message_changed)

        self.connect(self.description, SIGNAL('textChanged()'),
                     self.commit_message_changed)

        self.connect(self.description, SIGNAL('cursorPositionChanged()'),
                     self.emit_cursor_position)

        self.connect(self.description, SIGNAL('shiftTab()'),
                     self.focus_summary)

        self.setFont(diff_font())

        self.summary.installEventFilter(self)
        self.description.installEventFilter(self)

        self.enable_placeholder_summary(True)
        self.enable_placeholder_description(True)

        self.commit_button.setEnabled(False)
        self.commit_action.setEnabled(False)

        self.setFocusProxy(self.summary)

    def focus_summary(self):
        self.summary.setFocus(True)

    def is_summary_placeholder(self):
        summary = unicode(self.summary.text()).strip()
        return summary == self.summary_placeholder

    def is_description_placeholder(self):
        description = unicode(self.description.toPlainText()).strip()
        return description == self.description_placeholder

    def eventFilter(self, obj, event):
        if obj == self.summary:
            if event.type() == QtCore.QEvent.FocusIn:
                self.emit_summary_position()
                if self.is_summary_placeholder():
                    self.enable_placeholder_summary(False)

            elif event.type() == QtCore.QEvent.FocusOut:
                if not bool(self.commit_summary()):
                    self.enable_placeholder_summary(True)

        elif obj == self.description:
            if event.type() == QtCore.QEvent.FocusIn:
                self.emit_cursor_position()
                if self.is_description_placeholder():
                    self.enable_placeholder_description(False)

            elif event.type() == QtCore.QEvent.FocusOut:
                if not bool(self.commit_description()):
                    self.enable_placeholder_description(True)

        return False

    def enable_placeholder_summary(self, placeholder):
        blocksignals = self.summary.blockSignals(True)
        if placeholder:
            self.summary.setText(self.summary_placeholder)
        else:
            self.summary.clear()
        self.summary.setCursorPosition(0)
        self.summary.blockSignals(blocksignals)
        self.set_placeholder_palette(self.summary, placeholder)

    def enable_placeholder_description(self, placeholder):
        blocksignals = self.description.blockSignals(True)
        if placeholder:
            self.description.setPlainText(self.description_placeholder)
        else:
            self.description.clear()
        self.description.blockSignals(blocksignals)
        self.set_placeholder_palette(self.description, placeholder)

    def set_placeholder_palette(self, widget, placeholder):
        if placeholder:
            widget.setPalette(self.placeholder_palette)
        else:
            widget.setPalette(self.default_palette)

    def summary_return_pressed(self):
        if bool(self.commit_summary()):
            self.description.setFocus(True)

    def commit_summary(self):
        """Return the commit summary as unicode"""
        summary = unicode(self.summary.text()).strip()
        if summary != self.summary_placeholder:
            return summary
        else:
            return u''

    def commit_description(self):
        """Return the commit description as unicode"""
        description = unicode(self.description.toPlainText()).strip()
        if description != self.description_placeholder:
            return description
        else:
            return u''

    def commit_message(self):
        """Return the commit message as a unicode string"""
        summary = self.commit_summary()
        description = self.commit_description()
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
        self.update_placeholder_state()
        self.notifying = False
        self.update_actions()

    def update_actions(self):
        commit_enabled = bool(self.commit_summary())
        self.commit_button.setEnabled(commit_enabled)
        self.commit_action.setEnabled(commit_enabled)

    def update_placeholder_state(self):
        """Update the color palette for the placeholder text"""
        self.set_placeholder_palette(self.summary,
                                     self.is_summary_placeholder())
        self.set_placeholder_palette(self.description,
                                     self.is_description_placeholder())

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
            summary = self.summary_placeholder

        blocksignals = self.summary.blockSignals(True)
        self.summary.setText(summary)
        self.summary.setCursorPosition(0)
        self.summary.blockSignals(blocksignals)

        # Update description
        if not description and not self.description.hasFocus():
            description = self.description_placeholder

        blocksignals = self.description.blockSignals(True)
        self.description.setPlainText(description)
        self.description.blockSignals(blocksignals)

        # Update text color
        self.update_placeholder_state()

        # Focus the empty summary or description
        if focus_summary:
            self.summary.setFocus(True)
            self.emit_summary_position()
        elif focus_description:
            self.description.setFocus(True)
            self.emit_cursor_position()
        else:
            self.emit_summary_position()

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

    def emit_summary_position(self):
        cols = self.summary.cursorPosition()
        self.emit(SIGNAL('cursorPosition(int,int)'), 1, cols)

    def emit_cursor_position(self):
        """Update the UI with the current row and column."""
        cursor = self.description.textCursor()
        position = cursor.position()
        txt = unicode(self.description.toPlainText())
        rows = txt[:position].count('\n') + 1 + 2 # description starts at 2
        cols = cursor.columnNumber()
        self.emit(SIGNAL('cursorPosition(int,int)'), rows, cols)

    def commit(self):
        """Attempt to create a commit from the index and commit message."""
        if not bool(self.commit_summary()):
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


class CommitMessageTextEdit(QtGui.QTextEdit):
    def __init__(self, parent=None):
        QtGui.QTextEdit.__init__(self, parent)
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setAcceptRichText(False)
        self.setMinimumSize(QtCore.QSize(1, 1))

        self.action_emit_shift_tab = add_action(self,
                'Shift Tab', self.shift_tab, 'Shift+tab')

        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.FocusIn:
            height = QtGui.QFontMetrics(self.font()).height() * 3
            height += defs.spacing * 4
            self.setMinimumSize(QtCore.QSize(1, height))

        elif event.type() == QtCore.QEvent.FocusOut:
            self.setMinimumSize(QtCore.QSize(1, 1))

        return False

    def shift_tab(self):
        self.emit(SIGNAL('shiftTab()'))
