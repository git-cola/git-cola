from __future__ import division, absolute_import, unicode_literals

import os
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import gitcfg
from cola import gitcmds
from cola import qtutils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.qtutils import create_button
from cola.widgets import defs
from cola.widgets import completion
from cola.widgets import standard
from cola.compat import ustr


def install():
    Interaction.run_command = staticmethod(run_command)
    Interaction.confirm_config_action = staticmethod(confirm_config_action)


def get_config_actions():
    cfg = gitcfg.current()
    return cfg.get_guitool_names_and_shortcuts()


def confirm_config_action(name, opts):
    dlg = ActionDialog(qtutils.active_window(), name, opts)
    dlg.show()
    if dlg.exec_() != QtGui.QDialog.Accepted:
        return False
    rev = ustr(dlg.revision())
    if rev:
        opts['revision'] = rev
    args = ustr(dlg.args())
    if args:
        opts['args'] = args
    return True


def run_command(title, command):
    """Show a command widget"""
    view = GitCommandWidget(title, qtutils.active_window())
    view.set_command(command)
    view.show()
    view.raise_()
    view.run()
    view.exec_()
    return (view.exitstatus, view.out, view.err)


class GitCommandWidget(standard.Dialog):
    """Nice TextView that reads the output of a command syncronously"""
    # Keep us in scope otherwise PyQt kills the widget
    def __init__(self, title, parent=None):
        standard.Dialog.__init__(self, parent)
        self.setWindowTitle(title)
        if parent is not None:
            self.setWindowModality(Qt.ApplicationModal)

        # Construct the process
        self.proc = QtCore.QProcess(self)
        self.exitstatus = 0
        self.out = ''
        self.err = ''

        # Create the text browser
        self.output_text = QtGui.QTextBrowser(self)
        self.output_text.setAcceptDrops(False)
        self.output_text.setTabChangesFocus(True)
        self.output_text.setUndoRedoEnabled(False)
        self.output_text.setReadOnly(True)
        self.output_text.setAcceptRichText(False)

        # Create abort / close buttons
        self.button_abort = QtGui.QPushButton(self)
        self.button_abort.setText(N_('Abort'))
        self.button_close = QtGui.QPushButton(self)
        self.button_close.setText(N_('Close'))

        # Put them in a horizontal layout at the bottom.
        self.button_box = QtGui.QDialogButtonBox(self)
        self.button_box.addButton(self.button_abort, QtGui.QDialogButtonBox.RejectRole)
        self.button_box.addButton(self.button_close, QtGui.QDialogButtonBox.AcceptRole)

        # Connect the signals to the process
        self.connect(self.proc, SIGNAL('readyReadStandardOutput()'),
                self.read_stdout)
        self.connect(self.proc, SIGNAL('readyReadStandardError()'),
                self.read_stderr)
        self.connect(self.proc, SIGNAL('finished(int)'), self.finishProc)
        self.connect(self.proc, SIGNAL('stateChanged(QProcess::ProcessState)'), self.stateChanged)

        # Start with abort disabled - will be enabled when the process is run.
        self.button_abort.setEnabled(False)

        qtutils.connect_button(self.button_abort, self.abortProc)
        qtutils.connect_button(self.button_close, self.close)

        self._layout = qtutils.vbox(defs.margin, defs.spacing,
                                    self.output_text, self.button_box)
        self.setLayout(self._layout)

        self.resize(720, 420)

    def set_command(self, command):
        self.command = command

    def run(self):
        """Runs the process"""
        self.proc.start(self.command[0], QtCore.QStringList(self.command[1:]))

    def read_stdout(self):
        rawbytes = self.proc.readAllStandardOutput()
        data = ''
        for b in rawbytes:
            data += b
        text = core.decode(data)
        self.out += text
        self.append_text(text)

    def read_stderr(self):
        rawbytes = self.proc.readAllStandardError()
        data = ''
        for b in rawbytes:
            data += b
        text = core.decode(data)
        self.err += text
        self.append_text(text)

    def append_text(self, text):
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        cursor.movePosition(cursor.End)
        self.output_text.setTextCursor(cursor)

    def abortProc(self):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # Terminate seems to do nothing in windows
            self.proc.terminate()
            # Kill the process.
            QtCore.QTimer.singleShot(1000, self.proc, QtCore.SLOT('kill()'))

    def closeEvent(self, event):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # The process is still running, make sure we really want to abort.
            title = N_('Abort Action')
            msg = N_('An action is still running.\n'
                     'Terminating it could result in data loss.')
            info_text = N_('Abort the action?')
            ok_text = N_('Abort Action')
            if qtutils.confirm(title, msg, info_text, ok_text,
                               default=False, icon=qtutils.discard_icon()):
                self.abortProc()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

        return standard.Dialog.closeEvent(self, event)

    def stateChanged(self, newstate):
        # State of process has changed - change the abort button state.
        if newstate == QtCore.QProcess.NotRunning:
            self.button_abort.setEnabled(False)
        else:
            self.button_abort.setEnabled(True)

    def finishProc(self, status ):
        self.exitstatus = status


