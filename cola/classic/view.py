import os

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import cmds
from cola import qtutils
from cola import signals
from cola import utils
from cola.cmds import run
from cola.models.selection import State
from cola.widgets import defs
from cola.widgets import standard
from cola.classic.model import GitRepoNameItem


class Browser(standard.Widget):
    def __init__(self, parent, update=True):
        standard.Widget.__init__(self, parent)
        self.tree = RepoTreeView(self)
        self.mainlayout = QtGui.QHBoxLayout()
        self.setLayout(self.mainlayout)
        self.mainlayout.setMargin(0)
        self.mainlayout.setSpacing(defs.spacing)
        self.mainlayout.addWidget(self.tree)
        self.resize(720, 420)

        self.connect(self, SIGNAL('updated'), self._updated_callback)
        self.model = cola.model()
        self.model.add_observer(self.model.message_updated, self.model_updated)
        qtutils.add_close_action(self)
        if update:
            self.model_updated()

    # Read-only mode property
    mode = property(lambda self: self.model.mode)

    def model_updated(self):
        """Update the title with the current branch and directory name."""
        self.emit(SIGNAL('updated'))

    def _updated_callback(self):
        branch = self.model.currentbranch
        curdir = os.getcwd()
        msg = 'Repository: %s\nBranch: %s' % (curdir, branch)

        self.setToolTip(msg)

        title = '%s: %s - Browse' % (self.model.project, branch)
        if self.mode == self.model.mode_amend:
            title += ' ** amending **'
        self.setWindowTitle(title)


