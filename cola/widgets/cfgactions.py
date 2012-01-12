import os
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

import cola
from cola import core
from cola import gitcfg
from cola import gitcmds
from cola import qt
from cola import qtutils
from cola import signals
from cola.widgets import defs
from cola.widgets import completion
from cola.widgets import standard


def install_command_wrapper():
    cmd_wrapper = ActionCommandWrapper()
    cola.factory().add_command_wrapper(cmd_wrapper)


def get_config_actions():
    cfg = gitcfg.instance()
    names = cfg.get_guitool_names()
    return names or []


def run_command(title, command):
    """Show a command widget"""
    view = GitCommandWidget(qtutils.active_window())
    view.setWindowModality(QtCore.Qt.ApplicationModal)
    view.set_command(command)
    view.setWindowTitle(title)
    view.show()
    view.raise_()
    view.run()
    view.exec_()
    return (view.exitstatus, view.out, view.err)


class GitCommandWidget(standard.Dialog):
    """Nice TextView that reads the output of a command syncronously"""
    # Keep us in scope otherwise PyQt kills the widget
    def __init__(self, parent=None):
        standard.Dialog.__init__(self, parent)
        self.resize(720, 420)

        # Construct the process
        self.proc = QtCore.QProcess(self)
        self.exitstatus = 0
        self.out = ''
        self.err = ''

        self._layout = QtGui.QVBoxLayout(self)
        self._layout.setContentsMargins(3, 3, 3, 3)

        # Create the text browser
        self.output_text = QtGui.QTextBrowser(self)
        self.output_text.setAcceptDrops(False)
        self.output_text.setTabChangesFocus(True)
        self.output_text.setUndoRedoEnabled(False)
        self.output_text.setReadOnly(True)
        self.output_text.setAcceptRichText(False)

        self._layout.addWidget(self.output_text)

        # Create abort / close buttons
        self.button_abort = QtGui.QPushButton(self)
        self.button_abort.setText(self.tr('Abort'))
        self.button_close = QtGui.QPushButton(self)
        self.button_close.setText(self.tr('Close'))

        # Put them in a horizontal layout at the bottom.
        self.button_box = QtGui.QDialogButtonBox(self)
        self.button_box.addButton(self.button_abort, QtGui.QDialogButtonBox.RejectRole)
        self.button_box.addButton(self.button_close, QtGui.QDialogButtonBox.AcceptRole)
        self._layout.addWidget(self.button_box)

        # Connect the signals to the process
        self.connect(self.proc, SIGNAL('readyReadStandardOutput()'), self.readOutput)
        self.connect(self.proc, SIGNAL('readyReadStandardError()'), self.readErrors)
        self.connect(self.proc, SIGNAL('finished(int)'), self.finishProc)
        self.connect(self.proc, SIGNAL('stateChanged(QProcess::ProcessState)'), self.stateChanged)

        # Connect the signlas to the buttons
        self.connect(self.button_abort, SIGNAL('clicked()'), self.abortProc)
        self.connect(self.button_close, SIGNAL('clicked()'), self.close)
        # Start with abort disabled - will be enabled when the process is run.
        self.button_abort.setEnabled(False)

    def set_command(self, command):
        self.command = command

    def run(self):
        """Runs the process"""
        self.proc.start(self.command[0], QtCore.QStringList(self.command[1:]))

    def readOutput(self):
        rawbytes = self.proc.readAllStandardOutput()
        data = ''
        for b in rawbytes:
            data += b
        self.out += data
        self.append_text(data)

    def readErrors(self):
        rawbytes = self.proc.readAllStandardError()
        data = ''
        for b in rawbytes:
            data += b
        self.err += data
        self.append_text(data)

    def append_text(self, txt):
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(core.decode(txt))
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
            title = 'Abort Action'
            msg = ('An action is still running.\n'
                   'Terminating it could result in data loss.')
            info_text = 'Abort the action?'
            ok_text = 'Abort Action'
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


class ActionCommandWrapper(object):
    def __init__(self):
        self.callbacks = {
                signals.run_config_action: self.run_config_action,
                signals.run_command: run_command,
        }

    def run_config_action(self, name, opts):
        dlg = ActionDialog(qtutils.active_window(), name, opts)
        dlg.show()
        if dlg.exec_() != QtGui.QDialog.Accepted:
            return False
        rev = unicode(dlg.revision())
        if rev:
            opts['revision'] = rev
        args = unicode(dlg.args())
        if args:
            opts['args'] = args
        return True


