from __future__ import absolute_import, division, print_function, unicode_literals
import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import gitcmds
from .. import core
from .. import icons
from .. import utils
from .. import qtutils
from ..git import STDOUT
from ..i18n import N_


class Columns(object):
    """Defines columns in the worktree browser"""

    NAME = 0
    STATUS = 1
    MESSAGE = 2
    AUTHOR = 3
    AGE = 4

    ALL = (NAME, STATUS, MESSAGE, AUTHOR, AGE)
    ATTRS = ('name', 'status', 'message', 'author', 'age')
    TEXT = []

    @classmethod
    def init(cls):
        cls.TEXT.extend(
            [N_('Name'), N_('Status'), N_('Message'), N_('Author'), N_('Age')]
        )

    @classmethod
    def text_values(cls):
        if not cls.TEXT:
            cls.init()
        return cls.TEXT

    @classmethod
    def text(cls, column):
        try:
            value = cls.TEXT[column]
        except IndexError:
            # Defer translation until runtime
            cls.init()
            value = cls.TEXT[column]
        return value

    @classmethod
    def attr(cls, column):
        """Return the attribute for the column"""
        return cls.ATTRS[column]


class GitRepoModel(QtGui.QStandardItemModel):
    """Provides an interface into a git repository for browsing purposes."""

    model_updated = Signal()
    restore = Signal()

    def __init__(self, context, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.setColumnCount(len(Columns.ALL))

        self.context = context
        self.model = model = context.model
        self.entries = {}
        cfg = context.cfg
        self.turbo = cfg.get('cola.turbo', False)
        self.default_author = cfg.get('user.name', N_('Author'))
        self._parent = parent
        self._interesting_paths = set()
        self._interesting_files = set()
        self._runtask = qtutils.RunTask(parent=parent)

        self.model_updated.connect(self.refresh, type=Qt.QueuedConnection)

        model = context.model
        model.add_observer(model.message_updated, self._model_updated)

        self.file_icon = icons.file_text()
        self.dir_icon = icons.directory()

    def mimeData(self, indexes):
        context = self.context
        paths = qtutils.paths_from_indexes(
            self, indexes, item_type=GitRepoNameItem.TYPE
        )
        return qtutils.mimedata_from_paths(context, paths)

    # pylint: disable=no-self-use
    def mimeTypes(self):
        return qtutils.path_mimetypes()

    def clear(self):
        self.entries.clear()
        super(GitRepoModel, self).clear()

    def hasChildren(self, index):
        if index.isValid():
            item = self.itemFromIndex(index)
            result = item.hasChildren()
        else:
            result = True
        return result

    def get(self, path, default=None):
        if not path:
            item = self.invisibleRootItem()
        else:
            item = self.entries.get(path, default)
        return item

    def create_row(self, path, create=True, is_dir=False):
        try:
            row = self.entries[path]
        except KeyError:
            if create:
                column = create_column
                row = self.entries[path] = [
                    column(c, path, is_dir) for c in Columns.ALL
                ]
            else:
                row = None
        return row

    def populate(self, item):
        self.populate_dir(item, item.path + '/')

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""
        # First, try returning an existing item
        current_item = self.get(path)
        if current_item is not None:
            return current_item[0]

        # Create model items
        row_items = self.create_row(path, is_dir=True)

        # Use a standard directory icon
        name_item = row_items[0]
        name_item.setIcon(self.dir_icon)
        parent.appendRow(row_items)

        return name_item

    def add_file(self, parent, path):
        """Add a file entry to the model."""

        file_entry = self.get(path)
        if file_entry is not None:
            return file_entry

        # Create model items
        row_items = self.create_row(path)
        name_item = row_items[0]

        # Use a standard file icon for the name field
        name_item.setIcon(self.file_icon)

        # Add file paths at the end of the list
        parent.appendRow(row_items)

        return name_item

    def populate_dir(self, parent, path):
        """Populate a subtree"""
        context = self.context
        dirs, paths = gitcmds.listdir(context, path)

        # Insert directories before file paths
        for dirname in dirs:
            dir_parent = parent
            if '/' in dirname:
                dir_parent = self.add_parent_directories(parent, dirname)
            self.add_directory(dir_parent, dirname)
            self.update_entry(dirname)

        for filename in paths:
            file_parent = parent
            if '/' in filename:
                file_parent = self.add_parent_directories(parent, filename)
            self.add_file(file_parent, filename)
            self.update_entry(filename)

    def add_parent_directories(self, parent, dirname):
        """Ensure that all parent directory entries exist"""
        sub_parent = parent
        parent_dir = utils.dirname(dirname)
        for path in utils.pathset(parent_dir):
            sub_parent = self.add_directory(sub_parent, path)
        return sub_parent

    def path_is_interesting(self, path):
        """Return True if path has a status."""
        return path in self._interesting_paths

    def get_paths(self, files=None):
        """Return paths of interest; e.g. paths with a status."""
        if files is None:
            files = self.get_files()
        return utils.add_parents(files)

    def get_files(self):
        model = self.model
        return set(model.staged + model.unstaged)

    def _model_updated(self):
        """Observes model changes and updates paths accordingly."""
        self.model_updated.emit()

    def refresh(self):
        old_files = self._interesting_files
        old_paths = self._interesting_paths
        new_files = self.get_files()
        new_paths = self.get_paths(files=new_files)

        if new_files != old_files or not old_paths:
            self.clear()
            self._initialize()
            self.restore.emit()

        # Existing items
        for path in sorted(new_paths.union(old_paths)):
            self.update_entry(path)

        self._interesting_files = new_files
        self._interesting_paths = new_paths

    def _initialize(self):
        self.setHorizontalHeaderLabels(Columns.text_values())
        self.entries = {}
        self._interesting_files = files = self.get_files()
        self._interesting_paths = self.get_paths(files=files)

        root = self.invisibleRootItem()
        self.populate_dir(root, './')

    def update_entry(self, path):
        if self.turbo or path not in self.entries:
            return  # entry doesn't currently exist
        context = self.context
        task = GitRepoInfoTask(context, self._parent, path, self.default_author)
        self._runtask.start(task)


def create_column(col, path, is_dir):
    """Creates a StandardItem for use in a treeview cell."""
    # GitRepoNameItem is the only one that returns a custom type()
    # and is used to infer selections.
    if col == Columns.NAME:
        item = GitRepoNameItem(path, is_dir)
    else:
        item = GitRepoItem(path)
    return item


class GitRepoInfoTask(qtutils.Task):
    """Handles expensive git lookups for a path."""

    def __init__(self, context, parent, path, default_author):
        qtutils.Task.__init__(self, parent)
        self.context = context
        self.path = path
        self._parent = parent
        self._default_author = default_author
        self._data = {}

    def data(self, key):
        """Return git data for a path

        Supported keys are 'date', 'message', and 'author'

        """
        git = self.context.git
        if not self._data:
            log_line = git.log(
                '-1',
                '--',
                self.path,
                no_color=True,
                pretty=r'format:%ar%x01%s%x01%an',
                _readonly=True,
            )[STDOUT]
            if log_line:
                date, message, author = log_line.split(chr(0x01), 2)
                self._data['date'] = date
                self._data['message'] = message
                self._data['author'] = author
            else:
                self._data['date'] = self.date()
                self._data['message'] = '-'
                self._data['author'] = self._default_author

        return self._data[key]

    def date(self):
        """Returns a relative date for a file path

        This is typically used for new entries that do not have
        'git log' information.

        """
        try:
            st = core.stat(self.path)
        except OSError:
            return N_('%d minutes ago') % 0
        elapsed = time.time() - st.st_mtime
        minutes = int(elapsed / 60)
        if minutes < 60:
            return N_('%d minutes ago') % minutes
        hours = int(elapsed / 60 / 60)
        if hours < 24:
            return N_('%d hours ago') % hours
        return N_('%d days ago') % int(elapsed / 60 / 60 / 24)

    def status(self):
        """Return the status for the entry's path."""
        model = self.context.model
        unmerged = utils.add_parents(model.unmerged)
        modified = utils.add_parents(model.modified)
        staged = utils.add_parents(model.staged)
        untracked = utils.add_parents(model.untracked)
        upstream_changed = utils.add_parents(model.upstream_changed)

        path = self.path
        if path in unmerged:
            status = (icons.modified_name(), N_('Unmerged'))
        elif path in modified and self.path in staged:
            status = (icons.partial_name(), N_('Partially Staged'))
        elif path in modified:
            status = (icons.modified_name(), N_('Modified'))
        elif path in staged:
            status = (icons.staged_name(), N_('Staged'))
        elif path in upstream_changed:
            status = (icons.upstream_name(), N_('Changed Upstream'))
        elif path in untracked:
            status = (None, '?')
        else:
            status = (None, '')
        return status

    def task(self):
        """Perform expensive lookups and post corresponding events."""
        data = (
            self.path,
            self.status(),
            self.data('message'),
            self.data('author'),
            self.data('date'),
        )
        app = QtWidgets.QApplication.instance()
        try:
            app.postEvent(self._parent, GitRepoInfoEvent(data))
        except RuntimeError:
            pass  # The app exited before this task finished


class GitRepoInfoEvent(QtCore.QEvent):
    """Transport mechanism for communicating from a GitRepoInfoTask."""

    # Custom event type
    TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, data):
        QtCore.QEvent.__init__(self, self.TYPE)
        self.data = data

    def type(self):
        return self.TYPE


