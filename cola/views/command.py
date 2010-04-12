""" Provides the GitCommandWidget dialog. """

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import *
from cola import qtutils
import subprocess
import sys
import standard

def git_command(command, params, parent=None):
    """ Show a command widget """

    view = GitCommandWidget(parent)
    view.setWindowModality(QtCore.Qt.ApplicationModal)
    view.set_command(command, params)
    if not parent:
        qtutils.center_on_screen(view)
    view.run()
    view.show()
    return view.exitstatus

class GitCommandWidget(QtGui.QWidget):
    ''' Nice TextView that reads the output of a command syncronously '''
    # Keep us in scope otherwise PyQt kills the widget
    _instances = set()

    def __del__(self):
        if self.start:
            self.proc.kill()
        self._instances.remove(self)

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self._instances.add(self)
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

        # Construct the process
        self.proc = QtCore.QProcess(self)
        self.exitstatus = 0

        # Connect the signals to the process
        self.connect(self.proc, QtCore.SIGNAL("readyReadStandardOutput()"), self.readOutput)
        self.connect(self.proc, QtCore.SIGNAL("readyReadSteandardError()"), self.readErrors)
        self.connect(self.proc, QtCore.SIGNAL('finished(int)'), self.finishProc)
        self.connect(self.proc, QtCore.SIGNAL('stateChanged(QProcess::ProcessState)'), self.stateChanged)

        # Connect the signlas to the buttons
        self.connect(self.button_abort, QtCore.SIGNAL('clicked()'), self.abortProc)
        self.connect(self.button_close, QtCore.SIGNAL('clicked()'), self.close)
        # Start with abort disabled - will be enabled when the process is run.
        self.button_abort.setEnabled(False)

    def set_command(self, command, params):
        '''command : the shell command to spawn
           params  : parameters of the command '''
        self.command = command
        self.params = params

    def run(self):
        ''' Runs the process '''
        self.proc.start(self.command, QtCore.QStringList(self.params))

    def readOutput(self):
        strOut = self.proc.readAllStandardOutput()
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        text = self.output_text
        cursor.insertText(QtCore.QString(strOut)) # When running don't touch the TextView!!
        cursor.movePosition(cursor.End)
        text.setTextCursor(cursor)

    def readErrors(self):
        strOut = self.proc.readAllStandardOutput()
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        text = self.output_text
        cursor.insertText(QtCore.QString(strOut)) # When running don't touch the TextView!!
        cursor.movePosition(cursor.End)
        text.setTextCursor(cursor)

    def abortProc(self):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # Terminate seems to do nothing in windows
            self.proc.terminate()
            # Kill the process.
            QtCore.QTimer.singleShot(1000, self.proc, QtCore.SLOT("kill()"))

    def closeEvent(self, event):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # The process is still running, make sure we really want to abort.
            reply = QtGui.QMessageBox.question(self, 'Message',
                    self.tr("Abort process?"), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
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

