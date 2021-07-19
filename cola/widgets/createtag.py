from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import cmds
from .. import icons
from .. import qtutils
from ..i18n import N_
from ..qtutils import get
from . import defs
from . import completion
from . import standard
from . import text


def new_create_tag(context, name='', ref='', sign=False, parent=None):
    """Entry point for external callers."""
    opts = TagOptions(name, ref, sign)
    view = CreateTag(context, opts, parent=parent)
    return view


def create_tag(context, name='', ref='', sign=False):
    """Entry point for external callers."""
    view = new_create_tag(
        context,
        name=name,
        ref=ref,
        sign=sign,
        parent=qtutils.active_window(),
    )
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
    def __init__(self, context, opts, parent=None):
        standard.Dialog.__init__(self, parent=parent)

        self.context = context
        self.model = model = context.model
        self.opts = opts

        self.setWindowTitle(N_('Create Tag'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        # Tag label
        self.tag_name_label = QtWidgets.QLabel(self)
        self.tag_name_label.setText(N_('Name'))

        self.tag_name = text.HintedLineEdit(context, N_('vX.Y.Z'), parent=self)
        self.tag_name.set_value(opts.name)
        self.tag_name.setToolTip(N_('Specifies the tag name'))

        qtutils.add_completer(self.tag_name, model.tags)

        # Sign Tag
        self.sign_label = QtWidgets.QLabel(self)
        self.sign_label.setText(N_('Sign Tag'))

        tooltip = N_('Whether to sign the tag (git tag -s)')
        self.sign_tag = qtutils.checkbox(checked=True, tooltip=tooltip)

        # Tag message
        self.tag_msg_label = QtWidgets.QLabel(self)
        self.tag_msg_label.setText(N_('Message'))

        self.tag_msg = text.HintedPlainTextEdit(context, N_('Tag message...'), self)
        self.tag_msg.setToolTip(N_('Specifies the tag message'))
        # Revision
        self.rev_label = QtWidgets.QLabel(self)
        self.rev_label.setText(N_('Revision'))

        self.revision = completion.GitRefLineEdit(context)
        self.revision.setText(self.opts.ref)
        self.revision.setToolTip(N_('Specifies the SHA-1 to tag'))
        # Buttons
        self.create_button = qtutils.create_button(
            text=N_('Create Tag'), icon=icons.tag(), default=True
        )
        self.close_button = qtutils.close_button()

        # Form layout for inputs
        self.input_layout = qtutils.form(
            defs.margin,
            defs.spacing,
            (self.tag_name_label, self.tag_name),
            (self.tag_msg_label, self.tag_msg),
            (self.rev_label, self.revision),
            (self.sign_label, self.sign_tag),
        )

        self.button_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.close_button,
            qtutils.STRETCH,
            self.create_button,
        )

        self.main_layt = qtutils.vbox(
            defs.margin, defs.spacing, self.input_layout, self.button_layout
        )
        self.setLayout(self.main_layt)

        qtutils.connect_button(self.close_button, self.close)
        qtutils.connect_button(self.create_button, self.create_tag)

        settings = context.settings
        self.init_state(settings, self.resize, defs.scale(720), defs.scale(210))

    def create_tag(self):
        """Verifies inputs and emits a notifier tag message."""

        context = self.context
        revision = get(self.revision)
        tag_name = get(self.tag_name)
        tag_msg = get(self.tag_msg)
        sign_tag = get(self.sign_tag)

        ok = cmds.do(
            cmds.Tag, context, tag_name, revision, sign=sign_tag, message=tag_msg
        )
        if ok:
            self.close()
