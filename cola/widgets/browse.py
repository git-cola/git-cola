from __future__ import division

import os

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import difftool
from cola import gitcmds
from cola import utils
from cola import qtutils
from cola.cmds import BaseCommand
from cola.compat import set
from cola.git import git
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.models.browse import GitRepoModel
from cola.models.browse import GitRepoEntryManager
from cola.models.browse import GitRepoNameItem
from cola.models.selection import State
from cola.models.selection import selection_model
from cola.widgets import defs
from cola.widgets import standard
from cola.widgets.selectcommits import select_commits


def worktree_browser_widget(parent, update=True):
    """Return a widget for immediate use."""
    view = Browser(parent, update=update)
    view.tree.setModel(GitRepoModel(view.tree))
    view.ctl = BrowserController(view.tree)
    return view


def worktree_browser(update=True):
    """Launch a new worktree browser session."""
    view = worktree_browser_widget(None, update=update)
    view.show()
    return view


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
        self.model = main.model()
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
        msg = N_('Repository: %s') % curdir
        msg += '\n'
        msg += N_('Branch: %s') % branch
        self.setToolTip(msg)

        title = N_('%s: %s - Browse') % (self.model.project, branch)
        if self.mode == self.model.mode_amend:
            title += ' (%s)' % N_('Amending')
        self.setWindowTitle(title)