class ActionDialog(standard.Dialog):
    def __init__(self, parent, name, opts):
        standard.Dialog.__init__(self, parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.name = name
        self.opts = opts

        self.layt = QtGui.QVBoxLayout()
        self.layt.setMargin(defs.margin)
        self.layt.setSpacing(defs.spacing)
        self.setLayout(self.layt)

        title = opts.get('title')
        if title:
            self.setWindowTitle(os.path.expandvars(title))

        self.prompt = QtGui.QLabel()

        prompt = opts.get('prompt')
        if prompt:
            self.prompt.setText(os.path.expandvars(prompt))
        self.layt.addWidget(self.prompt)


        self.argslabel = QtGui.QLabel()
        if 'argprompt' not in opts or opts.get('argprompt') is True:
            argprompt = qtutils.tr('Arguments')
        else:
            argprompt = opts.get('argprompt')

        self.argslabel.setText(argprompt)

        self.argstxt = QtGui.QLineEdit()
        self.argslayt = QtGui.QHBoxLayout()
        self.argslayt.addWidget(self.argslabel)
        self.argslayt.addWidget(self.argstxt)
        self.layt.addLayout(self.argslayt)

        if not self.opts.get('argprompt'):
            self.argslabel.setMinimumSize(1, 1)
            self.argstxt.setMinimumSize(1, 1)
            self.argstxt.hide()
            self.argslabel.hide()

        revs = (
            ('Local Branch', gitcmds.branch_list(remote=False)),
            ('Tracking Branch', gitcmds.branch_list(remote=True)),
            ('Tag', gitcmds.tag_list()),
        )

        if 'revprompt' not in opts or opts.get('revprompt') is True:
            revprompt = qtutils.tr('Revision')
        else:
            revprompt = opts.get('revprompt')
        self.revselect = RevisionSelector(self, revs)
        self.revselect.set_revision_label(revprompt)
        self.layt.addWidget(self.revselect)

        if not opts.get('revprompt'):
            self.revselect.hide()

        # Close/Run buttons
        self.btnlayt = QtGui.QHBoxLayout()
        self.btnlayt.addStretch()
        self.closebtn = qt.create_button(text=self.tr('Close'), layout=self.btnlayt)
        self.runbtn = qt.create_button(text=self.tr('Run'), layout=self.btnlayt)
        self.runbtn.setDefault(True)
        self.layt.addLayout(self.btnlayt)

        self.connect(self.closebtn, SIGNAL('clicked()'), self.reject)
        self.connect(self.runbtn, SIGNAL('clicked()'), self.accept)

        # Widen the dialog by default
        self.resize(666, self.height())

    def revision(self):
        return self.revselect.revision()

    def args(self):
        return self.argstxt.text()


class RevisionSelector(QtGui.QWidget):
    def __init__(self, parent, revs):
        QtGui.QWidget.__init__(self, parent)

        self._revs = revs
        self._revdict = dict(revs)

        self._layt = QtGui.QVBoxLayout()
        self._layt.setMargin(0)
        self.setLayout(self._layt)

        self._rev_layt = QtGui.QHBoxLayout()
        self._rev_layt.setMargin(0)

        self._rev_label = QtGui.QLabel()
        self._rev_layt.addWidget(self._rev_label)

        self._revision = completion.GitRefLineEdit()
        self._rev_layt.addWidget(self._revision)

        self._layt.addLayout(self._rev_layt)

        self._radio_layt = QtGui.QHBoxLayout()
        self._radio_btns = {}

        # Create the radio buttons
        for label, rev_list in self._revs:
            radio = QtGui.QRadioButton()
            radio.setText(self.tr(label))
            radio.setObjectName(label)
            self.connect(radio, SIGNAL('clicked()'), self._set_revision_list)
            self._radio_layt.addWidget(radio)
            self._radio_btns[label] = radio

        self._radio_layt.addStretch()

        self._layt.addLayout(self._radio_layt)

        self._rev_list = QtGui.QListWidget()
        self._layt.addWidget(self._rev_list)

        label, rev_list = self._revs[0]
        self._radio_btns[label].setChecked(True)
        qtutils.set_items(self._rev_list, rev_list)

        self.connect(self._rev_list, SIGNAL('itemSelectionChanged()'),
                     self._rev_list_selection_changed)

    def revision(self):
        return self._revision.text()

    def set_revision_label(self, txt):
        self._rev_label.setText(txt)

    def _set_revision_list(self):
        sender = str(self.sender().objectName())
        revs = self._revdict[sender]
        qtutils.set_items(self._rev_list, revs)

    def _rev_list_selection_changed(self):
        items = self._rev_list.selectedItems()
        if not items:
            return
        self._revision.setText(items[0].text())
