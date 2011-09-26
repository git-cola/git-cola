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
from cola.views import revselect
from cola.views import standard


def install_command_wrapper(parent):
    cmd_wrapper = ActionCommandWrapper(parent)
    cola.factory().add_command_wrapper(cmd_wrapper)


def get_config_actions():
    cfg = gitcfg.instance()
    names = cfg.get_guitool_names()
    return names or []


def run_command(parent, title, command):
    """Show a command widget"""

    view = GitCommandWidget(parent)
    view.setWindowModality(QtCore.Qt.ApplicationModal)
    view.set_command(command)
    view.setWindowTitle(title)
    if not parent:
        qtutils.center_on_screen(view)
    view.run()
    view.show()
    view.raise_()
    view.exec_()
    return (view.exitstatus, view.out, view.err)


class GitCommandWidget(standard.StandardDialog):
    """Nice TextView that reads the output of a command syncronously"""
    # Keep us in scope otherwise PyQt kills the widget
    _instances = set()

    def __del__(self):
        self._instances.remove(self)

    def __init__(self, parent=None):
        standard.StandardDialog.__init__(self, parent=parent)
        self._instances.add(self)
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
            reply = QtGui.QMessageBox.question(self, 'Message',
                    self.tr('Abort process?'),
                    QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.abortProc()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def stateChanged(self, newstate):
        # State of process has changed - change the abort button state.
        if newstate == QtCore.QProcess.NotRunning:
            self.button_abort.setEnabled(False)
        else:
            self.button_abort.setEnabled(True)

    def finishProc(self, status ):
        self.exitstatus = status


class ActionCommandWrapper(object):
    def __init__(self, parent):
        self.parent = parent
        self.callbacks = {
                signals.run_config_action: self._run_config_action,
                signals.run_command: self._run_command,
        }

    def _run_command(self, title, cmd):
        return run_command(self.parent, title, cmd)

    def _run_config_action(self, name, opts):
        dlg = ActionDialog(self.parent, name, opts)
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


class ActionDialog(standard.StandardDialog):
    def __init__(self, parent, name, opts):
        standard.StandardDialog.__init__(self, parent)
        self.name = name
        self.opts = opts

        self.layt = QtGui.QVBoxLayout()
        self.layt.setMargin(10)
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
        self.revselect = revselect.RevisionSelector(self, revs=revs)
        self.revselect.set_revision_label(revprompt)
        self.layt.addWidget(self.revselect)

        if not opts.get('revprompt'):
            self.revselect.hide()

        # Close/Run buttons
        self.btnlayt = QtGui.QHBoxLayout()
        self.btnspacer = QtGui.QSpacerItem(1, 1,
                                           QtGui.QSizePolicy.MinimumExpanding,
                                           QtGui.QSizePolicy.Minimum)
        self.btnlayt.addItem(self.btnspacer)
        self.closebtn = qt.create_button(self.tr('Close'), self.btnlayt)
        self.runbtn = qt.create_button(self.tr('Run'), self.btnlayt)
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
