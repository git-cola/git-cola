from __future__ import division, absolute_import, unicode_literals
import collections
import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import gitcfg
from .. import gitcmds
from .. import core
from .. import icons
from .. import utils
from .. import qtutils
from ..git import STDOUT
from ..i18n import N_
from ..models import main


# Custom event type for GitRepoInfoEvents
INFO_EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())


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
    def text(cls, column):
        try:
            value = cls.TEXT[column]
        except IndexError:
            # Defer translation until runtime
            cls.TEXT.extend([
                N_('Name'),
                N_('Status'),
                N_('Message'),
                N_('Author'),
                N_('Age'),
            ])
            value = cls.TEXT[column]
        return value

    @classmethod
    def attr(cls, column):
        """Return the attribute for the column"""
        return cls.ATTRS[column]


class GitRepoEntryStore(object):

    entries = {}
    default_author = ''

    @classmethod
    def entry(cls, path, parent, runtask, turbo):
        """Return the shared GitRepoEntry for a path."""
        default_author = cls.default_author
        if not default_author:
            author = N_('Author')
            default_author = gitcfg.current().get('user.name', author)
            cls.default_author = default_author
        try:
            e = cls.entries[path]
        except KeyError:
            e = cls.entries[path] = GitRepoEntry(path, parent, runtask,
                                                 turbo, default_author)
        return e

    @classmethod
    def remove(cls, path):
        try:
            del cls.entries[path]
        except KeyError:
            pass


class GitRepoModel(QtGui.QStandardItemModel):
    """Provides an interface into a git repository for browsing purposes."""

    updated = Signal()
    restore = Signal()

    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)

        self.entries = {}
        self.turbo = gitcfg.current().get('cola.turbo', False)
        self._runtask = qtutils.RunTask(parent=parent)
        self._parent = parent
        self._interesting_paths = set()
        self._interesting_files = set()
        self._known_paths = set()
        self._dir_entries = {}

        self.updated.connect(self.refresh, type=Qt.QueuedConnection)

        model = main.model()
        model.add_observer(model.message_updated, self._model_updated)

        self.file_icon = icons.file_text()
        self.dir_icon = icons.directory()

    def mimeData(self, indexes):
        paths = qtutils.paths_from_indexes(self, indexes,
                                           item_type=GitRepoNameItem.TYPE)
        return qtutils.mimedata_from_paths(paths)

    def mimeTypes(self):
        return qtutils.path_mimetypes()

    def clear(self):
        super(GitRepoModel, self).clear()
        self.entries.clear()

    def columnCount(self, index):
        return len(Columns.ALL)

    def hasChildren(self, index):
        if index.isValid():
            item = self.itemFromIndex(index)
            return item.hasChildren()
        return True

    def canFetchMore(self, index):
        item = self.itemFromIndex(index)
        if item and item.is_dir:
            return True
        return False

    def rowCount(self, index):
        if not index.isValid():
            return self.invisibleRootItem().rowCount()

        item = self.itemFromIndex(index)
        return item.rowCount()

    def row(self, path, create=True, is_dir=False):
        try:
            row = self.entries[path]
        except KeyError:
            if create:
                column = self.create_column
                row = self.entries[path] = [
                        column(c, path, is_dir) for c in Columns.ALL]
            else:
                row = None
        return row

    def create_column(self, col, path, is_dir):
        """Creates a StandardItem for use in a treeview cell."""
        # GitRepoNameItem is the only one that returns a custom type()
        # and is used to infer selections.
        if col == Columns.NAME:
            item = GitRepoNameItem(path, self._parent, is_dir,
                                   self._runtask, self.turbo)
        else:
            item = GitRepoItem(col, path, self._parent,
                               self._runtask, self.turbo)
        return item

    def populate(self, item):
        self.populate_dir(item, item.path + '/')

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""

        # Create model items
        row_items = self.row(path, is_dir=True)

        # Use a standard directory icon
        name_item = row_items[0]
        name_item.setIcon(self.dir_icon)
        parent.appendRow(row_items)

        # Update the 'name' column for this entry
        self.entry(path).update_name()
        self._known_paths.add(path)

        return name_item

    def path_is_interesting(self, path):
        """Return True if path has a status."""
        return path in self._interesting_paths

    def get_paths(self, files=None):
        """Return paths of interest; e.g. paths with a status."""
        if files is None:
            files = self.get_files()
        return utils.add_parents(files)

    def get_files(self):
        model = main.model()
        return set(model.staged + model.unstaged)

    def _model_updated(self):
        """Observes model changes and updates paths accordingly."""
        self.updated.emit()

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
            self.entry(path).update()

        self._interesting_files = new_files
        self._interesting_paths = new_paths

    def _initialize(self):

        self.setColumnCount(len(Columns.ALL))
        for idx, header in enumerate(Columns.ALL):
            text = Columns.text(header)
            self.setHeaderData(idx, Qt.Horizontal, text)

        root = self.invisibleRootItem()
        self._dir_entries = {'': root}
        self._entries = {}
        self._known_paths = set()
        self._interesting_files = files = self.get_files()
        self._interesting_paths = self.get_paths(files=files)

        self.populate_dir(root, './')

    def add_file(self, parent, path):
        """Add a file entry to the model."""

        self._known_paths.add(path)

        # Create model items
        row_items = self.row(path)

        # Use a standard file icon for the name field
        row_items[0].setIcon(self.file_icon)

        # Add file paths at the end of the list
        parent.appendRow(row_items)
        self.entry(path).update_name()

    def _get_dir_entry(self, dirname, entries):
        """
        Create a directory entry for the model.

        This ensures that directories are always listed before files.

        """
        try:
            entry = entries[dirname]
        except KeyError:
            try:
                parent = entries[utils.dirname(dirname)]
            except KeyError:
                parent = self._get_dir_entry(utils.dirname(dirname), entries)

            entry = self.add_directory(parent, dirname)
            entries[dirname] = entry

        return entry

    def populate_dir(self, parent, path):
        """Populate a subtree"""
        dirs, paths = gitcmds.listdir(path)

        # Insert directories before file paths
        for dirname in dirs:
            self.add_directory(parent, dirname)

        for filename in paths:
            self.add_file(parent, filename)

    def entry(self, path):
        """Return the GitRepoEntry for a path."""
        return GitRepoEntryStore.entry(path, self._parent,
                                       self._runtask, self.turbo)