class ActionDialog(standard.Dialog):

    VALUES = {}

    def __init__(self, parent, name, opts):
        standard.Dialog.__init__(self, parent)
        self.name = name
        self.opts = opts

        try:
            values = self.VALUES[name]
        except KeyError:
            values = self.VALUES[name] = {}

        self.setWindowModality(Qt.ApplicationModal)

        title = opts.get('title')
        if title:
            self.setWindowTitle(os.path.expandvars(title))

        self.prompt = QtGui.QLabel()
        prompt = opts.get('prompt')
        if prompt:
            self.prompt.setText(os.path.expandvars(prompt))

        self.argslabel = QtGui.QLabel()
        if 'argprompt' not in opts or opts.get('argprompt') is True:
            argprompt = N_('Arguments')
        else:
            argprompt = opts.get('argprompt')
        self.argslabel.setText(argprompt)

        self.argstxt = QtGui.QLineEdit()
        if self.opts.get('argprompt'):
            try:
                # Remember the previous value
                saved_value = values['argstxt']
                self.argstxt.setText(saved_value)
            except KeyError:
                pass
        else:
            self.argslabel.setMinimumSize(1, 1)
            self.argstxt.setMinimumSize(1, 1)
            self.argstxt.hide()
            self.argslabel.hide()

        revs = (
            (N_('Local Branch'), gitcmds.branch_list(remote=False)),
            (N_('Tracking Branch'), gitcmds.branch_list(remote=True)),
            (N_('Tag'), gitcmds.tag_list()),
        )

        if 'revprompt' not in opts or opts.get('revprompt') is True:
            revprompt = N_('Revision')
        else:
            revprompt = opts.get('revprompt')
        self.revselect = RevisionSelector(self, revs)
        self.revselect.set_revision_label(revprompt)

        if not opts.get('revprompt'):
            self.revselect.hide()

        # Close/Run buttons
        self.closebtn = create_button(text=N_('Close'))
        self.runbtn = create_button(text=N_('Run'))
        self.runbtn.setDefault(True)

        self.argslayt = qtutils.hbox(defs.margin, defs.spacing,
                                     self.argslabel, self.argstxt)

        self.btnlayt = qtutils.hbox(defs.margin, defs.spacing,
                                    qtutils.STRETCH, self.closebtn, self.runbtn)

        self.layt = qtutils.vbox(defs.margin, defs.spacing,
                                 self.prompt, self.argslayt,
                                 self.revselect, self.btnlayt)
        self.setLayout(self.layt)

        self.connect(self.argstxt, SIGNAL('textChanged(QString)'),
                     self._argstxt_changed)

        qtutils.connect_button(self.closebtn, self.reject)
        qtutils.connect_button(self.runbtn, self.accept)

        # Widen the dialog by default
        self.resize(666, self.height())

    def revision(self):
        return self.revselect.revision()

    def args(self):
        return self.argstxt.text()

    def _argstxt_changed(self, value):
        """Store the argstxt value so that we can remember it between calls"""
        self.VALUES[self.name]['argstxt'] = ustr(value)


class RevisionSelector(QtGui.QWidget):

    def __init__(self, parent, revs):
        QtGui.QWidget.__init__(self, parent)

        self._revs = revs
        self._revdict = dict(revs)

        self._rev_label = QtGui.QLabel()
        self._revision = completion.GitRefLineEdit()

        # Create the radio buttons
        radio_btns = []
        self._radio_btns = {}
        for label, rev_list in self._revs:
            radio = QtGui.QRadioButton()
            radio.setText(label)
            radio.setObjectName(label)
            qtutils.connect_button(radio, self._set_revision_list)
            radio_btns.append(radio)
            self._radio_btns[label] = radio
        radio_btns.append(qtutils.STRETCH)

        self._rev_list = QtGui.QListWidget()
        label, rev_list = self._revs[0]
        self._radio_btns[label].setChecked(True)
        qtutils.set_items(self._rev_list, rev_list)

        self._rev_layt = qtutils.hbox(defs.no_margin, defs.spacing,
                                      self._rev_label, self._revision)

        self._radio_layt = qtutils.hbox(defs.margin, defs.spacing,
                                        *radio_btns)

        self._layt = qtutils.vbox(defs.no_margin, defs.spacing,
                                  self._rev_layt, self._radio_layt,
                                  self._rev_list)
        self.setLayout(self._layt)

        self.connect(self._rev_list, SIGNAL('itemSelectionChanged()'),
                     self._rev_list_selection_changed)

    def revision(self):
        return self._revision.text()

    def set_revision_label(self, txt):
        self._rev_label.setText(txt)

    def _set_revision_list(self):
        sender = ustr(self.sender().objectName())
        revs = self._revdict[sender]
        qtutils.set_items(self._rev_list, revs)

    def _rev_list_selection_changed(self):
        items = self._rev_list.selectedItems()
        if not items:
            return
        self._revision.setText(items[0].text())
