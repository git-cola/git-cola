from __future__ import division, absolute_import, unicode_literals

import collections
import time

from cola import sipcompat
sipcompat.initialize()

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import gitcfg
from cola import gitcmds
from cola import core
from cola import icons
from cola import utils
from cola import qtutils
from cola.git import STDOUT
from cola.i18n import N_
from cola.models import main


# Custom event type for GitRepoInfoEvents
INFO_EVENT_TYPE = QtCore.QEvent.User + 42


class Columns(object):
    """Defines columns in the worktree browser"""

    NAME = 'Name'
    STATUS = 'Status'
    AGE = 'Age'
    MESSAGE = 'Message'
    AUTHOR = 'Author'
    ALL = (NAME, STATUS, MESSAGE, AUTHOR, AGE)

    @classmethod
    def text(cls, column):
        if column == cls.NAME:
            return N_('Name')
        elif column == cls.STATUS:
            return N_('Status')
        elif column == cls.MESSAGE:
            return N_('Message')
        elif column == cls.AUTHOR:
            return N_('Author')
        elif column == cls.AGE:
            return N_('Age')
        else:
            raise NotImplementedError('Mapping required for "%s"' % column)


class GitRepoEntryStore(object):

    entries = {}

    @classmethod
    def entry(cls, path, parent, runtask):
        """Return the shared GitRepoEntry for a path."""
        try:
            e = cls.entries[path]
        except KeyError:
            e = cls.entries[path] = GitRepoEntry(path, parent, runtask)
        return e

    @classmethod
    def remove(cls, path):
        try:
            del cls.entries[path]
        except KeyError:
            pass


def _item_path(item):
    """Return the item's path"""
    try:
        path = item.path
    except AttributeError:
        # the root QStandardItem does not have a 'path' attribute
        path = ''
    return path


class GitRepoModel(QtGui.QStandardItemModel):
    """Provides an interface into a git repository for browsing purposes."""

    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)

        self.entries = {}
        self._runtask = qtutils.RunTask(parent=parent)
        self._parent = parent
        self._interesting_paths = set()
        self._interesting_files = set()
        self._known_paths = set()
        self._dir_entries= {}
        self._dir_rows = collections.defaultdict(int)

        self.connect(self, SIGNAL('updated()'),
                     self.refresh, Qt.QueuedConnection)

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

    def row(self, path, create=True):
        try:
            row = self.entries[path]
        except KeyError:
            if create:
                row = self.entries[path] = [self.create_column(c, path)
                                                for c in Columns.ALL]
            else:
                row = None
        return row

    def create_column(self, col, path):
        """Creates a StandardItem for use in a treeview cell."""
        # GitRepoNameItem is the only one that returns a custom type(),
        # so we use to infer selections.
        if col == Columns.NAME:
            item = GitRepoNameItem(path, self._parent, self._runtask)
        else:
            item = GitRepoItem(col, path, self._parent, self._runtask)
        return item

    def _add_file(self, parent, path, insert=False):
        """Add a file entry to the model."""

        self._known_paths.add(path)

        # Create model items
        row_items = self.row(path)

        # Use a standard file icon for the name field
        row_items[0].setIcon(self.file_icon)

        if not insert:
            # Add file paths at the end of the list
            parent.appendRow(row_items)
            self.entry(path).update_name()
            return
        # Entries exist so try to find an a good insertion point
        done = False
        for idx in range(parent.rowCount()):
            child = parent.child(idx, 0)
            if child.rowCount() > 0:
                continue
            if path < child.path:
                parent.insertRow(idx, row_items)
                done = True
                break

        # No adequate place found so simply append
        if not done:
            parent.appendRow(row_items)
        self.entry(path).update_name()

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""

        # Create model items
        row_items = self.row(path)

        # Use a standard directory icon
        row_items[0].setIcon(self.dir_icon)

        # Insert directories before file paths
        # TODO: have self._dir_rows's keys based on something less flaky than
        # QStandardItem instances.
        parent_path = _item_path(parent)
        row = self._dir_rows[parent_path]
        parent.insertRow(row, row_items)
        self._dir_rows[parent_path] += 1

        # Update the 'name' column for this entry
        self.entry(path).update_name()
        self._known_paths.add(path)

        return row_items[0]

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
        self.emit(SIGNAL('updated()'))

    def refresh(self):
        old_files = self._interesting_files
        old_paths = self._interesting_paths
        new_files = self.get_files()
        new_paths = self.get_paths(files=new_files)

        if new_files != old_files or not old_paths:
            self.clear()
            self._initialize()
            self.emit(SIGNAL('restore()'))

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

        self._entries = {}
        self._dir_rows = collections.defaultdict(int)
        self._known_paths = set()
        self._dir_entries = {'': self.invisibleRootItem()}
        self._interesting_files = files = self.get_files()
        self._interesting_paths = self.get_paths(files=files)
        for path in gitcmds.all_files():
            self.add_file(path)

    def add_file(self, path, insert=False):
        """Add a file to the model."""
        dirname = utils.dirname(path)
        if dirname in self._dir_entries:
            parent = self._dir_entries[dirname]
        else:
            parent = self._create_dir_entry(dirname, self._dir_entries)
            self._dir_entries[dirname] = parent
        self._add_file(parent, path, insert=insert)

    def _create_dir_entry(self, dirname, direntries):
        """
        Create a directory entry for the model.

        This ensures that directories are always listed before files.

        """
        entries = dirname.split('/')
        curdir = []
        parent = self.invisibleRootItem()
        curdir_append = curdir.append
        self_add_directory = self.add_directory
        for entry in entries:
            curdir_append(entry)
            path = '/'.join(curdir)
            try:
                parent = direntries[path]
            except KeyError:
                grandparent = parent
                parent = self_add_directory(grandparent, path)
                direntries[path] = parent
        return parent

    def entry(self, path):
        """Return the GitRepoEntry for a path."""
        return GitRepoEntryStore.entry(path, self._parent, self._runtask)


