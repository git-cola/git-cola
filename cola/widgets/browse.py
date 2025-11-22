import shlex
import shutil

from qtpy.QtCore import Qt
from qtpy.QtCore import Signal
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

from ..models.browse import GitRepoModel
from ..models.browse import GitRepoNameItem
from ..models.selection import State
from ..i18n import N_
from ..models import dag
from ..interaction import Interaction
from .. import cmds
from .. import core
from .. import difftool
from .. import gitcmds
from .. import hotkeys
from .. import icons
from .. import utils
from .. import qtutils
from .selectcommits import select_commits
from . import common
from . import defs
from . import standard


def worktree_browser(context, parent=None, update=True, show=True):
    """Create a new worktree browser"""
    view = Browser(context, parent, update=update)
    if parent is None:
        context.browser_windows.append(view)
        view.closed.connect(context.browser_windows.remove)
    model = GitRepoModel(context, view.tree)
    view.set_model(model)
    if update:
        view.refresh()
    if show:
        view.show()
    return view


def save_path(context, path, model):
    """Choose an output filename based on the selected path"""
    filename = qtutils.save_as(path)
    if filename:
        model.filename = filename
        cmds.do(SaveBlob, context, model)
        result = True
    else:
        result = False
    return result


class Browser(standard.Widget):
    """A repository branch file browser. Browses files provided by GitRepoModel"""

    # Read-only mode property
    mode = property(lambda self: self.model.mode)

    def __init__(self, context, parent, update=True):
        standard.Widget.__init__(self, parent)
        self.tree = RepoTreeView(context, self)
        self.mainlayout = qtutils.hbox(defs.no_margin, defs.spacing, self.tree)
        self.setLayout(self.mainlayout)

        self.model = context.model
        self.model.updated.connect(self._updated_callback, type=Qt.QueuedConnection)
        if parent is None:
            qtutils.add_close_action(self)
        if update:
            self._updated_callback()

        self.init_state(context.settings, self.resize, 720, 420)

    def set_model(self, model):
        """Set the model"""
        self.tree.set_model(model)

    def refresh(self):
        """Refresh the model triggering view updates"""
        self.tree.refresh()

    def _updated_callback(self):
        branch = self.model.currentbranch
        curdir = core.getcwd()
        msg = N_('Repository: %s') % curdir
        msg += '\n'
        msg += N_('Branch: %s') % branch
        self.setToolTip(msg)

        scope = {
            'project': self.model.project,
            'branch': branch,
        }
        title = N_('%(project)s: %(branch)s - Browse') % scope
        if self.mode == self.model.mode_amend:
            title += ' %s' % N_('(Amending)')
        self.setWindowTitle(title)