class GitRepoEntry(QtCore.QObject):
    """
    Provides asynchronous lookup of repository data for a path.

    Emits signal names matching those defined in Columns.

    """
    name = Signal(object)
    status = Signal(object)
    author = Signal(object)
    message = Signal(object)
    age = Signal(object)

    def __init__(self, path, parent, runtask, turbo, default_author):
        QtCore.QObject.__init__(self, parent)
        self.path = path
        self.runtask = runtask
        self.turbo = turbo
        self.default_author = default_author

    def update_name(self):
        """Emits a signal corresponding to the entry's name."""
        # 'name' is cheap to calculate so simply emit a signal
        self.name.emit(utils.basename(self.path))
        if '/' not in self.path:
            self.update()

    def update(self):
        """Starts a GitRepoInfoTask to calculate info for entries."""
        # GitRepoInfoTask handles expensive lookups
        if self.turbo:
            # Turbo mode does not run background tasks
            return
        task = GitRepoInfoTask(self.path, self, self.runtask,
                               self.turbo, self.default_author)
        self.runtask.start(task)

    def event(self, e):
        """Receive GitRepoInfoEvents and emit corresponding Qt signals."""
        if e.type() == INFO_EVENT_TYPE:
            e.accept()
            attrs = (Columns.STATUS, Columns.MESSAGE,
                     Columns.AUTHOR, Columns.AGE)
            for (attr, value) in zip(attrs, e.data):
                signal = getattr(self, Columns.attr(attr))
                signal.emit(value)
            return True
        return QtCore.QObject.event(self, e)


