from __future__ import absolute_import, division, print_function, unicode_literals
import os

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import core
from .. import gitcmds
from .. import icons
from .. import qtutils
from ..i18n import N_
from ..interaction import Interaction
from . import defs
from . import completion
from . import standard
from .text import LineEdit


def install():
    Interaction.run_command = staticmethod(run_command)
    Interaction.confirm_config_action = staticmethod(confirm_config_action)


def get_config_actions(context):
    cfg = context.cfg
    return cfg.get_guitool_names_and_shortcuts()


def confirm_config_action(context, name, opts):
    dlg = ActionDialog(context, qtutils.active_window(), name, opts)
    dlg.show()
    if dlg.exec_() != QtWidgets.QDialog.Accepted:
        return False
    rev = dlg.revision()
    if rev:
        opts['revision'] = rev
    args = dlg.args()
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
    """Text viewer that reads the output of a command synchronously"""

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
        self.command = []

        # Create the text browser
        self.output_text = QtWidgets.QTextBrowser(self)
        self.output_text.setAcceptDrops(False)
        self.output_text.setTabChangesFocus(True)
        self.output_text.setUndoRedoEnabled(False)
        self.output_text.setReadOnly(True)
        self.output_text.setAcceptRichText(False)

        # Create abort / close buttons
        # Start with abort disabled - will be enabled when the process is run.
        self.button_abort = qtutils.create_button(text=N_('Abort'), enabled=False)
        self.button_close = qtutils.close_button()

        # Put them in a horizontal layout at the bottom.
        self.button_box = QtWidgets.QDialogButtonBox(self)
        self.button_box.addButton(
            self.button_abort, QtWidgets.QDialogButtonBox.RejectRole
        )
        self.button_box.addButton(
            self.button_close, QtWidgets.QDialogButtonBox.AcceptRole
        )

        # Connect the signals to the process
        # pylint: disable=no-member
        self.proc.readyReadStandardOutput.connect(self.read_stdout)
        self.proc.readyReadStandardError.connect(self.read_stderr)
        self.proc.finished.connect(self.proc_finished)
        self.proc.stateChanged.connect(self.proc_state_changed)

        qtutils.connect_button(self.button_abort, self.abort)
        qtutils.connect_button(self.button_close, self.close)

        self._layout = qtutils.vbox(
            defs.margin, defs.spacing, self.output_text, self.button_box
        )
        self.setLayout(self._layout)

        self.resize(720, 420)

    def set_command(self, command):
        self.command = command

    def run(self):
        """Runs the process"""
        self.proc.start(self.command[0], self.command[1:])

    def read_stdout(self):
        text = self.read_stream(self.proc.readAllStandardOutput)
        self.out += text

    def read_stderr(self):
        text = self.read_stream(self.proc.readAllStandardError)
        self.err += text

    def read_stream(self, fn):
        data = fn().data()
        text = core.decode(data)
        self.append_text(text)
        return text

    def append_text(self, text):
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        cursor.movePosition(cursor.End)
        self.output_text.setTextCursor(cursor)

    def abort(self):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # Terminate seems to do nothing in windows
            self.proc.terminate()
            # Kill the process.
            QtCore.QTimer.singleShot(1000, self.proc.kill)

    def closeEvent(self, event):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # The process is still running, make sure we really want to abort.
            title = N_('Abort Action')
            msg = N_(
                'An action is still running.\n'
                'Terminating it could result in data loss.'
            )
            info_text = N_('Abort the action?')
            ok_text = N_('Abort Action')
            if Interaction.confirm(
                title, msg, info_text, ok_text, default=False, icon=icons.close()
            ):
                self.abort()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

        return standard.Dialog.closeEvent(self, event)

    def proc_state_changed(self, newstate):
        # State of process has changed - change the abort button state.
        if newstate == QtCore.QProcess.NotRunning:
            self.button_abort.setEnabled(False)
        else:
            self.button_abort.setEnabled(True)

    def proc_finished(self, status):
        self.exitstatus = status