class GitRepoItem(QtGui.QStandardItem):
    """Represents a cell in a treeview.

    Many GitRepoItems map to a single repository path.
    Each GitRepoItem manages a different cell in the tree view.
    One is created for each column -- Name, Status, Age, etc.

    """

    def __init__(self, path):
        QtGui.QStandardItem.__init__(self)
        self.path = path
        self.cached = False
        self.setDragEnabled(False)
        self.setEditable(False)

    def set_status(self, data):
        icon, txt = data
        if icon:
            self.setIcon(QtGui.QIcon(icon))
        else:
            self.setIcon(QtGui.QIcon())
        self.setText(txt)


class GitRepoNameItem(GitRepoItem):
    """Subclass GitRepoItem to provide a custom type()."""

    TYPE = QtGui.QStandardItem.ItemType(QtGui.QStandardItem.UserType + 1)

    def __init__(self, path, is_dir):
        GitRepoItem.__init__(self, path)
        self.is_dir = is_dir
        self.setDragEnabled(True)
        self.setText(utils.basename(path))

    def type(self):
        """
        Indicate that this item is of a special user-defined type.

        'name' is the only column that registers a user-defined type.
        This is done to allow filtering out other columns when determining
        which paths are selected.

        """
        return self.TYPE

    def hasChildren(self):
        return self.is_dir
