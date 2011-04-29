from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.views import standard


class OptionsView(standard.StandardDialog):
    def __init__(self, parent=None):
        standard.StandardDialog.__init__(self, parent=parent)
        #self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle(self.tr('Preferences'))
        self.resize(608, 425)

        self._main_layt = QtGui.QVBoxLayout(self)
        self._main_grid = QtGui.QGridLayout()
        self._diff_font_label = QtGui.QLabel(self)
        self._diff_font_label.setText(self.tr('Diff/Console Font'))
        self._main_grid.addWidget(self._diff_font_label, 0, 0, 1, 1)

        # Exposed
        self.global_cola_fontdiff_size = QtGui.QSpinBox(self)
        self.global_cola_fontdiff_size.setMinimum(8)
        self.global_cola_fontdiff_size.setProperty('value', QtCore.QVariant(12))
        self._main_grid.addWidget(self.global_cola_fontdiff_size, 0, 1, 1, 1)

        # Exposed
        self.global_cola_fontdiff = QtGui.QFontComboBox(self)
        self.global_cola_fontdiff.setFontFilters(QtGui.QFontComboBox.MonospacedFonts)
        self._main_grid.addWidget(self.global_cola_fontdiff, 0, 2, 1, 2)

        self._tab_width_label = QtGui.QLabel(self)
        self._tab_width_label.setText(self.tr('Tab Width'))
        self._main_grid.addWidget(self._tab_width_label, 1, 0, 1, 1)

        # Exposed
        self.global_cola_tabwidth = QtGui.QSpinBox(self)
        self.global_cola_tabwidth.setWrapping(True)
        self.global_cola_tabwidth.setMaximum(42)
        self.global_cola_tabwidth.setProperty('value', QtCore.QVariant(8))
        self._main_grid.addWidget(self.global_cola_tabwidth, 1, 1, 1, 1)

        # Exposed
        self.global_cola_savewindowsettings = QtGui.QCheckBox(self)
        self.global_cola_savewindowsettings.setText(self.tr('Save GUI Settings'))
        self._main_grid.addWidget(self.global_cola_savewindowsettings, 1, 2, 1, 1)

        # Exposed
        self.global_merge_keepbackup = QtGui.QCheckBox(self)
        self.global_merge_keepbackup.setText(self.tr('Save *.orig Merge Backups'))
        self._main_grid.addWidget(self.global_merge_keepbackup, 1, 3, 1, 1)

        self._editor_label = QtGui.QLabel(self)
        self._editor_label.setText(self.tr('Editor'))
        self._main_grid.addWidget(self._editor_label, 2, 0, 1, 1)

        # Exposed
        self.global_gui_editor = QtGui.QLineEdit(self)
        self._main_grid.addWidget(self.global_gui_editor, 2, 1, 1, 1)

        self._difftool_label = QtGui.QLabel(self)
        self._difftool_label.setText(self.tr('Diff Tool'))
        self._main_grid.addWidget(self._difftool_label, 2, 2, 1, 1)

        # Exposed
        self.global_diff_tool = QtGui.QLineEdit(self)
        self._main_grid.addWidget(self.global_diff_tool, 2, 3, 1, 1)

        self._historybrowser_label = QtGui.QLabel(self)
        self._historybrowser_label.setText(self.tr('History Browser'))
        self._main_grid.addWidget(self._historybrowser_label, 3, 0, 1, 1)

        # Exposed
        self.global_gui_historybrowser = QtGui.QLineEdit(self)
        self._main_grid.addWidget(self.global_gui_historybrowser,
                                  3, 1, 1, 1)

        self._mergetool_label = QtGui.QLabel(self)
        self._mergetool_label.setText(self.tr('Merge Tool'))
        self._main_grid.addWidget(self._mergetool_label, 3, 2, 1, 1)

        # Exposed
        self.global_merge_tool = QtGui.QLineEdit(self)
        self._main_grid.addWidget(self.global_merge_tool, 3, 3, 1, 1)

        self._main_layt.addLayout(self._main_grid)

        self._repo_horiz_layt = QtGui.QHBoxLayout()
        self._repo_horiz_layt.setSpacing(3)

        # Exposed
        self.local_groupbox = QtGui.QGroupBox(self)
        self.local_groupbox.setTitle(self.tr('Local Repository'))

        self._local_repo_layt = QtGui.QGridLayout(self.local_groupbox)

        self._local_user_name_label = QtGui.QLabel(self.local_groupbox)
        self._local_user_name_label.setText(self.tr('User Name'))
        self._local_repo_layt.addWidget(self._local_user_name_label,
                                        0, 0, 1, 1)

        # Exposed
        self.local_user_name = QtGui.QLineEdit(self.local_groupbox)

        self._local_repo_layt.addWidget(self.local_user_name,
                                        0, 1, 1, 2)

        self._local_user_email_label = QtGui.QLabel(self.local_groupbox)
        self._local_user_email_label.setText(self.tr('Email Address'))
        self._local_repo_layt.addWidget(self._local_user_email_label,
                                        1, 0, 1, 1)

        # Exposed
        self.local_user_email = QtGui.QLineEdit(self.local_groupbox)
        self._local_repo_layt.addWidget(self.local_user_email,
                                        1, 1, 1, 2)

        self._local_merge_verb_label = QtGui.QLabel(self.local_groupbox)
        self._local_merge_verb_label.setText(self.tr('Merge Verbosity'))
        self._local_repo_layt.addWidget(self._local_merge_verb_label,
                                        2, 0, 1, 2)

        # Exposed
        self.local_merge_verbosity = QtGui.QSpinBox(self.local_groupbox)
        self.local_merge_verbosity.setMinimum(0)
        self.local_merge_verbosity.setMaximum(5)
        self.local_merge_verbosity.setProperty('value', QtCore.QVariant(5))
        self._local_repo_layt.addWidget(self.local_merge_verbosity,
                                        2, 2, 1, 1)

        self._local_diffctxt_label = QtGui.QLabel(self.local_groupbox)
        self._local_diffctxt_label.setText(self.tr('Number of Diff Context Lines'))
        self._local_repo_layt.addWidget(self._local_diffctxt_label,
                                        3, 0, 1, 2)

        # Exposed
        self.local_gui_diffcontext = QtGui.QSpinBox(self.local_groupbox)
        self.local_gui_diffcontext.setMinimum(2)
        self.local_gui_diffcontext.setProperty('value', QtCore.QVariant(5))
        self._local_repo_layt.addWidget(self.local_gui_diffcontext,
                                        3, 2, 1, 1)

        # Exposed
        self.local_merge_summary = QtGui.QCheckBox(self.local_groupbox)
        self.local_merge_summary.setText(self.tr('Summarize Merge Commits'))
        self._local_repo_layt.addWidget(self.local_merge_summary,
                                        4, 0, 1, 2)

        # Exposed
        self.local_merge_diffstat = QtGui.QCheckBox(self.local_groupbox)
        self.local_merge_diffstat.setText(self.tr('Show Diffstat After Merge'))
        self._local_repo_layt.addWidget(self.local_merge_diffstat,
                                        5, 0, 1, 2)

        self._repo_horiz_layt.addWidget(self.local_groupbox)

        self._global_repo_grp = QtGui.QGroupBox(self)
        self._global_repo_grp.setTitle(self.tr('Global (All Repositories)'))

        self._global_repo_lyt = QtGui.QGridLayout(self._global_repo_grp)
        self._global_user_name_label = QtGui.QLabel(self._global_repo_grp)
        self._global_user_name_label.setText(self.tr('User Name'))
        self._global_repo_lyt.addWidget(self._global_user_name_label,
                                        0, 0, 1, 1)

        # Exposed
        self.global_user_name = QtGui.QLineEdit(self._global_repo_grp)
        self._global_repo_lyt.addWidget(self.global_user_name,
                                        0, 1, 1, 2)

        self._global_user_email_label = QtGui.QLabel(self._global_repo_grp)
        self._global_user_email_label.setText(self.tr('Email Address'))
        self._global_repo_lyt.addWidget(self._global_user_email_label,
                                        1, 0, 1, 1)

        # Exposed
        self.global_user_email = QtGui.QLineEdit(self._global_repo_grp)
        self._global_repo_lyt.addWidget(self.global_user_email,
                                        1, 1, 1, 2)

        self._global_merge_verb_label = QtGui.QLabel(self._global_repo_grp)
        self._global_merge_verb_label.setText(self.tr('Merge Verbosity'))
        self._global_repo_lyt.addWidget(self._global_merge_verb_label,
                                        2, 0, 1, 2)

        # Exposed
        self.global_merge_verbosity = QtGui.QSpinBox(self._global_repo_grp)
        self.global_merge_verbosity.setMinimum(0)
        self.global_merge_verbosity.setMaximum(5)
        self.global_merge_verbosity.setProperty('value', QtCore.QVariant(5))
        self._global_repo_lyt.addWidget(self.global_merge_verbosity,
                                        2, 2, 1, 1)

        self._global_diffctxt_label = QtGui.QLabel(self._global_repo_grp)
        self._global_diffctxt_label.setText(
                self.tr('Number of Diff Context Lines'))
        self._global_repo_lyt.addWidget(self._global_diffctxt_label,
                                        3, 0, 1, 2)

        # Exposed
        self.global_gui_diffcontext = QtGui.QSpinBox(self._global_repo_grp)
        self.global_gui_diffcontext.setMinimum(2)
        self.global_gui_diffcontext.setProperty('value', QtCore.QVariant(5))
        self._global_repo_lyt.addWidget(self.global_gui_diffcontext, 3, 2, 1, 1)

        # Exposed
        self.global_merge_summary = QtGui.QCheckBox(self._global_repo_grp)
        self.global_merge_summary.setText(self.tr('Summarize Merge Commits'))
        self._global_repo_lyt.addWidget(self.global_merge_summary, 4, 0, 1, 2)

        # Exposed
        self.global_merge_diffstat = QtGui.QCheckBox(self._global_repo_grp)
        self.global_merge_diffstat.setText(self.tr('Show Diffstat After Merge'))
        self._global_repo_lyt.addWidget(self.global_merge_diffstat, 5, 0, 1, 2)

        self._repo_horiz_layt.addWidget(self._global_repo_grp)
        self._main_layt.addLayout(self._repo_horiz_layt)

        # Save/Cancel buttons
        self._button_layt = QtGui.QHBoxLayout()
        self._button_spacer = QtGui.QSpacerItem(1, 1,
                                                QtGui.QSizePolicy.Expanding,
                                                QtGui.QSizePolicy.Minimum)
        self._button_layt.addItem(self._button_spacer)

        # Exposed
        self.save_button = QtGui.QPushButton(self)
        self.save_button.setText(self.tr('Save'))
        self.save_button.setDefault(True)
        self._button_layt.addWidget(self.save_button)

        # Exposed
        self.cancel_button = QtGui.QPushButton(self)
        self.cancel_button.setText(self.tr('Cancel'))
        self._button_layt.addWidget(self.cancel_button)
        self._main_layt.addLayout(self._button_layt)

        self.connect(self.cancel_button, SIGNAL('released()'), self.reject)


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    options = OptionsView()
    options.show()
    sys.exit(app.exec_())