class GitRepoEntry(QtCore.QObject):
    """
    Provides asynchronous lookup of repository data for a path.

    Emits signal names matching those defined in Columns.

    """
    def __init__(self, path, parent, runtask):
        QtCore.QObject.__init__(self, parent)
        self.path = path
        self.runtask = runtask

    def update_name(self):
        """Emits a signal corresponding to the entry's name."""
        # 'name' is cheap to calculate so simply emit a signal
        self.emit(SIGNAL(Columns.NAME), utils.basename(self.path))
        if '/' not in self.path:
            self.update()

    def update(self):
        """Starts a GitRepoInfoTask to calculate info for entries."""
        # GitRepoInfoTask handles expensive lookups
        task = GitRepoInfoTask(self.path, self, self.runtask)
        self.runtask.start(task)

    def event(self, e):
        """Receive GitRepoInfoEvents and emit corresponding Qt signals."""
        if e.type() == INFO_EVENT_TYPE:
            e.accept()
            self.emit(SIGNAL(e.signal), *e.data)
            return True
        return QtCore.QObject.event(self, e)


class GitRepoInfoTask(qtutils.Task):
    """Handles expensive git lookups for a path."""

    def __init__(self, path, parent, runtask):
        qtutils.Task.__init__(self, parent)
        self.path = path
        self._parent = parent
        self._runtask = runtask
        self._cfg = gitcfg.current()
        self._data = {}

    def data(self, key):
        """
        Return git data for a path.

        Supported keys are 'date', 'message', and 'author'

        """
        if not self._data:
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
                self._data['author'] = self._cfg.get('user.name', 'unknown')
        return self._data[key]

    def name(self):
        """Calculate the name for an entry."""
        return utils.basename(self.path)

    def date(self):
        """
        Returns a relative date for a file path.

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
        app = QtGui.QApplication.instance()
        entry = GitRepoEntryStore.entry(self.path, self._parent, self._runtask)
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.MESSAGE, self.data('message')))
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.AGE, self.data('date')))
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.AUTHOR, self.data('author')))
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.STATUS, self.status()))


class GitRepoInfoEvent(QtCore.QEvent):
    """Transport mechanism for communicating from a GitRepoInfoTask."""
    def __init__(self, signal, *data):
        QtCore.QEvent.__init__(self, QtCore.QEvent.User + 1)
        self.signal = signal
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
    def __init__(self, column, path, parent, runtask):
        QtGui.QStandardItem.__init__(self)
        self.path = path
        self.runtask = runtask
        self.cached = False
        self.setDragEnabled(False)
        self.setEditable(False)
        entry = GitRepoEntryStore.entry(path, parent, runtask)
        if column == Columns.STATUS:
            QtCore.QObject.connect(entry, SIGNAL(column), self.set_status,
                                   Qt.QueuedConnection)
        else:
            QtCore.QObject.connect(entry, SIGNAL(column), self.setText,
                                   Qt.QueuedConnection)

    def set_status(self, data):
        icon, txt = data
        if icon:
            self.setIcon(QtGui.QIcon(icon))
        else:
            self.setIcon(QtGui.QIcon())
        self.setText(txt)


class GitRepoNameItem(GitRepoItem):
    """Subclass GitRepoItem to provide a custom type()."""
    TYPE = QtGui.QStandardItem.UserType + 1

    def __init__(self, path, parent, runtask):
        GitRepoItem.__init__(self, Columns.NAME, path, parent, runtask)
        self.setDragEnabled(True)

    def type(self):
        """
        Indicate that this item is of a special user-defined type.

        'name' is the only column that registers a user-defined type.
        This is done to allow filtering out other columns when determining
        which paths are selected.

        """
        return GitRepoNameItem.TYPE