class RepoTreeView(standard.TreeView):
    """Provides a filesystem-like view of a git repository."""

    def __init__(self, context, parent):
        standard.TreeView.__init__(self, parent)

        self.context = context
        self.selection = context.selection
        self.saved_selection = []
        self.saved_current_path = None
        self.saved_open_folders = set()
        self.restoring_selection = False
        self._column_widths = []
        self._columns_sized = False

        self.setDragEnabled(True)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(False)
        self.setSelectionMode(self.ExtendedSelection)

        # Observe model updates
        model = context.model
        model.about_to_update.connect(self.save_state, type=Qt.QueuedConnection)
        model.updated.connect(self.update_actions, type=Qt.QueuedConnection)
        self.expanded.connect(self.index_expanded)

        self.collapsed.connect(lambda idx: self.size_columns())
        self.collapsed.connect(self.index_collapsed)

        # Sync selection before the key press event changes the model index
        queued = Qt.QueuedConnection
        self.index_about_to_change.connect(self.sync_selection, type=queued)

        self.action_history = qtutils.add_action_with_tooltip(
            self,
            N_('View History...'),
            N_('View history for selected paths'),
            self.view_history,
            hotkeys.HISTORY,
        )

        self.action_stage = qtutils.add_action_with_tooltip(
            self,
            cmds.StageOrUnstage.name(),
            N_('Stage/unstage selected paths for commit'),
            cmds.run(cmds.StageOrUnstage, context),
            hotkeys.STAGE_SELECTION,
        )

        self.action_untrack = qtutils.add_action_with_tooltip(
            self,
            N_('Untrack Selected'),
            N_('Stop tracking paths'),
            self.untrack_selected,
        )

        self.action_rename = qtutils.add_action_with_tooltip(
            self, N_('Rename'), N_('Rename selected paths'), self.rename_selected
        )

        self.action_difftool = qtutils.add_action_with_tooltip(
            self,
            difftool.LaunchDifftool.name(),
            N_('Launch git-difftool on the current path'),
            cmds.run(difftool.LaunchDifftool, context),
            hotkeys.DIFF,
        )

        self.action_difftool_predecessor = qtutils.add_action_with_tooltip(
            self,
            N_('Diff Against Predecessor...'),
            N_('Launch git-difftool against previous versions'),
            self.diff_predecessor,
            hotkeys.DIFF_SECONDARY,
        )

        self.action_revert_unstaged = qtutils.add_action_with_tooltip(
            self,
            cmds.RevertUnstagedEdits.name(),
            N_('Revert unstaged changes to selected paths'),
            cmds.run(cmds.RevertUnstagedEdits, context),
            hotkeys.REVERT,
            hotkeys.REVERT_ALT,
        )

        self.action_revert_uncommitted = qtutils.add_action_with_tooltip(
            self,
            cmds.RevertUncommittedEdits.name(),
            N_('Revert uncommitted changes to selected paths'),
            cmds.run(cmds.RevertUncommittedEdits, context),
            hotkeys.UNDO,
        )

        self.action_editor = qtutils.add_action_with_tooltip(
            self,
            cmds.LaunchEditor.name(),
            N_('Edit selected paths'),
            cmds.run(cmds.LaunchEditor, context),
            hotkeys.EDIT,
        )

        self.action_blame = qtutils.add_action_with_tooltip(
            self,
            cmds.BlamePaths.name(),
            N_('Blame selected paths'),
            cmds.run(cmds.BlamePaths, context),
        )

        self.action_refresh = common.refresh_action(context, self)

        self.action_default_app = common.default_app_action(
            context, self, self.selected_paths
        )

        self.action_parent_dir = common.parent_dir_action(
            context, self, self.selected_paths
        )

        self.action_terminal = common.terminal_action(
            context, self, func=self.selected_paths
        )

        self.x_width = qtutils.text_width(self.font(), 'x')
        self.size_columns(force=True)

    def index_expanded(self, index):
        """Update information about a directory as it is expanded."""
        # Remember open folders so that we can restore them when refreshing
        item = self.name_item_from_index(index)
        self.saved_open_folders.add(item.path)
        self.size_columns()

        # update information about a directory as it is expanded
        if item.cached:
            return
        path = item.path

        model = self.model()
        model.populate(item)
        model.update_entry(path)

        for row in range(item.rowCount()):
            path = item.child(row, 0).path
            model.update_entry(path)

        item.cached = True

    def index_collapsed(self, index):
        item = self.name_item_from_index(index)
        self.saved_open_folders.remove(item.path)

    def refresh(self):
        self.model().refresh()

    def size_columns(self, force=False):
        """Set the column widths."""
        cfg = self.context.cfg
        should_resize = cfg.get('cola.resizebrowsercolumns', default=False)
        if not force and not should_resize:
            return
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)
        self.resizeColumnToContents(4)

    def sizeHintForColumn(self, column):
        x_width = self.x_width

        if column == 1:
            # Status
            size = x_width * 11
        elif column == 2:
            # Summary
            size = x_width * 64
        elif column == 3:
            # Author
            size = x_width * 18
        elif column == 4:
            # Age
            size = x_width * 16
        else:
            # Filename and others use the actual content
            size = super().sizeHintForColumn(column)
        return size

    def save_state(self):
        selection = self.selected_paths()
        if selection:
            self.saved_selection = selection

        current = self.current_item()
        if current:
            self.saved_current_path = current.path

        self._column_widths = [
            self.columnWidth(x) for x in range(self.header().count())
        ]

    def restore_state(self):
        selection = self.selectionModel()
        flags = selection.Select | selection.Rows

        self.restoring_selection = True

        # Restore opened folders
        model = self.model()
        for path in sorted(self.saved_open_folders):
            row = model.get(path)
            if not row:
                continue
            index = row[0].index()
            if index.isValid():
                self.setExpanded(index, True)

        # Restore the current item.  We do this first, otherwise
        #  setCurrentIndex() can mess with the selection we set below
        current_index = None
        current_path = self.saved_current_path
        if current_path:
            row = model.get(current_path)
            if row:
                current_index = row[0].index()

        if current_index and current_index.isValid():
            self.setCurrentIndex(current_index)

        # Restore selected items
        for path in self.saved_selection:
            row = model.get(path)
            if not row:
                continue
            index = row[0].index()
            if index.isValid():
                self.scrollTo(index)
                selection.select(index, flags)

        self.restoring_selection = False

        # After the initial resize then _columns_sized will be True.
        if self._columns_sized:
            # The widths have to be restored when new files are added. The model
            # responds to model updates and detects when the list of files has changed.
            # When the file list changes, clear() is called on the model, and clear()
            # has a side-effect of losing column widths that may have been set
            # interactively by the user.
            for idx, value in enumerate(self._column_widths):
                self.setColumnWidth(idx, value)
            self._column_widths = []
        else:
            # Resize the columns once when cola.resizebrowsercolumns is False.
            # This provides a good initial size since we will not be resizing
            # the columns during expand/collapse.
            self._columns_sized = True
            self.size_columns(force=True)

        self.update_diff()

    def update_actions(self):
        """Enable/disable actions."""
        selection = self.selected_paths()
        selected = bool(selection)
        staged = bool(self.selected_staged_paths(selection=selection))
        modified = bool(self.selected_modified_paths(selection=selection))
        unstaged = bool(self.selected_unstaged_paths(selection=selection))
        tracked = bool(self.selected_tracked_paths(selection=selection))
        revertable = staged or modified

        self.action_editor.setEnabled(selected)
        self.action_history.setEnabled(selected)
        self.action_default_app.setEnabled(selected)
        self.action_parent_dir.setEnabled(selected)

        if self.action_terminal is not None:
            self.action_terminal.setEnabled(selected)

        self.action_stage.setEnabled(staged or unstaged)
        self.action_untrack.setEnabled(tracked)
        self.action_rename.setEnabled(tracked)
        self.action_difftool.setEnabled(staged or modified)
        self.action_difftool_predecessor.setEnabled(tracked)
        self.action_revert_unstaged.setEnabled(revertable)
        self.action_revert_uncommitted.setEnabled(revertable)

    def contextMenuEvent(self, event):
        """Create a context menu."""
        self.update_actions()
        menu = qtutils.create_menu(N_('Actions'), self)
        menu.addAction(self.action_editor)
        menu.addAction(self.action_stage)
        menu.addSeparator()
        menu.addAction(self.action_history)
        menu.addAction(self.action_difftool)
        menu.addAction(self.action_difftool_predecessor)
        menu.addAction(self.action_blame)
        menu.addSeparator()
        menu.addAction(self.action_revert_unstaged)
        menu.addAction(self.action_revert_uncommitted)
        menu.addAction(self.action_untrack)
        menu.addAction(self.action_rename)
        menu.addSeparator()
        menu.addAction(self.action_default_app)
        menu.addAction(self.action_parent_dir)

        if self.action_terminal is not None:
            menu.addAction(self.action_terminal)
        menu.exec_(self.mapToGlobal(event.pos()))

    def mousePressEvent(self, event):
        """Synchronize the selection on mouse-press."""
        result = QtWidgets.QTreeView.mousePressEvent(self, event)
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
        model = self.context.model
        model_staged = utils.add_parents(model.staged)
        model_modified = utils.add_parents(model.modified)
        model_unmerged = utils.add_parents(model.unmerged)
        model_untracked = utils.add_parents(model.untracked)

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
        self.selection.set_selection(state)
        return paths

    def selectionChanged(self, old, new):
        """Override selectionChanged to update available actions."""
        result = QtWidgets.QTreeView.selectionChanged(self, old, new)
        if not self.restoring_selection:
            self.update_actions()
            self.update_diff()
        return result

    def update_diff(self):
        context = self.context
        model = context.model
        paths = self.sync_selection()
        if paths and self.model().path_is_interesting(paths[0]):
            cached = paths[0] in model.staged
            cmds.do(cmds.Diff, context, paths[0], cached)

    def set_model(self, model):
        """Set the concrete QAbstractItemModel instance."""
        self.setModel(model)
        model.restore.connect(self.restore_state, type=Qt.QueuedConnection)

    def name_item_from_index(self, model_index):
        """Return the name item corresponding to the model index."""
        index = model_index.sibling(model_index.row(), 0)
        return self.model().itemFromIndex(index)

    def paths_from_indexes(self, indexes):
        return qtutils.paths_from_indexes(
            self.model(), indexes, item_type=GitRepoNameItem.TYPE
        )

    def selected_paths(self):
        """Return the selected paths."""
        return self.paths_from_indexes(self.selectedIndexes())

    def selected_staged_paths(self, selection=None):
        """Return selected staged paths."""
        if selection is None:
            selection = self.selected_paths()
        model = self.context.model
        staged = utils.add_parents(model.staged)
        return [p for p in selection if p in staged]

    def selected_modified_paths(self, selection=None):
        """Return selected modified paths."""
        if selection is None:
            selection = self.selected_paths()
        model = self.context.model
        modified = utils.add_parents(model.modified)
        return [p for p in selection if p in modified]

    def selected_unstaged_paths(self, selection=None):
        """Return selected unstaged paths."""
        if selection is None:
            selection = self.selected_paths()
        model = self.context.model
        modified = utils.add_parents(model.modified)
        untracked = utils.add_parents(model.untracked)
        unstaged = modified.union(untracked)
        return [p for p in selection if p in unstaged]

    def selected_tracked_paths(self, selection=None):
        """Return selected tracked paths."""
        if selection is None:
            selection = self.selected_paths()
        model = self.context.model
        staged = set(self.selected_staged_paths(selection=selection))
        modified = set(self.selected_modified_paths(selection=selection))
        untracked = utils.add_parents(model.untracked)
        tracked = staged.union(modified)
        return [p for p in selection if p not in untracked or p in tracked]

    def view_history(self):
        """Launch the configured history browser path-limited to entries."""
        paths = self.selected_paths()
        cmds.do(cmds.VisualizePaths, self.context, paths)

    def untrack_selected(self):
        """Untrack selected paths."""
        context = self.context
        cmds.do(cmds.Untrack, context, self.selected_tracked_paths())

    def rename_selected(self):
        """Untrack selected paths."""
        context = self.context
        cmds.do(cmds.Rename, context, self.selected_tracked_paths())

    def diff_predecessor(self):
        """Diff paths against previous versions."""
        context = self.context
        paths = self.selected_tracked_paths()
        args = ['--'] + paths
        revs, summaries = gitcmds.log_helper(context, all=False, extra_args=args)
        commits = select_commits(
            context, N_('Select Previous Version'), revs, summaries, multiselect=False
        )
        if not commits:
            return
        commit = commits[0]
        difftool.difftool_launch(context, left=commit, paths=paths)

    def current_path(self):
        """Return the path for the current item."""
        index = self.currentIndex()
        if not index.isValid():
            return None
        return self.name_item_from_index(index).path


