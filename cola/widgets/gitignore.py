"""Provides the StashView dialog."""
from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtCore
from qtpy import QtWidgets

from .. import cmds
from .. import qtutils
from ..i18n import N_
from . import defs
from .standard import Dialog


def gitignore_view(context):
    """Launches a gitignore dialog"""
    view = AddToGitIgnore(context, parent=qtutils.active_window())
    view.show()
    return view


class AddToGitIgnore(Dialog):
    def __init__(self, context, parent=None):
        Dialog.__init__(self, parent=parent)
        self.context = context
        self.selection = context.selection
        if parent is not None:
            self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowTitle(N_('Add to exclusions'))

        # Create text
        self.text_description = QtWidgets.QLabel()
        self.text_description.setText(N_('Ignore filename or pattern'))

        # Create edit filename
        self.edit_filename = QtWidgets.QLineEdit()
        self.check_filename()

        self.filename_layt = qtutils.vbox(
            defs.no_margin, defs.spacing, self.text_description, self.edit_filename
        )

        # Create radio options
        self.radio_filename = qtutils.radio(
            text=N_('Ignore exact filename'), checked=True
        )
        self.radio_pattern = qtutils.radio(text=N_('Ignore custom pattern'))
        self.name_radio_group = qtutils.buttongroup(
            self.radio_filename, self.radio_pattern
        )
        self.name_radio_layt = qtutils.vbox(
            defs.no_margin, defs.spacing, self.radio_filename, self.radio_pattern
        )

        self.radio_in_repo = qtutils.radio(text=N_('Add to .gitignore'), checked=True)
        self.radio_local = qtutils.radio(text=N_('Add to local ' '.git/info/exclude'))
        self.location_radio_group = qtutils.buttongroup(
            self.radio_in_repo, self.radio_local
        )
        self.location_radio_layt = qtutils.vbox(
            defs.no_margin, defs.spacing, self.radio_in_repo, self.radio_local
        )

        # Create buttons
        self.button_apply = qtutils.ok_button(text=N_('Add'))
        self.button_close = qtutils.close_button()
        self.btn_layt = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            qtutils.STRETCH,
            self.button_close,
            self.button_apply,
        )

        # Layout
        self.main_layout = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.name_radio_layt,
            defs.button_spacing,
            self.filename_layt,
            defs.button_spacing,
            self.location_radio_layt,
            qtutils.STRETCH,
            self.btn_layt,
        )
        self.setLayout(self.main_layout)

        # Connect actions
        qtutils.connect_toggle(self.radio_pattern, self.check_pattern)
        qtutils.connect_toggle(self.radio_filename, self.check_filename)
        qtutils.connect_button(self.button_apply, self.apply)
        qtutils.connect_button(self.button_close, self.close)

        self.init_state(None, self.resize_widget, parent)

    def resize_widget(self, parent):
        """Set the initial size of the widget"""
        width, height = qtutils.default_size(parent, 720, 400)
        self.resize(width, max(400, height // 2))

    def check_pattern(self):
        self.edit_filename.setDisabled(False)

    def check_filename(self):
        self.edit_filename.setText('/' + ';/'.join(self.selection.untracked))
        self.edit_filename.setDisabled(True)

    def close(self):
        self.reject()

    def apply(self):
        context = self.context
        cmds.do(
            cmds.Ignore,
            context,
            self.edit_filename.text().split(';'),
            self.radio_local.isChecked(),
        )
        self.accept()
