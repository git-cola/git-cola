import os
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

import cola
from cola import qt
from cola import i18n
from cola import qtutils
from cola import signals
from cola import gitcfg
from cola import gitcmds
from cola.qtutils import SLOT
from cola.views import revselect
from cola.views import standard


def install_command_wrapper(parent):
    cmd_wrapper = ActionCommandWrapper(parent)
    cola.factory().add_command_wrapper(cmd_wrapper)


def install_config_actions(menu):
    cfg = gitcfg.instance()
    names = cfg.get_guitool_names()
    if not names:
        return
    menu.addSeparator()
    for name in names:
        menu.addAction(name, SLOT(signals.run_config_action, name))


class ActionCommandWrapper(object):
    def __init__(self, parent):
        self.parent = parent
        self.callbacks = {
                signals.run_config_action: self._run_config_action,
        }

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

        cmd = self.opts.get('cmd')
        title = self.opts.get('title')
        if title:
            self.setWindowTitle(os.path.expandvars(title))

        self.prompt = QtGui.QLabel()

        prompt = self.opts.get('prompt')
        if prompt:
            self.prompt.setText(os.path.expandvars(prompt))
        self.layt.addWidget(self.prompt)


        self.argslabel = QtGui.QLabel()
        argprompt = self.opts.get('argprompt', i18n.gettext('Arguments'))
        self.argslabel.setText(argprompt)

        self.argstxt = QtGui.QLineEdit()
        self.argslayt = QtGui.QHBoxLayout()
        self.argslayt.addWidget(self.argslabel)
        self.argslayt.addWidget(self.argstxt)
        self.layt.addLayout(self.argslayt)

        if not self.opts.get('argprompt'):
            self.argslabel.setMinimumSize(1, 1)
            self.argstxt.setMinimumSize(1, 1)
            self.argslayt.hide()

        revs = (
            ('Local Branch', gitcmds.branch_list(remote=False)),
            ('Tracking Branch', gitcmds.branch_list(remote=True)),
            ('Tag', gitcmds.tag_list()),
        )
        revprompt = self.opts.get('revprompt', i18n.gettext('Revision'))
        self.revselect = revselect.RevisionSelector(self,
                                                    revs=revs,
                                                    default_revision='HEAD')
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