class GitRepoInfoTask(qtutils.Task):
    """Handles expensive git lookups for a path."""

    def __init__(self, path, parent, runtask, turbo, default_author):
        qtutils.Task.__init__(self, parent)
        self.path = path
        self._parent = parent
        self._runtask = runtask
        self._turbo = turbo
        self._default_author = default_author
        self._data = {}

    def data(self, key):
        """Return git data for a path

        Supported keys are 'date', 'message', and 'author'

        """
        if self._turbo:
            # Turbo mode skips the expensive git-log lookup
            return ''

        elif not self._data:
            log_line = main.model().git.log('-1', '--', self.path,
                                            no_color=True,
                                            pretty=r'format:%ar%x01%s%x01%an',
                                            _readonly=True
                                            )[STDOUT]
            if log_line:
                log_line = log_line
                date, message, author = log_line.split(chr(0x01), 2)
                self._data['date'] = date
                self._data['message'] = message
                self._data['author'] = author
            else:
                self._data['date'] = self.date()
                self._data['message'] = '-'
                self._data['author'] = self._default_author

        return self._data[key]

    def name(self):
        """Calculate the name for an entry."""
        return utils.basename(self.path)

    def date(self):
        """Returns a relative date for a file path

        This is typically used for new entries that do not have
        'git log' information.

        """
        try:
            st = core.stat(self.path)
        except:
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

        model = main.model()
        unmerged = utils.add_parents(model.unmerged)
        modified = utils.add_parents(model.modified)
        staged = utils.add_parents(model.staged)
        untracked = utils.add_parents(model.untracked)
        upstream_changed = utils.add_parents(model.upstream_changed)

        if self.path in unmerged:
            status = (icons.modified_name(), N_('Unmerged'))
        elif self.path in modified and self.path in staged:
            status = (icons.partial_name(), N_('Partially Staged'))
        elif self.path in modified:
            status = (icons.modified_name(), N_('Modified'))
        elif self.path in staged:
            status = (icons.staged_name(), N_('Staged'))
        elif self.path in upstream_changed:
            status = (icons.upstream_name(), N_('Changed Upstream'))
        elif self.path in untracked:
            status = (None, '?')
        else:
            status = (None, '')
        return status

    def task(self):
        """Perform expensive lookups and post corresponding events."""
        app = QtWidgets.QApplication.instance()
        entry = GitRepoEntryStore.entry(self.path, self._parent,
                                        self._runtask, self._turbo)
        data = (
            self.status(),
            self.data('message'),
            self.data('author'),
            self.data('date'),
        )
        app.postEvent(entry, GitRepoInfoEvent(data))


class GitRepoInfoEvent(QtCore.QEvent):
    """Transport mechanism for communicating from a GitRepoInfoTask."""

    def __init__(self, data):
        QtCore.QEvent.__init__(self, INFO_EVENT_TYPE)
        self.data = data

    def type(self):
        return INFO_EVENT_TYPE


class GitRepoItem(QtGui.QStandardItem):
    """
    Represents a cell in a treeview.

    Many GitRepoItems map to a single repository path.
    Each GitRepoItem manages a different cell in the tree view.
    One is created for each column -- Name, Status, Age, etc.

    """
    def __init__(self, column, path, parent, runtask, turbo):
        QtGui.QStandardItem.__init__(self)
        self.path = path
        self.runtask = runtask
        self.cached = False
        self.setDragEnabled(False)
        self.setEditable(False)
        entry = GitRepoEntryStore.entry(path, parent, runtask, turbo)
        if column == Columns.STATUS:
            qtutils.disconnect(entry.status)
            entry.status.connect(self.set_status, type=Qt.QueuedConnection)
        else:
            signal = getattr(entry, Columns.attr(column))
            qtutils.disconnect(signal)
            signal.connect(self.setText, type=Qt.QueuedConnection)

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

    def __init__(self, path, parent, is_dir, runtask, turbo):
        GitRepoItem.__init__(self, Columns.NAME, path, parent, runtask, turbo)
        self.is_dir = is_dir
        self.setDragEnabled(True)

    def type(self):
        """
        Indicate that this item is of a special user-defined type.

        'name' is the only column that registers a user-defined type.
        This is done to allow filtering out other columns when determining
        which paths are selected.

        """
        return GitRepoNameItem.TYPE

    def hasChildren(self):
        return self.is_dir