class BrowseModel:
    """Context data used for browsing branches via git-ls-tree"""

    def __init__(self, ref, filename=None):
        self.ref = ref
        self.relpath = filename
        self.filename = filename


class SaveBlob(cmds.ContextCommand):
    def __init__(self, context, model):
        super().__init__(context)
        self.browse_model = model

    def do(self):
        model = self.browse_model
        if model.ref == dag.WORKTREE:
            try:
                shutil.copy2(model.relpath, model.filename)
                err = ''
                status = 0
            except OSError as error:
                err = f'\n{error}'
                status = 1
            out = '# shutil.copy2({}, {}){}'.format(
                shlex.quote(model.relpath),
                shlex.quote(model.filename),
                err,
            )
            Interaction.command(
                N_('Error Saving File'), 'shutil.copy2', status, out, err
            )
        else:
            if model.ref == dag.STAGE:
                model_ref = ':0'
            else:
                model_ref = model.ref
            ref = f'{model_ref}:{model.relpath}'
            with core.xopen(model.filename, 'wb') as fp:
                status, output, err = self.context.git.cat_file('blob', ref, _stdout=fp)

            out = '# git cat-file blob {} >{}\n{}'.format(
                shlex.quote(ref),
                shlex.quote(model.filename),
                output,
            )
            Interaction.command(
                N_('Error Saving File'), 'git cat-file', status, out, err
            )
        if status != 0:
            return

        msg = N_('Saved "%(filename)s" from "%(ref)s" to "%(destination)s"') % {
            'filename': model.relpath,
            'ref': model.ref,
            'destination': model.filename,
        }
        Interaction.log_status(status, msg, '')

        Interaction.information(
            N_('File Saved'), N_('File saved to "%s"') % model.filename
        )