class ActionDialog(standard.Dialog):

    VALUES = {}

    def __init__(self, context, parent, name, opts):
        standard.Dialog.__init__(self, parent)
        self.context = context
        self.action_name = name
        self.opts = opts

        try:
            values = self.VALUES[name]
        except KeyError:
            values = self.VALUES[name] = {}

        self.setWindowModality(Qt.ApplicationModal)

        title = opts.get('title')
        if title:
            self.setWindowTitle(os.path.expandvars(title))

        self.prompt = QtWidgets.QLabel()
        prompt = opts.get('prompt')
        if prompt:
            self.prompt.setText(os.path.expandvars(prompt))

        self.argslabel = QtWidgets.QLabel()
        if 'argprompt' not in opts or opts.get('argprompt') is True:
            argprompt = N_('Arguments')
        else:
            argprompt = opts.get('argprompt')
        self.argslabel.setText(argprompt)

        self.argstxt = LineEdit()
        if self.opts.get('argprompt'):
            try:
                # Remember the previous value
                saved_value = values['argstxt']
                self.argstxt.setText(saved_value)
            except KeyError:
                pass
        else:
            self.argslabel.setMinimumSize(10, 10)
            self.argstxt.setMinimumSize(10, 10)
            self.argstxt.hide()
            self.argslabel.hide()

        revs = (
            (N_('Local Branch'), gitcmds.branch_list(context, remote=False)),
            (N_('Tracking Branch'), gitcmds.branch_list(context, remote=True)),
            (N_('Tag'), gitcmds.tag_list(context)),
        )

        if 'revprompt' not in opts or opts.get('revprompt') is True:
            revprompt = N_('Revision')
        else:
            revprompt = opts.get('revprompt')
        self.revselect = RevisionSelector(context, self, revs)
        self.revselect.set_revision_label(revprompt)

        if not opts.get('revprompt'):
            self.revselect.hide()

        # Close/Run buttons
        self.closebtn = qtutils.close_button()
        self.runbtn = qtutils.create_button(
            text=N_('Run'), default=True, icon=icons.ok()
        )

        self.argslayt = qtutils.hbox(
            defs.margin, defs.spacing, self.argslabel, self.argstxt
        )

        self.btnlayt = qtutils.hbox(
            defs.margin, defs.spacing, qtutils.STRETCH, self.closebtn, self.runbtn
        )

        self.layt = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.prompt,
            self.argslayt,
            self.revselect,
            self.btnlayt,
        )
        self.setLayout(self.layt)

        # pylint: disable=no-member
        self.argstxt.textChanged.connect(self._argstxt_changed)
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
        self.VALUES[self.action_name]['argstxt'] = value


class RevisionSelector(QtWidgets.QWidget):
    def __init__(self, context, parent, revs):
        QtWidgets.QWidget.__init__(self, parent)

        self.context = context
        self._revs = revs
        self._revdict = dict(revs)

        self._rev_label = QtWidgets.QLabel(self)
        self._revision = completion.GitRefLineEdit(context, parent=self)

        # Create the radio buttons
        radio_btns = []
        self._radio_btns = {}
        for label, rev_list in self._revs:
            radio = qtutils.radio(text=label)
            radio.setObjectName(label)
            qtutils.connect_button(radio, self._set_revision_list)
            radio_btns.append(radio)
            self._radio_btns[label] = radio
        radio_btns.append(qtutils.STRETCH)

        self._rev_list = QtWidgets.QListWidget()
        label, rev_list = self._revs[0]
        self._radio_btns[label].setChecked(True)
        qtutils.set_items(self._rev_list, rev_list)

        self._rev_layt = qtutils.hbox(
            defs.no_margin, defs.spacing, self._rev_label, self._revision
        )

        self._radio_layt = qtutils.hbox(defs.margin, defs.spacing, *radio_btns)

        self._layt = qtutils.vbox(
            defs.no_margin,
            defs.spacing,
            self._rev_layt,
            self._radio_layt,
            self._rev_list,
        )
        self.setLayout(self._layt)

        # pylint: disable=no-member
        self._rev_list.itemSelectionChanged.connect(self.selection_changed)

    def revision(self):
        return self._revision.text()

    def set_revision_label(self, txt):
        self._rev_label.setText(txt)

    def _set_revision_list(self):
        sender = self.sender().objectName()
        revs = self._revdict[sender]
        qtutils.set_items(self._rev_list, revs)

    def selection_changed(self):
        items = self._rev_list.selectedItems()
        if not items:
            return
        self._revision.setText(items[0].text())
