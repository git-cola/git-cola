import os

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import qtutils
from cola import signals
from cola import utils
from cola.views import standard
from cola.classic.model import GitRepoNameItem


class RepoDialog(standard.Dialog):
    def __init__(self, parent=None, update=True):
        standard.Dialog.__init__(self, parent)
        self.setObjectName('classic')
        self.tree = RepoTreeView(parent)
        self.setLayout(QtGui.QHBoxLayout())
        self.layout().setMargin(1)
        self.layout().addWidget(self.tree)
        self.resize(720, 420)

        self.connect(self, SIGNAL('updated'), self._updated_callback)
        self.model = cola.model()
        self.model.add_message_observer(self.model.message_updated,
                                        self._model_updated)
        qtutils.add_close_action(self)
        if update:
            self._model_updated()

    # Read-only mode property
    mode = property(lambda self: self.model.mode)

    def _model_updated(self):
        """Update the title with the current branch and directory name."""
        self.emit(SIGNAL('updated'))

    def _updated_callback(self):
        branch = self.model.currentbranch
        curdir = os.getcwd()
        msg = 'Repository: %s\nBranch: %s' % (curdir, branch)

        self.setToolTip(msg)

        title = '%s [%s]' % (self.model.project, branch)
        if self.mode in (self.model.mode_diff, self.model.mode_diff_expr):
            title += ' *** diff mode***'
        elif self.mode == self.model.mode_review:
            title += ' *** review mode***'
        elif self.mode == self.model.mode_amend:
            title += ' *** amending ***'
        self.setWindowTitle(title)