class BrowseBranch(standard.Dialog):
    @classmethod
    def browse(cls, context, ref):
        model = BrowseModel(ref)
        dlg = cls(context, model, parent=qtutils.active_window())
        dlg_model = GitTreeModel(context, ref, dlg)
        dlg.setModel(dlg_model)
        dlg.setWindowTitle(N_('Browsing %s') % model.ref)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return dlg

    def __init__(self, context, model, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        # updated for use by commands
        self.context = context
        self.model = model

        # widgets
        self.tree = GitTreeWidget(parent=self)
        self.close_button = qtutils.close_button()

        text = N_('Save')
        self.save = qtutils.create_button(text=text, enabled=False, default=True)

        # layouts
        self.btnlayt = qtutils.hbox(
            defs.margin, defs.spacing, self.close_button, qtutils.STRETCH, self.save
        )

        self.layt = qtutils.vbox(defs.margin, defs.spacing, self.tree, self.btnlayt)
        self.setLayout(self.layt)

        # connections
        self.tree.path_chosen.connect(self.save_path)

        self.tree.selection_changed.connect(
            self.selection_changed, type=Qt.QueuedConnection
        )

        qtutils.connect_button(self.close_button, self.close)
        qtutils.connect_button(self.save, self.save_blob)
        self.init_size(parent=parent)

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
        if save_path(self.context, path, self.model):
            self.accept()

    def save_blob(self):
        """Save the currently selected file"""
        filenames = self.tree.selected_files()
        if not filenames:
            return
        self.save_path(filenames[0])

    def selection_changed(self):
        """Update actions based on the current selection"""
        filenames = self.tree.selected_files()
        self.save.setEnabled(bool(filenames))


class GitTreeWidget(standard.TreeView):
    selection_changed = Signal()
    path_chosen = Signal(object)

    def __init__(self, parent=None):
        standard.TreeView.__init__(self, parent)
        self.setHeaderHidden(True)
        self.doubleClicked.connect(self.double_clicked)

    def double_clicked(self, index):
        item = self.model().itemFromIndex(index)
        if item is None:
            return
        if item.is_dir:
            return
        self.path_chosen.emit(item.path)

    def selected_files(self):
        items = self.selected_items()
        return [i.path for i in items if not i.is_dir]

    def selectionChanged(self, old_selection, new_selection):
        QtWidgets.QTreeView.selectionChanged(self, old_selection, new_selection)
        self.selection_changed.emit()

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

        row_items = create_row(path, False)
        parent.appendRow(row_items)

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""
        # Create model items
        row_items = create_row(path, True)

        try:
            parent_path = parent.path
        except AttributeError:  # root QStandardItem
            parent_path = ''

        # Insert directories before file paths
        try:
            row = self.dir_rows[parent_path]
        except KeyError:
            row = self.dir_rows[parent_path] = 0

        parent.insertRow(row, row_items)
        self.dir_rows[parent_path] += 1
        self.dir_entries[path] = row_items[0]

        return row_items[0]

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


def create_row(path, is_dir):
    """Return a list of items representing a row."""
    return [GitTreeItem(path, is_dir)]


class GitTreeModel(GitFileTreeModel):
    def __init__(self, context, ref, parent):
        GitFileTreeModel.__init__(self, parent)
        self.context = context
        self.ref = ref
        self._initialize()

    def _initialize(self):
        """Iterate over git-ls-tree and create GitTreeItems."""
        status, out, err = self.context.git.ls_tree(
            '--full-tree', '-r', '-t', '-z', self.ref
        )
        if status != 0:
            Interaction.log_status(status, out, err)
            return

        if not out:
            return

        oid_len = self.context.model.oid_len
        for line in out[:-1].split('\0'):
            # .....6 ...4 ......................................40
            # 040000 tree c127cde9a0c644a3a8fef449a244f47d5272dfa6	relative
            # 100644 blob 139e42bf4acaa4927ec9be1ec55a252b97d3f1e2	relative/path
            objtype = line[7]
            relpath = line[6 + 1 + 4 + 1 + oid_len + 1 :]
            if objtype == 't':
                parent = self.dir_entries[utils.dirname(relpath)]
                self.add_directory(parent, relpath)
            elif objtype == 'b':
                self.add_file(relpath)


class GitTreeItem(QtGui.QStandardItem):
    """
    Represents a cell in a tree view.

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
            icon = icons.directory()
        else:
            icon = icons.file_text()
        self.setIcon(icon)