class RepoTreeView(standard.TreeView):
    """Provides a filesystem-like view of a git repository."""
    def __init__(self, parent):
        standard.TreeView.__init__(self, parent)

        self.setSortingEnabled(False)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        # Observe model updates
        model = cola.model()
        model.add_observer(model.message_updated, self.update_actions)

        # The non-Qt cola application model
        self.connect(self, SIGNAL('expanded(QModelIndex)'), self.size_columns)
        self.connect(self, SIGNAL('collapsed(QModelIndex)'), self.size_columns)

        # Sync selection before the key press event changes the model index
        self.connect(self, SIGNAL('indexAboutToChange()'), self.sync_selection)

        self.action_history =\
                self._create_action('View History...',
                                    'View history for selected path(s).',
                                    self.view_history,
                                    'Shift+Ctrl+H')
        self.action_stage =\
                self._create_action('Stage Selected',
                                    'Stage selected path(s) for commit.',
                                    self.stage_selected,
                                    defs.stage_shortcut)
        self.action_unstage =\
                self._create_action('Unstage Selected',
                                    'Remove selected path(s) from '
                                    'the staging area.',
                                    self.unstage_selected,
                                    'Ctrl+U')

        self.action_untrack =\
                self._create_action('Untrack Selected',
                                    'Stop tracking path(s)',
                                    self.untrack_selected)

        self.action_difftool =\
                self._create_action(cmds.LaunchDifftool.NAME,
                                    'Launch git-difftool on the current path.',
                                    run(cmds.LaunchDifftool),
                                    cmds.LaunchDifftool.SHORTCUT)
        self.action_difftool_predecessor =\
                self._create_action('Diff Against Predecessor...',
                                    'Launch git-difftool against previous versions.',
                                    self.difftool_predecessor,
                                    'Shift+Ctrl+D')
        self.action_revert =\
                self._create_action('Revert Uncommitted Changes...',
                                    'Revert changes to selected path(s).',
                                    self.revert,
                                    'Ctrl+Z')
        self.action_editor =\
                self._create_action(cmds.LaunchEditor.NAME,
                                    'Edit selected path(s).',
                                    run(cmds.LaunchEditor),
                                    cmds.LaunchDifftool.SHORTCUT)

    def size_columns(self):
        """Set the column widths."""
        self.resizeColumnToContents(0)

    def update_actions(self):
        """Enable/disable actions."""
        selection = self.selected_paths()
        selected = bool(selection)
        staged = bool(self.selected_staged_paths(selection=selection))
        modified = bool(self.selected_modified_paths(selection=selection))
        unstaged = bool(self.selected_unstaged_paths(selection=selection))
        tracked = bool(self.selected_tracked_paths())

        self.action_history.setEnabled(selected)
        self.action_stage.setEnabled(unstaged)
        self.action_unstage.setEnabled(staged)
        self.action_untrack.setEnabled(tracked)
        self.action_difftool.setEnabled(staged or modified)
        self.action_difftool_predecessor.setEnabled(tracked)
        self.action_revert.setEnabled(tracked)

    def contextMenuEvent(self, event):
        """Create a context menu."""
        self.update_actions()
        menu = QtGui.QMenu(self)
        menu.addAction(self.action_editor)
        menu.addAction(self.action_stage)
        menu.addAction(self.action_unstage)
        menu.addSeparator()
        menu.addAction(self.action_history)
        menu.addAction(self.action_difftool)
        menu.addAction(self.action_difftool_predecessor)
        menu.addSeparator()
        menu.addAction(self.action_revert)
        menu.addAction(self.action_untrack)
        menu.exec_(self.mapToGlobal(event.pos()))

    def mousePressEvent(self, event):
        """Synchronize the selection on mouse-press."""
        result = QtGui.QTreeView.mousePressEvent(self, event)
        self.sync_selection()
        return result

    def sync_selection(self):
        """Push selection into the selection model."""
        staged = []
        unmerged = []
        modified = []
        untracked = []
        state = State(staged, unmerged, modified, untracked)

        paths = self.selected_paths()
        model = cola.model()
        model_staged = utils.add_parents(set(model.staged))
        model_modified = utils.add_parents(set(model.modified))
        model_unmerged = utils.add_parents(set(model.unmerged))
        model_untracked = utils.add_parents(set(model.untracked))

        for path in paths:
            if path in model_unmerged:
                unmerged.append(path)
            elif path in model_untracked:
                untracked.append(path)
            elif path in model_staged:
                staged.append(path)
            elif path in model_modified:
                modified.append(path)
            else:
                staged.append(path)
        # Push the new selection into the model.
        cola.selection_model().set_selection(state)
        return paths

    def selectionChanged(self, old_selection, new_selection):
        """Override selectionChanged to update available actions."""
        result = QtGui.QTreeView.selectionChanged(self, old_selection, new_selection)
        self.update_actions()
        paths = self.sync_selection()

        if paths and self.model().path_is_interesting(paths[0]):
            cached = paths[0] in cola.model().staged
            cola.notifier().broadcast(signals.diff, paths, cached)
        return result

    def setModel(self, model):
        """Set the concrete QAbstractItemModel instance."""
        QtGui.QTreeView.setModel(self, model)
        self.size_columns()

    def item_from_index(self, model_index):
        """Return the name item corresponding to the model index."""
        index = model_index.sibling(model_index.row(), 0)
        return self.model().itemFromIndex(index)

    def selected_paths(self):
        """Return the selected paths."""
        items = map(self.model().itemFromIndex, self.selectedIndexes())
        return [i.path for i in items
                    if i.type() == GitRepoNameItem.TYPE]

    def selected_staged_paths(self, selection=None):
        """Return selected staged paths."""
        if not selection:
            selection = self.selected_paths()
        staged = utils.add_parents(set(cola.model().staged))
        return [p for p in selection if p in staged]

    def selected_modified_paths(self, selection=None):
        """Return selected modified paths."""
        if not selection:
            selection = self.selected_paths()
        model = cola.model()
        modified = utils.add_parents(set(model.modified))
        return [p for p in selection if p in modified]

    def selected_unstaged_paths(self, selection=None):
        """Return selected unstaged paths."""
        if not selection:
            selection = self.selected_paths()
        model = cola.model()
        modified = utils.add_parents(set(model.modified))
        untracked = utils.add_parents(set(model.untracked))
        unstaged = modified.union(untracked)
        return [p for p in selection if p in unstaged]

    def selected_tracked_paths(self, selection=None):
        """Return selected tracked paths."""
        if not selection:
            selection = self.selected_paths()
        model = cola.model()
        staged = set(self.selected_staged_paths())
        modified = set(self.selected_modified_paths())
        untracked = utils.add_parents(set(model.untracked))
        tracked = staged.union(modified)
        return [p for p in selection
                if p not in untracked or p in tracked]

    def _create_action(self, name, tooltip, slot, shortcut=None):
        """Create an action with a shortcut, tooltip, and callback slot."""
        action = QtGui.QAction(self.tr(name), self)
        action.setStatusTip(self.tr(tooltip))
        if shortcut is not None:
            if hasattr(Qt, 'WidgetWithChildrenShortcut'):
                action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            action.setShortcut(shortcut)
        self.addAction(action)
        qtutils.connect_action(action, slot)
        return action

    def view_history(self):
        """Signal that we should view history for paths."""
        self.emit(SIGNAL('history(QStringList)'), self.selected_paths())

    def stage_selected(self):
        """Signal that we should stage selected paths."""
        cola.notifier().broadcast(signals.stage,
                                  self.selected_unstaged_paths())

    def unstage_selected(self):
        """Signal that we should stage selected paths."""
        cola.notifier().broadcast(signals.unstage,
                                  self.selected_staged_paths())

    def untrack_selected(self):
        """Signal that we should stage selected paths."""
        cola.notifier().broadcast(signals.untrack,
                                  self.selected_tracked_paths())

    def difftool_predecessor(self):
        """Diff paths against previous versions."""
        paths = self.selected_tracked_paths()
        self.emit(SIGNAL('difftool_predecessor'), paths)

    def revert(self):
        """Signal that we should revert changes to a path."""
        if not qtutils.confirm('Revert Uncommitted Changes?',
                               'This operation drops uncommitted changes.'
                               '\nThese changes cannot be recovered.',
                               'Revert the uncommitted changes?',
                               'Revert Uncommitted Changes',
                               default=True,
                               icon=qtutils.icon('undo.svg')):
            return
        paths = self.selected_tracked_paths()
        cola.notifier().broadcast(signals.checkout,
                                  ['HEAD', '--'] + paths)

    def current_path(self):
        """Return the path for the current item."""
        index = self.currentIndex()
        if not index.isValid():
            return None
        return self.item_from_index(index).path