class RepoTreeView(QtGui.QTreeView):
    """Provides a filesystem-like view of a git repository."""
    def __init__(self, parent=None):
        QtGui.QTreeView.__init__(self, parent)

        self.setSortingEnabled(False)
        self.setAllColumnsShowFocus(True)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        # Observe model updates
        model = cola.model()
        model.add_message_observer(model.message_updated,
                                   self.update_actions)

        # The non-Qt cola application model
        self.connect(self, SIGNAL('expanded(QModelIndex)'), self.size_columns)
        self.connect(self, SIGNAL('collapsed(QModelIndex)'), self.size_columns)
        self.action_history =\
                self._create_action('View History...',
                                    'View history for selected path(s).',
                                    self.view_history,
                                    'Shift+Ctrl+H')
        self.action_stage =\
                self._create_action('Stage Selected',
                                    'Stage selected path(s) for commit.',
                                    self.stage_selected,
                                    'Ctrl+S')
        self.action_unstage =\
                self._create_action('Unstage Selected',
                                    'Remove selected path(s) from '
                                    'the staging area.',
                                    self.unstage_selected,
                                    'Ctrl+U')
        self.action_difftool =\
                self._create_action('View Diff...',
                                    'Launch git-difftool on the current path.',
                                    self.difftool,
                                    'Ctrl+D')
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
                self._create_action('Launch Editor',
                                    'Edit selected path(s).',
                                    self.editor,
                                    'Ctrl+E')

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
        menu.exec_(self.mapToGlobal(event.pos()))

    def keyPressEvent(self, event):
        """
        Override keyPressEvent to allow LeftArrow to work on non-directories.

        When LeftArrow is pressed on a file entry or an unexpanded directory,
        then move the current index to the parent directory.

        This simplifies navigation using the keyboard.
        For power-users, we support Vim keybindings ;-P

        """
        # Check whether the item is expanded before calling the base class
        # keyPressEvent otherwise we end up collapsing and changing the
        # current index in one shot, which we don't want to do.
        index = self.currentIndex()
        was_expanded = self.isExpanded(index)
        was_collapsed = not was_expanded

        # Vim keybindings...
        # Rewrite the event before marshalling to QTreeView.event()
        key = event.key()

        # Remap 'H' to 'Left'
        if key == QtCore.Qt.Key_H:
            event = QtGui.QKeyEvent(event.type(),
                                    QtCore.Qt.Key_Left,
                                    event.modifiers())
        # Remap 'J' to 'Down'
        elif key == QtCore.Qt.Key_J:
            event = QtGui.QKeyEvent(event.type(),
                                    QtCore.Qt.Key_Down,
                                    event.modifiers())
        # Remap 'K' to 'Up'
        elif key == QtCore.Qt.Key_K:
            event = QtGui.QKeyEvent(event.type(),
                                    QtCore.Qt.Key_Up,
                                    event.modifiers())
        # Remap 'L' to 'Right'
        elif key == QtCore.Qt.Key_L:
            event = QtGui.QKeyEvent(event.type(),
                                    QtCore.Qt.Key_Right,
                                    event.modifiers())

        # Re-read the event key to take the remappings into account
        key = event.key()

        # Process the keyPressEvent before changing the current index
        # otherwise the event will affect the new index set here
        # instead of the original index.
        result = QtGui.QTreeView.keyPressEvent(self, event)

        # Sync the selection model
        self.sync_selection()

        # Try to select the first item if the model index is invalid
        if not index.isValid():
            index = self.model().index(0, 0, QtCore.QModelIndex())
            if index.isValid():
                self.setCurrentIndex(index)
            return result

        # Automatically select the first entry when expanding a directory
        if (key == QtCore.Qt.Key_Right and was_collapsed and
                self.isExpanded(index)):
            index = self.moveCursor(self.MoveDown, event.modifiers())
            self.setCurrentIndex(index)

        # Process non-root entries with valid parents only.
        if key == QtCore.Qt.Key_Left and index.parent().isValid():

            # File entries have rowCount() == 0
            if self.item_from_index(index).rowCount() == 0:
                self.setCurrentIndex(index.parent())

            # Otherwise, do this for collapsed directories only
            elif was_collapsed:
                self.setCurrentIndex(index.parent())

        return result

    def mousePressEvent(self, event):
        """Synchronize the selection on mouse-press."""
        result = QtGui.QTreeView.mousePressEvent(self, event)
        self.sync_selection()
        return result

    def sync_selection(self):
        """Push selection into the selection model."""
        staged = []
        modified = []
        unmerged = []
        untracked = []
        paths = self.selected_paths()

        model = cola.model()
        model_staged = utils.add_parents(set(model.staged))
        model_modified = utils.add_parents(set(model.modified))
        model_unmerged = utils.add_parents(set(model.unmerged))
        model_untracked =utils.add_parents(set(model.untracked))

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
        cola.selection_model().set_selection(staged, modified,
                                             unmerged, untracked)
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

    def _create_action(self, name, tooltip, slot, shortcut):
        """Create an action with a shortcut, tooltip, and callback slot."""
        action = QtGui.QAction(self.tr(name), self)
        action.setStatusTip(self.tr(tooltip))
        if hasattr(Qt, 'WidgetWithChildrenShortcut'):
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        action.setShortcut(shortcut)
        self.addAction(action)
        self.connect(action, SIGNAL('triggered()'), slot)
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

    def difftool(self):
        """Signal that we should launch difftool on a path."""
        cola.notifier().broadcast(signals.difftool,
                                  False,
                                  self.selected_tracked_paths())

    def difftool_predecessor(self):
        """Diff paths against previous versions."""
        paths = self.selected_tracked_paths()
        self.emit(SIGNAL('difftool_predecessor'), paths)

    def revert(self):
        """Signal that we should revert changes to a path."""
        if not cola.qtutils.question(self,
                                     'Revert Local Changes?',
                                     'This operation will drop '
                                     'uncommitted changes.\n'
                                     'This cannot be undone.\n'
                                     'Continue?',
                                     default=False):
            return
        paths = self.selected_tracked_paths()
        cola.notifier().broadcast(signals.checkout,
                                  ['HEAD', '--'] + paths)

    def editor(self):
        """Signal that we should edit selected paths using an external editor."""
        cola.notifier().broadcast(signals.edit, self.selected_paths())

    def current_path(self):
        """Return the path for the current item."""
        index = self.currentIndex()
        if not index.isValid():
            return None
        return self.item_from_index(index).path
