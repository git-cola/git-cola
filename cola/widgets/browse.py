from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import cmdfactory
from cola import core
from cola import utils
from cola import qtutils
from cola import signals
from cola.cmds import BaseCommand
from cola.ctrl import Controller
from cola.git import git
from cola.widgets import defs
from cola.widgets import standard


save_blob = 'save_blob'


class BrowseModel(object):
    def __init__(self, ref):
        self.ref = ref
        self.relpath = None
        self.filename = None


class SaveBlob(BaseCommand):
    def __init__(self):
        BaseCommand.__init__(self)
        self.factory = cmdfactory.factory()

    def do(self):
        context = self.context
        ref = core.encode(context.ref)
        relpath = core.encode(context.relpath)

        cmd = ['git', 'show', '%s:%s' % (ref, relpath)]
        fp = open(core.encode(context.filename), 'wb')
        proc = utils.start_command(cmd, stdout=fp)

        out, err = proc.communicate()
        fp.close()

        status = proc.returncode
        msg = ('Saved "%s" from %s to "%s"' %
               (context.relpath, context.ref, context.filename))
        cola.notifier().broadcast(signals.log_cmd, status, msg)

        self.factory.prompt_user(signals.information,
                                 'File Saved',
                                 'File saved to "%s"' % context.filename)


class BrowseDialogController(Controller):
    def __init__(self, model, view):
        Controller.__init__(self, model, view)
        command_directory = {
            save_blob: SaveBlob,
        }
        self.add_commands(command_directory)


class BrowseDialog(QtGui.QDialog):

    @staticmethod
    def browse(ref):
        parent = qtutils.active_window()
        model = BrowseModel(ref)
        dlg = BrowseDialog(model, parent=parent)
        dlg_model = GitTreeModel(ref, dlg)
        dlg.setModel(dlg_model)
        dlg.setWindowTitle('Browsing %s' % model.ref)
        ctrl = BrowseDialogController(model, dlg)
        dlg.resize(parent.width()*3/4, 333)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return ctrl

    @staticmethod
    def select_file(ref):
        parent = qtutils.active_window()
        model = BrowseModel(ref)
        dlg = BrowseDialog(model, select_file=True, parent=parent)
        dlg_model = GitTreeModel(ref, dlg)
        dlg.setModel(dlg_model)
        dlg.setWindowTitle('Select File from %s' % model.ref)
        dlg.resize(parent.width()*3/4, 333)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return model.filename

    @staticmethod
    def select_file_from_list(file_list, title='Select File'):
        parent = qtutils.active_window()
        model = BrowseModel(None)
        dlg = BrowseDialog(model, select_file=True, parent=parent)
        dlg_model = GitFileTreeModel(dlg)
        dlg_model.add_files(file_list)
        dlg.setModel(dlg_model)
        dlg.expandAll()
        dlg.setWindowTitle(title)
        dlg.resize(parent.width()*3/4, 333)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return model.filename

    def __init__(self, model, select_file=False, parent=None):
        super(BrowseDialog, self).__init__(parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowModality(QtCore.Qt.WindowModal)

        # updated for use by commands
        self.model = model

        # widgets
        self.tree = GitTreeWidget(model.ref, parent=self)
        self.close = QtGui.QPushButton('Close')
        self.save = QtGui.QPushButton(select_file and 'Select' or 'Save')
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
        self.connect(self.close, SIGNAL('clicked()'), self.reject)

        self.connect(self.save, SIGNAL('clicked()'), self.save_blob)

        if select_file:
            self.connect(self.tree, SIGNAL('path_chosen'), self.path_chosen)
        else:
            self.connect(self.tree, SIGNAL('path_chosen'), self.save_path)

        self.connect(self.tree, SIGNAL('selectionChanged()'),
                     self.selection_changed)

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
        self.emit(SIGNAL(save_blob))
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
    def __init__(self, ref, parent=None):
        super(GitTreeWidget, self).__init__(parent)
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
        status, output = git.ls_tree('--full-tree', '-r', '-t', '-z', self.ref,
                                     with_status=True, with_stderr=True)
        if status != 0:
            cola.notifier().broadcast(signals.log_cmd, status, output)
            return

        if not output:
            return

        for line in core.decode(output[:-1]).split('\0'):
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
