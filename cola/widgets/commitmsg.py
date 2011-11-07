from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import gitcmds
from cola import signals
from cola.qt import create_toolbutton
from cola.qtutils import apply_icon
from cola.qtutils import confirm
from cola.qtutils import connect_button
from cola.qtutils import emit
from cola.qtutils import log
from cola.qtutils import relay_signal
from cola.qtutils import save_icon
from cola.qtutils import tr
from cola.prefs import diff_font
from cola.controllers.selectcommits import select_commits
from cola.dag.model import DAG
from cola.dag.model import RepoReader


class CommitMessageEditor(QtGui.QWidget):
    def __init__(self, model, parent):
        QtGui.QWidget.__init__(self, parent)

        self.model = model
        self._layt = QtGui.QVBoxLayout()
        self._layt.setMargin(0)
        self._layt.setSpacing(0)

        self.commitmsg = CommitMessageTextEdit(model, self)
        self.commitmsg.setFont(diff_font())

        self._ctrls_layt = QtGui.QHBoxLayout()
        self._ctrls_layt.setSpacing(4)
        self._ctrls_layt.setMargin(4)

        # Sign off and commit buttons
        self.signoff_button = create_toolbutton(self,
                                                text='Sign Off',
                                                tooltip='Sign off on this commit',
                                                icon=apply_icon())

        self.commit_button = create_toolbutton(self,
                                               text='Commit@@verb',
                                               tooltip='Commit staged changes',
                                               icon=save_icon())

        # Position display
        self.position_label = QtGui.QLabel()
        self.position_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        # Amend checkbox
        self.amend_checkbox = QtGui.QCheckBox()
        self.amend_checkbox.setText(tr('Amend Last Commit'))

        self._ctrls_layt.addWidget(self.signoff_button)
        self._ctrls_layt.addWidget(self.commit_button)
        self._ctrls_layt.addWidget(self.position_label)
        self._ctrls_layt.addStretch()
        self._ctrls_layt.addWidget(self.amend_checkbox)

        self._layt.addWidget(self.commitmsg)
        self._layt.addLayout(self._ctrls_layt)
        self.setLayout(self._layt)

        relay_signal(self, self.commitmsg,
                     SIGNAL(signals.load_previous_message))
        connect_button(self.commit_button, self.commit)

        cola.notifier().connect(signals.amend, self.amend_checkbox.setChecked)

        # Broadcast the amend mode
        self.connect(self.amend_checkbox,
                     SIGNAL('toggled(bool)'), emit(self, signals.amend_mode))
        self.connect(self.signoff_button,
                     SIGNAL('clicked()'), emit(self, signals.signoff))

        # Display the current column
        self.connect(self.commitmsg, SIGNAL('cursorPositionChanged()'),
                     self.show_cursor_position)

        # Initialize the GUI to show 'Column: 00'
        self.show_cursor_position()

    def set_mode(self, mode):
        checked = (mode == self.model.mode_amend)
        self.amend_checkbox.blockSignals(True)
        self.amend_checkbox.setChecked(checked)
        self.amend_checkbox.blockSignals(False)

    def commit(self):
        """Attempt to create a commit from the index and commit message."""
        msg = unicode(self.commitmsg.toPlainText())
        if not msg:
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
        amend = self.amend_checkbox.isChecked()
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

    def show_cursor_position(self):
        """Update the UI with the current row and column."""
        cursor = self.commitmsg.textCursor()
        position = cursor.position()
        txt = unicode(self.commitmsg.toPlainText())
        rows = txt[:position].count('\n') + 1
        cols = cursor.columnNumber()
        display = ' %d,%d ' % (rows, cols)
        if cols > 78:
            display = ('<span style="color: white; '
                       '             background-color: red;"'
                       '>%s</span>' % display.replace(' ', '&nbsp;'))
        elif cols > 72:
            display = ('<span style="color: black; '
                       '             background-color: orange;"'
                       '>%s</span>' % display.replace(' ', '&nbsp;'))
        elif cols > 64:
            display = ('<span style="color: black; '
                       '             background-color: yellow;"'
                       '>%s</span>' % display.replace(' ', '&nbsp;'))
        self.position_label.setText(display)


class CommitMessageTextEdit(QtGui.QTextEdit):
    def __init__(self, model, parent):
        QtGui.QTextEdit.__init__(self, parent)
        self.model = model
        self.notifying = False
        self.menu_ready= False
        self.setMinimumSize(QtCore.QSize(1, 1))
        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                   QtGui.QSizePolicy.Minimum)
        self.setSizePolicy(policy)
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setAcceptRichText(False)

        self.model.add_message_observer(self.model.message_commit_message_changed,
                                        self.set_commitmsg)
        # Keep model informed of changes
        self.connect(self, SIGNAL('textChanged()'), self.commitmsg_changed)

    def commitmsg_changed(self):
        self.notifying = True
        self.model.set_commitmsg(unicode(self.toPlainText()))
        self.notifying = False

    def set_commitmsg(self, message):
        if self.notifying:
            return
        self.blockSignals(True)
        self.setPlainText(unicode(message))
        self.blockSignals(False)

    def contextMenuEvent(self, event):
        self.menu_ready = False
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        prevmenu = menu.addMenu('Load Previous Commit Message')
        self.connect(prevmenu, SIGNAL('aboutToShow()'),
                     lambda: self.prev_commit_menu_clicked(prevmenu, event))
        menu.exec_(self.mapToGlobal(event.pos()))
        self.menu_ready = False

    def prev_commit_menu_clicked(self, menu, event):
        if self.menu_ready:
            return
        dag = DAG('HEAD', 6)
        commits = RepoReader(dag)

        menu_commits = []
        for idx, c in enumerate(commits):
            menu_commits.insert(0, c)
            if idx > 5:
                continue

        for c in menu_commits:
            menu.addAction(c.subject,
                           lambda c=c: self.load_previous_message(c.sha1))

        if len(commits) == 6:
            menu.addSeparator()
            menu.addAction('More...', self.choose_commit)

        self.menu_ready = True

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
