"""This view provides the main git-cola user interface.
"""
import os

from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

import cola
from cola import core
from cola import gitcmds
from cola import utils
from cola import settings
from cola import signals
from cola import version
from cola.qtutils import connect_button
from cola.qtutils import emit
from cola.qtutils import log
from cola.views import actions as actions
from cola.views.mainwindow import MainWindow


class MainView(MainWindow):
    """The main cola interface."""

    # Read-only mode property
    mode = property(lambda self: self.model.mode)

    def __init__(self, model, parent=None):
        MainWindow.__init__(self, model, parent)
        self._has_threadpool = hasattr(QtCore, 'QThreadPool')

        # Keeps track of merge messages we've seen
        self.merge_message_hash = ''

        # Internal field used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self._widget_version = 1

        model.add_message_observer(model.message_updated,
                                   self._update_view)

        connect_button(self.stage_button, self.stage)
        connect_button(self.unstage_button, self.unstage)

        self.connect(self, SIGNAL('update'), self._update_callback)
        self.connect(self, SIGNAL('import_state'), self.import_state)
        self.connect(self, SIGNAL('install_config_actions'),
                     self._install_config_actions)

        # Install .git-config-defined actions
        self._config_task = None
        self.install_config_actions()

        # Restore saved settings
        self._gui_state_task = None
        self._load_gui_state()

        log(0, self.model.git_version + '\ncola version ' + version.version())

    def install_config_actions(self):
        """Install .gitconfig-defined actions"""
        if self._has_threadpool:
            self._config_task = self._start_config_actions_task()
        else:
            names = actions.get_config_actions()
            self._install_config_actions(names)

    def _start_config_actions_task(self):
        """Do the expensive "get_config_actions()" call in the background"""
        class ConfigActionsTask(QtCore.QRunnable):
            def __init__(self, sender):
                QtCore.QRunnable.__init__(self)
                self._sender = sender
            def run(self):
                names = actions.get_config_actions()
                self._sender.emit(SIGNAL('install_config_actions'), names)

        task = ConfigActionsTask(self)
        QtCore.QThreadPool.globalInstance().start(task)
        return task

    def _install_config_actions(self, names):
        """Install .gitconfig-defined actions"""
        if not names:
            return
        menu = self.actions_menu
        menu.addSeparator()
        for name in names:
            menu.addAction(name, emit(self, signals.run_config_action, name))

    def _update_view(self):
        self.emit(SIGNAL('update'))

    def _update_callback(self):
        """Update the title with the current branch and directory name."""
        branch = self.model.currentbranch
        curdir = core.decode(os.getcwd())
        msg = 'Repository: %s\nBranch: %s' % (curdir, branch)
        self.commitdockwidget.setToolTip(msg)

        title = '%s [%s]' % (self.model.project, branch)
        if self.mode in (self.model.mode_diff, self.model.mode_diff_expr):
            title += ' *** diff mode***'
        elif self.mode == self.model.mode_review:
            title += ' *** review mode***'
        elif self.mode == self.model.mode_amend:
            title += ' *** amending ***'
        self.setWindowTitle(title)

        self.commitmsgeditor.set_mode(self.mode)

        if not self.model.read_only() and self.mode != self.model.mode_amend:
            # Check if there's a message file in .git/
            merge_msg_path = gitcmds.merge_message_path()
            if merge_msg_path is None:
                return
            merge_msg_hash = utils.checksum(core.decode(merge_msg_path))
            if merge_msg_hash == self.merge_message_hash:
                return
            self.merge_message_hash = merge_msg_hash
            cola.notifier().broadcast(signals.load_commit_message,
                                      core.decode(merge_msg_path))

    def import_state(self, state):
        """Imports data for save/restore"""
        MainWindow.import_state(self, state)
        # Restore the dockwidget, etc. window state
        if 'windowstate' in state:
            windowstate = state['windowstate']
            self.restoreState(QtCore.QByteArray.fromBase64(str(windowstate)),
                              self._widget_version)

    def export_state(self):
        """Exports data for save/restore"""
        state = MainWindow.export_state(self)
        # Save the window state
        windowstate = self.saveState(self._widget_version)
        state['windowstate'] = unicode(windowstate.toBase64().data())
        return state

    def _load_gui_state(self):
        """Restores the gui from the preferences file."""
        if self._has_threadpool:
            self._gui_state_task = self._start_gui_state_loading_thread()
        else:
            state = settings.SettingsManager.gui_state(self)
            self.import_state(state)

    def _start_gui_state_loading_thread(self):
        """Do expensive file reading and json decoding in the background"""
        class LoadGUIStateTask(QtCore.QRunnable):
            def __init__(self, sender):
                QtCore.QRunnable.__init__(self)
                self._sender = sender
            def run(self):
                state = settings.SettingsManager.gui_state(self._sender)
                self._sender.emit(SIGNAL('import_state'), state)

        task = LoadGUIStateTask(self)
        QtCore.QThreadPool.globalInstance().start(task)
        return task

    def stage(self):
        """Stage selected files, or all files if no selection exists."""
        paths = cola.selection_model().unstaged
        if not paths:
            cola.notifier().broadcast(signals.stage_modified)
        else:
            cola.notifier().broadcast(signals.stage, paths)

    def unstage(self):
        """Unstage selected files, or all files if no selection exists."""
        paths = cola.selection_model().staged
        if not paths:
            cola.notifier().broadcast(signals.unstage_all)
        else:
            cola.notifier().broadcast(signals.unstage, paths)

    def dragEnterEvent(self, event):
        """Accepts drops"""
        MainWindow.dragEnterEvent(self, event)
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Apply dropped patches with git-am"""
        event.accept()
        urls = event.mimeData().urls()
        if not urls:
            return
        paths = map(lambda x: unicode(x.path()), urls)
        patches = [p for p in paths if p.endswith('.patch')]
        dirs = [p for p in paths if os.path.isdir(p)]
        dirs.sort()
        for d in dirs:
            patches.extend(self._gather_patches(d))
        # Broadcast the patches to apply
        cola.notifier().broadcast(signals.apply_patches, patches)

    def _gather_patches(self, path):
        """Find patches in a subdirectory"""
        patches = []
        for root, subdirs, files in os.walk(path):
            for name in [f for f in files if f.endswith('.patch')]:
                patches.append(os.path.join(root, name))
        return patches