class RepoTreeView(standard.TreeView):
    """Provides a filesystem-like view of a git repository."""

    def __init__(self, parent):
        standard.TreeView.__init__(self, parent)

        self.setRootIsDecorated(True)
        self.setSortingEnabled(False)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        # Observe model updates
        model = main.model()
        model.add_observer(model.message_updated, self.update_actions)

        # The non-Qt cola application model
        self.connect(self, SIGNAL('expanded(QModelIndex)'), self.size_columns)
        self.connect(self, SIGNAL('collapsed(QModelIndex)'), self.size_columns)

        # Sync selection before the key press event changes the model index
        self.connect(self, SIGNAL('indexAboutToChange()'), self.sync_selection)

        self.action_history =\
                self._create_action(
                        N_('View History...'),
                        N_('View history for selected path(s).'),
                        self.view_history,
                        'Shift+Ctrl+H')
        self.action_stage =\
                self._create_action(N_('Stage Selected'),
                                    N_('Stage selected path(s) for commit.'),
                                    self.stage_selected,
                                    cmds.Stage.SHORTCUT)
        self.action_unstage =\
                self._create_action(
                        N_('Unstage Selected'),
                        N_('Remove selected path(s) from the staging area.'),
                        self.unstage_selected,
                        'Ctrl+U')

        self.action_untrack =\
                self._create_action(N_('Untrack Selected'),
                                    N_('Stop tracking path(s)'),
                                    self.untrack_selected)

        self.action_difftool =\
                self._create_action(cmds.LaunchDifftool.name(),
                                    N_('Launch git-difftool on the current path.'),
                                    cmds.run(cmds.LaunchDifftool),
                                    cmds.LaunchDifftool.SHORTCUT)
        self.action_difftool_predecessor =\
                self._create_action(N_('Diff Against Predecessor...'),
                                    N_('Launch git-difftool against previous versions.'),
                                    self.difftool_predecessor,
                                    'Shift+Ctrl+D')
        self.action_revert =\
                self._create_action(N_('Revert Uncommitted Changes...'),
                                    N_('Revert changes to selected path(s).'),
                                    self.revert,
                                    'Ctrl+Z')
        self.action_editor =\
                self._create_action(cmds.LaunchEditor.name(),
                                    N_('Edit selected path(s).'),
                                    cmds.run(cmds.LaunchEditor),
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
        model = main.model()
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
        selection_model().set_selection(state)
        return paths

    def selectionChanged(self, old_selection, new_selection):
        """Override selectionChanged to update available actions."""
        result = QtGui.QTreeView.selectionChanged(self, old_selection, new_selection)
        self.update_actions()
        paths = self.sync_selection()

        if paths and self.model().path_is_interesting(paths[0]):
            cached = paths[0] in main.model().staged
            cmds.do(cmds.Diff, paths, cached)
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
        staged = utils.add_parents(set(main.model().staged))
        return [p for p in selection if p in staged]

    def selected_modified_paths(self, selection=None):
        """Return selected modified paths."""
        if not selection:
            selection = self.selected_paths()
        model = main.model()
        modified = utils.add_parents(set(model.modified))
        return [p for p in selection if p in modified]

    def selected_unstaged_paths(self, selection=None):
        """Return selected unstaged paths."""
        if not selection:
            selection = self.selected_paths()
        model = main.model()
        modified = utils.add_parents(set(model.modified))
        untracked = utils.add_parents(set(model.untracked))
        unstaged = modified.union(untracked)
        return [p for p in selection if p in unstaged]

    def selected_tracked_paths(self, selection=None):
        """Return selected tracked paths."""
        if not selection:
            selection = self.selected_paths()
        model = main.model()
        staged = set(self.selected_staged_paths())
        modified = set(self.selected_modified_paths())
        untracked = utils.add_parents(set(model.untracked))
        tracked = staged.union(modified)
        return [p for p in selection
                if p not in untracked or p in tracked]

    def _create_action(self, name, tooltip, slot, shortcut=None):
        """Create an action with a shortcut, tooltip, and callback slot."""
        action = QtGui.QAction(name, self)
        action.setStatusTip(tooltip)
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
        cmds.do(cmds.Stage, self.selected_unstaged_paths())

    def unstage_selected(self):
        """Signal that we should stage selected paths."""
        cmds.do(cmds.Unstage, self.selected_staged_paths())

    def untrack_selected(self):
        """untrack selected paths."""
        cmds.do(cmds.Untrack, self.selected_tracked_paths())

    def difftool_predecessor(self):
        """Diff paths against previous versions."""
        paths = self.selected_tracked_paths()
        self.emit(SIGNAL('difftool_predecessor'), paths)

    def revert(self):
        """Signal that we should revert changes to a path."""
        if not qtutils.confirm(N_('Revert Uncommitted Changes?'),
                               N_('This operation drops uncommitted changes.\n'
                                  'These changes cannot be recovered.'),
                               N_('Revert the uncommitted changes?'),
                               N_('Revert Uncommitted Changes'),
                               default=True,
                               icon=qtutils.icon('undo.svg')):
            return
        paths = self.selected_tracked_paths()
        cmds.do(cmds.Checkout, ['HEAD', '--'] + paths)

    def current_path(self):
        """Return the path for the current item."""
        index = self.currentIndex()
        if not index.isValid():
            return None
        return self.item_from_index(index).path


class BrowserController(QtCore.QObject):
    def __init__(self, view=None):
        QtCore.QObject.__init__(self, view)
        self.model = main.model()
        self.view = view
        self.updated = set()
        self.connect(view, SIGNAL('history(QStringList)'),
                     self.view_history)
        self.connect(view, SIGNAL('expanded(QModelIndex)'),
                     self.query_model)
        self.connect(view, SIGNAL('difftool_predecessor'),
                     self.difftool_predecessor)

    def view_history(self, entries):
        """Launch the configured history browser path-limited to entries."""
        entries = map(unicode, entries)
        cmds.do(cmds.VisualizePaths, entries)

    def query_model(self, model_index):
        """Update information about a directory as it is expanded."""
        item = self.view.item_from_index(model_index)
        path = item.path
        if path in self.updated:
            return
        self.updated.add(path)
        GitRepoEntryManager.entry(path).update()
        entry = GitRepoEntryManager.entry
        for row in xrange(item.rowCount()):
            path = item.child(row, 0).path
            entry(path).update()

    def difftool_predecessor(self, paths):
        """Prompt for an older commit and launch difftool against it."""
        args = ['--'] + paths
        revs, summaries = gitcmds.log_helper(all=False, extra_args=args)
        commits = select_commits(N_('Select Previous Version'),
                                 revs, summaries, multiselect=False)
        if not commits:
            return
        commit = commits[0]
        difftool.launch([commit, '--'] + paths)


class BrowseModel(object):
    def __init__(self, ref):
        self.ref = ref
        self.relpath = None
        self.filename = None


class SaveBlob(BaseCommand):
    def __init__(self, model):
        BaseCommand.__init__(self)
        self.model = model

    def do(self):
        model = self.model
        cmd = ['git', 'show', '%s:%s' % (model.ref, model.relpath)]
        with core.xopen(model.filename, 'wb') as fp:
            proc = core.start_command(cmd, stdout=fp)
            out, err = proc.communicate()

        status = proc.returncode
        msg = (N_('Saved "%(filename)s" from "%(ref)s" to "%(destination)s"') %
               dict(filename=model.relpath,
                    ref=model.ref,
                    destination=model.filename))
        Interaction.log_status(status, msg, '')

        Interaction.information(
                N_('File Saved'),
                N_('File saved to "%s"') % model.filename)



class BrowseDialog(QtGui.QDialog):

    @staticmethod
    def browse(ref):
        parent = qtutils.active_window()
        model = BrowseModel(ref)
        dlg = BrowseDialog(model, parent=parent)
        dlg_model = GitTreeModel(ref, dlg)
        dlg.setModel(dlg_model)
        dlg.setWindowTitle(N_('Browsing %s') % model.ref)
        if hasattr(parent, 'width'):
            dlg.resize(parent.width()*3//4, 333)
        else:
            dlg.resize(420, 333)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return dlg

    @staticmethod
    def select_file(ref):
        parent = qtutils.active_window()
        model = BrowseModel(ref)
        dlg = BrowseDialog(model, select_file=True, parent=parent)
        dlg_model = GitTreeModel(ref, dlg)
        dlg.setModel(dlg_model)
        dlg.setWindowTitle(N_('Select file from "%s"') % model.ref)
        dlg.resize(parent.width()*3//4, 333)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return model.filename

    @staticmethod
    def select_file_from_list(file_list, title=N_('Select File')):
        parent = qtutils.active_window()
        model = BrowseModel(None)
        dlg = BrowseDialog(model, select_file=True, parent=parent)
        dlg_model = GitFileTreeModel(dlg)
        dlg_model.add_files(file_list)
        dlg.setModel(dlg_model)
        dlg.expandAll()
        dlg.setWindowTitle(title)
        dlg.resize(parent.width()*3//4, 333)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return model.filename

    def __init__(self, model, select_file=False, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        # updated for use by commands
        self.model = model

        # widgets
        self.tree = GitTreeWidget(parent=self)
        self.close = QtGui.QPushButton(N_('Close'))
        self.save = QtGui.QPushButton(select_file and N_('Select') or N_('Save'))
        self.save.setDefault(True)
        self.save.setEnabled(False)

        # layouts
        self.btnlayt = QtGui.QHBoxLayout()
        self.btnlayt.addStretch()
        self.btnlayt.addWidget(self.close)
        self.btnlayt.addWidget(self.save)

        self.layt = QtGui.QVBoxLayout()
        self.layt.setMargin(defs.margin)
        self.layt.setSpacing(defs.spacing)
        self.layt.addWidget(self.tree)
        self.layt.addLayout(self.btnlayt)
        self.setLayout(self.layt)

        # connections
        if select_file:
            self.connect(self.tree, SIGNAL('path_chosen'), self.path_chosen)
        else:
            self.connect(self.tree, SIGNAL('path_chosen'), self.save_path)

        self.connect(self.tree, SIGNAL('selectionChanged()'),
                     self.selection_changed)

        qtutils.connect_button(self.close, self.reject)
        qtutils.connect_button(self.save, self.save_blob)

    def expandAll(self):
        self.tree.expandAll()

    def setModel(self, model):
        self.tree.setModel(model)

    def path_chosen(self, path, close=True):
        """Update the model from the view"""
        model = self.model
        model.relpath = path
        model.filename = path
        if close:
            self.accept()

    def save_path(self, path):
        """Choose an output filename based on the selected path"""
        self.path_chosen(path, close=False)
        model = self.model
        filename = qtutils.save_as(model.filename)
        if not filename:
            return
        model.filename = filename
        cmds.do(SaveBlob, model)
        self.accept()

    def save_blob(self):
        """Save the currently selected file"""
        filenames = self.tree.selected_files()
        if not filenames:
            return
        self.path_chosen(filenames[0], close=True)

    def selection_changed(self):
        """Update actions based on the current selection"""
        filenames = self.tree.selected_files()
        self.save.setEnabled(bool(filenames))


class GitTreeWidget(standard.TreeView):
    def __init__(self, parent=None):
        standard.TreeView.__init__(self, parent)
        self.setHeaderHidden(True)

        self.connect(self, SIGNAL('doubleClicked(const QModelIndex &)'),
                     self.double_clicked)

    def double_clicked(self, index):
        item = self.model().itemFromIndex(index)
        if item is None:
            return
        if item.is_dir:
            return
        self.emit(SIGNAL('path_chosen'), item.path)

    def selected_files(self):
        items = map(self.model().itemFromIndex, self.selectedIndexes())
        return [i.path for i in items if not i.is_dir]

    def selectionChanged(self, old_selection, new_selection):
        QtGui.QTreeView.selectionChanged(self, old_selection, new_selection)
        self.emit(SIGNAL('selectionChanged()'))

    def select_first_file(self):
        """Select the first filename in the tree"""
        model = self.model()
        idx = self.indexAt(QtCore.QPoint(0, 0))
        item = model.itemFromIndex(idx)
        while idx and idx.isValid() and item and item.is_dir:
            idx = self.indexBelow(idx)
            item = model.itemFromIndex(idx)

        if idx and idx.isValid() and item:
            self.setCurrentIndex(idx)


class GitFileTreeModel(QtGui.QStandardItemModel):
    """Presents a list of file paths as a hierarchical tree."""
    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.dir_entries = {'': self.invisibleRootItem()}
        self.dir_rows = {}

    def clear(self):
        QtGui.QStandardItemModel.clear(self)
        self.dir_rows = {}
        self.dir_entries = {'': self.invisibleRootItem()}

    def add_files(self, files):
        """Add a list of files"""
        add_file = self.add_file
        for f in files:
            add_file(f)

    def add_file(self, path):
        """Add a file to the model."""
        dirname = utils.dirname(path)
        dir_entries = self.dir_entries
        try:
            parent = dir_entries[dirname]
        except KeyError:
            parent = dir_entries[dirname] = self.create_dir_entry(dirname)

        row_items = self.create_row(path, False)
        parent.appendRow(row_items)

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""
        # Create model items
        row_items = self.create_row(path, True)

        # Insert directories before file paths
        try:
            row = self.dir_rows[parent]
        except KeyError:
            row = self.dir_rows[parent] = 0

        parent.insertRow(row, row_items)
        self.dir_rows[parent] += 1
        self.dir_entries[path] = row_items[0]

        return row_items[0]

    def create_row(self, path, is_dir):
        """Return a list of items representing a row."""
        return [GitTreeItem(path, is_dir)]

    def create_dir_entry(self, dirname):
        """
        Create a directory entry for the model.

        This ensures that directories are always listed before files.

        """
        entries = dirname.split('/')
        curdir = []
        parent = self.invisibleRootItem()
        curdir_append = curdir.append
        self_add_directory = self.add_directory
        dir_entries = self.dir_entries
        for entry in entries:
            curdir_append(entry)
            path = '/'.join(curdir)
            try:
                parent = dir_entries[path]
            except KeyError:
                grandparent = parent
                parent = self_add_directory(grandparent, path)
                dir_entries[path] = parent
        return parent


class GitTreeModel(GitFileTreeModel):
    def __init__(self, ref, parent):
        GitFileTreeModel.__init__(self, parent)
        self.ref = ref
        self._initialize()

    def _initialize(self):
        """Iterate over git-ls-tree and create GitTreeItems."""
        status, out, err = git.ls_tree('--full-tree', '-r', '-t', '-z',
                                       self.ref)
        if status != 0:
            Interaction.log_status(status, out, err)
            return

        if not out:
            return

        for line in out[:-1].split('\0'):
            # .....6 ...4 ......................................40
            # 040000 tree c127cde9a0c644a3a8fef449a244f47d5272dfa6	relative
            # 100644 blob 139e42bf4acaa4927ec9be1ec55a252b97d3f1e2	relative/path
            objtype = line[7]
            relpath = line[6 + 1 + 4 + 1 + 40 + 1:]
            if objtype == 't':
                parent = self.dir_entries[utils.dirname(relpath)]
                self.add_directory(parent, relpath)
            elif objtype == 'b':
                self.add_file(relpath)


class GitTreeItem(QtGui.QStandardItem):
    """
    Represents a cell in a treeview.

    Many GitRepoItems could map to a single repository path,
    but this tree only has a single column.
    Each GitRepoItem manages a different cell in the tree view.

    """
    def __init__(self, path, is_dir):
        QtGui.QStandardItem.__init__(self)
        self.is_dir = is_dir
        self.path = path
        self.setEditable(False)
        self.setDragEnabled(False)
        self.setText(utils.basename(path))
        if is_dir:
            self.setIcon(qtutils.dir_icon())
        else:
            self.setIcon(qtutils.file_icon())
