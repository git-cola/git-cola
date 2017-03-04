"""Provides the StashView dialog."""
from __future__ import division, absolute_import, unicode_literals

from qtpy import QtCore
from qtpy import QtWidgets

from .. import cmds
from .. import qtutils
from ..i18n import N_
from ..models.selection import selection_model
from . import defs
from .standard import Dialog


def gitignore_view():
    """Launches a gitignore dialog
    """
    view = AddToGitIgnore(parent=qtutils.active_window())
    view.show()
    view.raise_()
    return view


class AddToGitIgnore(Dialog):

    def __init__(self, parent=None):
        Dialog.__init__(self, parent=parent)
        if parent is not None:
            self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowTitle(N_('Add to .gitignore'))

        # Create text
        self.text_description = QtWidgets.QLabel()
        self.text_description.setText(N_('Ignore filename or pattern'))

        # Create edit filename
        self.edit_filename = QtWidgets.QLineEdit()
        self.check_filename()

        self.filename_layt = qtutils.vbox(defs.no_margin, defs.spacing,
                                          self.text_description,
                                          self.edit_filename)

        # Create radio options
        self.radio_filename = qtutils.radio(text=N_('Ignore exact filename'),
                                            checked=True)
        self.radio_pattern = qtutils.radio(text=N_('Ignore custom pattern'))

        self.radio_layt = qtutils.vbox(defs.no_margin, defs.spacing,
                                       self.radio_filename, self.radio_pattern)

        # Create buttons
        self.button_apply = qtutils.ok_button(text=N_('Add'))
        self.button_close = qtutils.close_button()
        self.btn_layt = qtutils.hbox(defs.no_margin, defs.spacing,
                                     qtutils.STRETCH,
                                     self.button_close,
                                     self.button_apply)

        # Layout
        self.main_layout = qtutils.vbox(defs.margin, defs.spacing,
                                        self.radio_layt,
                                        defs.button_spacing,
                                        self.filename_layt,
                                        qtutils.STRETCH,
                                        self.btn_layt)
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
        self.resize(width, max(400, height//2))

    def check_pattern(self):
        self.edit_filename.setDisabled(False)

    def check_filename(self):
        self.edit_filename.setText('/' + ';/'.join(selection_model().untracked))
        self.edit_filename.setDisabled(True)

    def close(self):
        self.reject()

    def apply(self):
        cmds.do(cmds.Ignore, self.edit_filename.text().split(';'))
        self.accept()
