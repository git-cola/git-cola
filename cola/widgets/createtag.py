from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt

from cola import cmds
from cola import qtutils
from cola.i18n import N_
from cola.qtutils import connect_button
from cola.qtutils import critical
from cola.qtutils import information
from cola.widgets import completion
from cola.widgets import standard
from cola.widgets import text


def new_create_tag(name='', ref='', sign=False, parent=None):
    """Entry point for external callers."""
    opts = TagOptions(name, ref, sign)
    view = CreateTag(opts, parent=parent)
    return view


def create_tag(name='', ref='', sign=False):
    """Entry point for external callers."""
    view = new_create_tag(name=name, ref=ref, sign=sign,
                          parent=qtutils.active_window())
    view.show()
    view.raise_()
    return view



class TagOptions(object):
    """Simple data container for the CreateTag dialog."""

    def __init__(self, name, ref, sign):
        self.name = name or ''
        self.ref = ref or 'HEAD'
        self.sign = sign


class CreateTag(standard.Dialog):

    def __init__(self, opts, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Create Tag'))
        if parent is not None:
            self.setWindowModality(QtCore.Qt.WindowModal)

        self.opts = opts

        self.main_layt = QtGui.QVBoxLayout(self)
        self.main_layt.setContentsMargins(6, 12, 6, 6)

        # Form layout for inputs
        self.input_form_layt = QtGui.QFormLayout()
        self.input_form_layt.setFieldGrowthPolicy(QtGui.QFormLayout.ExpandingFieldsGrow)

        # Tag label
        self.tag_name_label = QtGui.QLabel(self)
        self.tag_name_label.setText(N_('Name'))
        self.input_form_layt.setWidget(0, QtGui.QFormLayout.LabelRole,
                                       self.tag_name_label)

        self.tag_name = text.HintedLineEdit(N_('vX.Y.Z'), self)
        self.tag_name.set_value(opts.name)
        self.tag_name.setToolTip(N_('Specifies the tag name'))
        self.input_form_layt.setWidget(0, QtGui.QFormLayout.FieldRole,
                                       self.tag_name)

        # Sign Tag
        self.sign_label = QtGui.QLabel(self)
        self.sign_label.setText(N_('Sign Tag'))
        self.input_form_layt.setWidget(1, QtGui.QFormLayout.LabelRole,
                                       self.sign_label)

        self.sign_tag = QtGui.QCheckBox(self)
        self.sign_tag.setChecked(opts.sign)
        self.sign_tag.setToolTip(N_('Whether to sign the tag (git tag -s)'))
        self.input_form_layt.setWidget(1, QtGui.QFormLayout.FieldRole,
                                       self.sign_tag)
        self.main_layt.addLayout(self.input_form_layt)

        # Tag message
        self.tag_msg_label = QtGui.QLabel(self)
        self.tag_msg_label.setText(N_('Message'))
        self.input_form_layt.setWidget(2, QtGui.QFormLayout.LabelRole,
                                       self.tag_msg_label)

        self.tag_msg = text.HintedTextEdit(N_('Tag message...'), self)
        self.tag_msg.setToolTip(N_('Specifies the tag message'))
        self.tag_msg.enable_hint(True)
        self.input_form_layt.setWidget(2, QtGui.QFormLayout.FieldRole,
                                       self.tag_msg)
        # Revision
        self.rev_label = QtGui.QLabel(self)
        self.rev_label.setText(N_('Revision'))
        self.input_form_layt.setWidget(3, QtGui.QFormLayout.LabelRole,
                                       self.rev_label)

        self.revision = completion.GitRefLineEdit()
        self.revision.setText(self.opts.ref)
        self.revision.setToolTip(N_('Specifies the SHA-1 to tag'))
        self.input_form_layt.setWidget(3, QtGui.QFormLayout.FieldRole,
                                       self.revision)

        # Buttons
        self.button_hbox_layt = QtGui.QHBoxLayout()
        self.button_hbox_layt.addStretch()

        self.create_button = qtutils.create_button(text=N_('Create Tag'),
                                                   icon=qtutils.git_icon())
        self.button_hbox_layt.addWidget(self.create_button)
        self.main_layt.addLayout(self.button_hbox_layt)

        self.close_button = qtutils.create_button(text=N_('Close'))
        self.button_hbox_layt.addWidget(self.close_button)

        connect_button(self.close_button, self.accept)
        connect_button(self.create_button, self.create_tag)

        self.resize(506, 295)

    def create_tag(self):
        """Verifies inputs and emits a notifier tag message."""

        revision = self.revision.value()
        tag_name = self.tag_name.value()
        tag_msg = self.tag_msg.value()
        sign_tag = self.sign_tag.isChecked()

        if not revision:
            critical(N_('Missing Revision'),
                     N_('Please specify a revision to tag.'))
            return
        elif not tag_name:
            critical(N_('Missing Name'),
                     N_('Please specify a name for the new tag.'))
            return
        elif (sign_tag and not tag_msg and
                not qtutils.confirm(N_('Missing Tag Message'),
                                    N_('Tag-signing was requested but the tag '
                                       'message is empty.'),
                                    N_('An unsigned, lightweight tag will be '
                                       'created instead.\n'
                                       'Create an unsigned tag?'),
                                    N_('Create Unsigned Tag'),
                                    default=False,
                                    icon=qtutils.save_icon())):
            return

        cmds.do(cmds.Tag, tag_name, revision,
                sign=sign_tag, message=tag_msg)
        information(N_('Tag Created'),
                    N_('Created a new tag named "%s"') % tag_name,
                    details=tag_msg or None)
        self.accept()
