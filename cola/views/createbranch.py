from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import qtutils
from cola.views import standard
from cola.widgets import defs


class CreateBranchView(standard.Dialog):
    """A dialog for creating branches."""

    def __init__(self, parent=None):
        standard.Dialog.__init__(self, parent=parent)

        self.setWindowTitle(self.tr('Create Branch'))

        self.resize(555, 333)
        self._main_layt = QtGui.QVBoxLayout(self)
        self._main_layt.setMargin(defs.margin)
        self._main_layt.setSpacing(defs.spacing)

        self._branch_name_layt = QtGui.QHBoxLayout()
        self._branch_name_label = QtGui.QLabel(self)
        self._branch_name_label.setText(self.tr('Branch Name'))
        self._branch_name_layt.addWidget(self._branch_name_label)

        # Exposed
        self.local_branch = QtGui.QLineEdit(self)
        self._branch_name_layt.addWidget(self.local_branch)

        self._main_layt.addLayout(self._branch_name_layt)
        self._rev_start_grp = QtGui.QGroupBox(self)
        self._rev_start_grp.setTitle(self.tr('Starting Revision'))

        self._rev_start_vbox_layt = QtGui.QVBoxLayout(self._rev_start_grp)
        self._rev_start_vbox_layt.setMargin(defs.margin)
        self._rev_start_vbox_layt.setSpacing(defs.spacing)

        self._rev_start_textinput_layt = QtGui.QHBoxLayout()
        self._rev_start_textinput_layt.setSpacing(defs.spacing)

        self._rev_label = QtGui.QLabel(self._rev_start_grp)
        self._rev_label.setText(self.tr('Revision Expression:'))
        self._rev_start_textinput_layt.addWidget(self._rev_label)

        # Exposed
        self.revision = QtGui.QLineEdit(self._rev_start_grp)
        self._rev_start_textinput_layt.addWidget(self.revision)
        self._rev_start_vbox_layt.addLayout(self._rev_start_textinput_layt)

        self._rev_start_radiobtn_layt = QtGui.QHBoxLayout()

        # Exposed
        self.local_radio = QtGui.QRadioButton(self._rev_start_grp)
        self.local_radio.setText(self.tr('Local Branch'))
        self.local_radio.setChecked(True)
        self._rev_start_radiobtn_layt.addWidget(self.local_radio)

        # Exposed
        self.remote_radio = QtGui.QRadioButton(self._rev_start_grp)
        self.remote_radio.setText(self.tr('Tracking Branch'))
        self._rev_start_radiobtn_layt.addWidget(self.remote_radio)

        # Exposed
        self.tag_radio = QtGui.QRadioButton(self._rev_start_grp)
        self.tag_radio.setText(self.tr('Tag'))
        self._rev_start_radiobtn_layt.addWidget(self.tag_radio)

        self._radio_spacer = QtGui.QSpacerItem(1, 1,
                                               QtGui.QSizePolicy.Expanding,
                                               QtGui.QSizePolicy.Minimum)
        self._rev_start_radiobtn_layt.addItem(self._radio_spacer)

        self._rev_start_vbox_layt.addLayout(self._rev_start_radiobtn_layt)

        # Exposed
        self.branch_list = QtGui.QListWidget(self._rev_start_grp)
        self._rev_start_vbox_layt.addWidget(self.branch_list)
        self._main_layt.addWidget(self._rev_start_grp)

        self._options_section_layt = QtGui.QHBoxLayout()
        self._options_section_layt.setMargin(defs.margin)
        self._options_section_layt.setSpacing(defs.spacing)

        self._option_grpbox = QtGui.QGroupBox(self)
        self._option_grpbox.setTitle(self.tr('Options'))

        self._options_grp_layt = QtGui.QVBoxLayout(self._option_grpbox)
        self._options_grp_layt.setMargin(defs.margin)
        self._options_grp_layt.setSpacing(defs.spacing)
        self._options_radio_layt = QtGui.QHBoxLayout()

        self._update_existing_label = QtGui.QLabel(self._option_grpbox)
        self._update_existing_label.setText(self.tr('Update Existing Branch:'))
        self._options_radio_layt.addWidget(self._update_existing_label)

        # Exposed
        self.no_update_radio = QtGui.QRadioButton(self._option_grpbox)
        self.no_update_radio.setText(self.tr('No'))
        self._options_radio_layt.addWidget(self.no_update_radio)

        # Exposed
        self.ffwd_only_radio = QtGui.QRadioButton(self._option_grpbox)
        self.ffwd_only_radio.setText(self.tr('Fast Forward Only'))
        self.ffwd_only_radio.setChecked(True)
        self._options_radio_layt.addWidget(self.ffwd_only_radio)

        # Exposed
        self.reset_radio = QtGui.QRadioButton(self._option_grpbox)
        self.reset_radio.setText(self.tr('Reset'))
        self._options_radio_layt.addWidget(self.reset_radio)

        self._options_grp_layt.addLayout(self._options_radio_layt)

        self._options_bottom_layt = QtGui.QHBoxLayout()
        self._options_checkbox_layt = QtGui.QVBoxLayout()

        self.fetch_checkbox = QtGui.QCheckBox(self._option_grpbox)
        self.fetch_checkbox.setText(self.tr('Fetch Tracking Branch'))
        self.fetch_checkbox.setChecked(True)
        self._options_checkbox_layt.addWidget(self.fetch_checkbox)

        self.checkout_checkbox = QtGui.QCheckBox(self._option_grpbox)
        self.checkout_checkbox.setText(self.tr('Checkout After Creation'))
        self.checkout_checkbox.setChecked(True)
        self._options_checkbox_layt.addWidget(self.checkout_checkbox)

        self._options_bottom_layt.addLayout(self._options_checkbox_layt)

        self._options_spacer = QtGui.QSpacerItem(1, 1,
                                                 QtGui.QSizePolicy.Expanding,
                                                 QtGui.QSizePolicy.Minimum)
        self._options_bottom_layt.addItem(self._options_spacer)

        self._options_grp_layt.addLayout(self._options_bottom_layt)
        self._options_section_layt.addWidget(self._option_grpbox)

        self._buttons_layt = QtGui.QHBoxLayout()
        self._buttons_layt.setMargin(defs.margin)
        self._buttons_layt.setSpacing(defs.spacing)

        # Exposed
        self.create_button = QtGui.QPushButton(self)
        self.create_button.setText(self.tr('Create Branch'))
        self.create_button.setIcon(qtutils.git_icon())
        self.create_button.setDefault(True)
        self._buttons_layt.addWidget(self.create_button)

        # Exposed
        self.cancel_button = QtGui.QPushButton(self)
        self.cancel_button.setText(self.tr('Cancel'))
        self._buttons_layt.addWidget(self.cancel_button)

        self._options_section_layt.addLayout(self._buttons_layt)
        self._main_layt.addLayout(self._options_section_layt)

        self.connect(self.cancel_button, SIGNAL('pressed()'), self.reject)


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    createbranch = CreateBranchView()
    createbranch.show()
    sys.exit(app.exec_())
