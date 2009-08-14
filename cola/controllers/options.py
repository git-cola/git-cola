"""This module provides the controller for the options gui

"""

from PyQt4 import QtGui

from cola.views import OptionsView
from cola.qobserver import QObserver


def update_options(model, parent):
    """Launch the options window given a model and parent widget."""
    view = OptionsView(parent)
    ctl = OptionsController(model, view)
    view.show()
    return view.exec_() == QtGui.QDialog.Accepted


class OptionsController(QObserver):
    """Provides control to the options dialog."""

    def __init__(self, model, view):
        ## operate on a clone of the original model
        QObserver.__init__(self, model.clone(), view)

        ## used for telling about interactive font changes
        self._orig_model = model

        ## used to restore original values when cancelling
        self._backup_model = model.clone()

        ## config params modified by the gui
        self.add_observables('local_user_email',
                             'local_user_name',
                             'local_merge_summary',
                             'local_merge_diffstat',
                             'local_merge_verbosity',
                             'local_gui_diffcontext',
                             'global_user_email',
                             'global_user_name',
                             'global_merge_keepbackup',
                             'global_merge_summary',
                             'global_merge_diffstat',
                             'global_merge_verbosity',
                             'global_gui_editor',
                             'global_merge_tool',
                             'global_diff_tool',
                             'global_gui_diffcontext',
                             'global_gui_historybrowser',
                             'global_cola_fontdiff_size',
                             'global_cola_fontdiff',
                             'global_cola_fontui_size',
                             'global_cola_fontui',
                             'global_cola_savewindowsettings',
                             'global_cola_tabwidth')

        self.add_actions(global_cola_fontdiff = self.tell_parent_model)
        self.add_actions(global_cola_fontui = self.tell_parent_model)
        self.add_callbacks(save_button = self.save_settings)
        self.add_callbacks(global_cola_fontdiff_size = self.update_size)
        self.add_callbacks(global_cola_fontui_size = self.update_size)
        self.connect(self.view, 'rejected()', self.restore_settings)

        self.refresh_view()

    def refresh_view(self):
        """Apply the configured font and update widgets."""
        # The main application font
        font = self.model.cola_config('fontui')
        if font:
            fontui = QtGui.QFont()
            fontui.fromString(font)
            self.view.global_cola_fontui.setCurrentFont(fontui)
        # The fixed-width console font
        font = self.model.cola_config('fontdiff')
        if font:
            fontdiff = QtGui.QFont()
            fontdiff.fromString(font)
            self.view.global_cola_fontdiff.setCurrentFont(fontdiff)
        # Label the group box around the local repository
        self.view.local_groupbox.setTitle(unicode(self.tr('%s Repository'))
                                          % self.model.project)
        QObserver.refresh_view(self)

    # save button
    def save_settings(self):
        """Save updated config variables back to git."""
        params_to_save = []
        params = self.model.config_params()
        for param in params:
            value = self.model.param(param)
            backup = self._backup_model.param(param)
            if value != backup:
                params_to_save.append(param)
        for param in params_to_save:
            self.model.save_config_param(param)
        # Update the main model with any changed parameters
        self._orig_model.copy_params(self.model, params_to_save)
        self.view.done(QtGui.QDialog.Accepted)

    # cancel button -> undo changes
    def restore_settings(self):
        """Reverts any changes done in the Options dialog."""
        params = self._backup_model.config_params()
        self.model.copy_params(self._backup_model, params)
        self.tell_parent_model()

    def tell_parent_model(self,*rest):
        """Notifies the main app's model about changed parameters"""
        params= ('global_cola_fontdiff',
                 'global_cola_fontui',
                 'global_cola_fontdiff_size',
                 'global_cola_fontui_size',
                 'global_cola_savewindowsettings',
                 'global_cola_tabwidth',
                 )
        for param in params:
            self._orig_model.set_param(param, self.model.param(param))

    def update_size(self, *rest):
        """Updates fonts whenever font sizes change"""
        # The main app font combobox
        combo = self.view.global_cola_fontui
        param = unicode(combo.objectName())
        default = unicode(combo.currentFont().toString())
        self.model.apply_font_size(param, default)

        # The fixed-width console font combobox
        combo = self.view.global_cola_fontdiff
        param = unicode(combo.objectName())
        default = unicode(combo.currentFont().toString())
        self.model.apply_font_size(param, default)

        self.tell_parent_model()
