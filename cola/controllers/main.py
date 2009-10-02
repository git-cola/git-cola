"""Provides the main application controller."""

import os
import sys
import glob

from PyQt4 import QtGui
from PyQt4 import QtCore

import cola
from cola import core
from cola import utils
from cola import qtutils
from cola import version
from cola import difftool
from cola import settings
from cola import signals
from cola.qobserver import QObserver
from cola.views import log


class MainController(QObserver):
    """Manage interactions between models and views."""

    def __init__(self, model, view):
        """Initializes the MainController's internal data."""
        QObserver.__init__(self, model, view)

        # Binds model params to their equivalent view widget
        self.add_observables('commitmsg')

        # When a model attribute changes, this runs a specific action
        self.add_actions(global_cola_fontdiff = self.update_diff_font)
        self.add_actions(global_cola_tabwidth = self.update_tab_width)

        #TODO move thread shutdown out of this class
        self.add_callbacks(menu_quit = self.quit_app)
        # Route events here
        view.closeEvent = self.quit_app
        self._init_log_window()
        self.refresh_view('global_cola_fontdiff') # Update the diff font

    def quit_app(self, *args):
        """Save config settings and cleanup temp files."""
        if self.model.remember_gui_settings():
            settings.SettingsManager.save_gui_state(self.view)

        # Remove any cola temp files
        pattern = self.model.tmp_file_pattern()
        for filename in glob.glob(pattern):
            os.unlink(filename)

        self.view.close()

    def update_diff_font(self):
        """Updates the diff font based on the configured value."""
        qtutils.set_diff_font(qtutils.logger())
        qtutils.set_diff_font(self.view.display_text)
        qtutils.set_diff_font(self.view.commitmsg)

    def update_tab_width(self):
        """Implement the variable-tab-width setting."""
        tab_width = self.model.cola_config('tabwidth')
        display_font = self.view.display_text.font()
        space_width = QtGui.QFontMetrics(display_font).width(' ')
        self.view.display_text.setTabStopWidth(tab_width * space_width)

    def _init_log_window(self):
        """Initialize the logging subwindow."""
        branch = self.model.currentbranch
        qtutils.log(0, self.model.git_version +
                    '\ncola version ' + version.version())
