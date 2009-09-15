import os
import sys
import time

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt

import cola

from cola import core
from cola import utils
from cola import qtutils


class GitRepoSignals:
    """
    Defines signal names used in thread communication.

    A nice trick we use here is using the columns header as the
    value for the class-variable constant.

    """
    Name = 'Name'
    Status = 'Status'
    Age = 'Age'
    Message = 'Message'
    Who = 'Who'


class GitRepoModel(QtGui.QStandardItemModel):
    """Provides an interface into a git repository for browsing purposes."""
    def __init__(self, parent):
        QtGui.QStandardItem.__init__(self, parent)
        self._dir_rows = {}
        self._headers = (GitRepoSignals.Name,
                         GitRepoSignals.Status,
                         GitRepoSignals.Age,
                         GitRepoSignals.Message,
                         GitRepoSignals.Who)
        self.setColumnCount(len(self._headers))
        for idx, header in enumerate(self._headers):
            self.setHeaderData(idx, Qt.Horizontal,
                               QtCore.QVariant(self.tr(header)))
        self._initialize()

    def _create_row(self, path):
        """Return a list of items representing a row."""
        return [GitRepoItem(path, i) for i in self._headers]

    def add_file(self, parent, path):
        """Add a file entry to the model."""

        # Create model items
        row_items = self._create_row(path)

        # Use a standard file icon for the name field
        row_items[0].setIcon(qtutils.file_icon())

        # Add file paths at the end of the list
        parent.appendRow(row_items)

        # Update the name column
        entry = self.entry(path)
        entry.update_name()

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""

        # Create model items
        row_items = self._create_row(path)

        # Use a standard directory icon
        row_items[0].setIcon(qtutils.dir_icon())

        # Insert directories before file paths
        row = self._dir_rows.setdefault(parent, 0)
        parent.insertRow(row, row_items)
        self._dir_rows[parent] += 1

        # Update the 'name' column for this entry
        entry = self.entry(path)
        entry.update_name()

        return row_items[0]

    def _initialize(self):
        """Iterate over the cola model and create GitRepoItems."""
        direntries = {'': self.invisibleRootItem()}
        for path in cola.model().everything():
            dirname = utils.dirname(path)
            if dirname in direntries:
                parent = direntries[dirname]
            else:
                parent = self._create_dir_entry(dirname, direntries)
                direntries[dirname] = parent
            self.add_file(parent, path)

    def _create_dir_entry(self, dirname, direntries):
        """
        Create a directory entry for the model.

        This ensures that directories are always listed before files.

        """
        entries = dirname.split('/')
        curdir = []
        parent = self.invisibleRootItem()
        for entry in entries:
            curdir.append(entry)
            path = '/'.join(curdir)
            if path in direntries:
                parent = direntries[path]
            else:
                grandparent = parent
                parent_path = '/'.join(curdir[:-1])
                parent = self.add_directory(grandparent, path)
                direntries[path] = parent
        return parent

    def entry(self, path):
        """Return the GitRepoEntry for a path."""
        return GitRepoEntryManager.entry(path)


class GitRepoEntryManager(object):
    """
    Provides access to static instances of GitRepoEntry and model data.
    """
    static_entries = {}

    @classmethod
    def entry(cls, path):
        """Return a static instance of a GitRepoEntry."""
        if path not in cls.static_entries:
            cls.static_entries[path] = GitRepoEntry(path)
        return cls.static_entries[path]


class GitRepoEntry(QtCore.QObject):
    """
    Provides asynchronous lookup of repository data for a path.

    Emits the following Qt Signals:
        name(QString)
        status(QString)
        age(QString)
        message(QString)
        who(QString)

    """
    def __init__(self, path):
        QtCore.QObject.__init__(self)
        self.path = path
        self.task = None

    def update_name(self):
        """Emits a signal corresponding to the entry's name."""
        # 'name' is cheap to calculate so simply emit a signal
        self.emit(QtCore.SIGNAL('name(QString)'), utils.basename(self.path))
        if '/' not in self.path:
            self.update()

    def update(self):
        """Starts a GitRepoInfoTask to calculate info for entries."""
        # GitRepoInfoTask handles expensive lookups
        threadpool = QtCore.QThreadPool.globalInstance()
        self.task = GitRepoInfoTask(self, self.path)
        threadpool.start(self.task)

    def event(self, e):
        """Receive GitRepoInfoEvents and emit corresponding Qt signals."""
        e.accept()
        self.emit(QtCore.SIGNAL(e.signal), *e.data)
        return True


class GitRepoInfoTask(QtCore.QRunnable):
    """Handles expensive git lookups for a path."""
    def __init__(self, entry, path):
        QtCore.QRunnable.__init__(self)
        self.entry = entry
        self.path = path
        self._data = {}

    def data(self, key):
        """
        Return git data for a path.

        Supported keys are 'date', 'message', and 'author'

        """
        if not self._data:
            log_line = cola.model().git.log('-1', '--', self.path,
                                            M=True,
                                            all=True,
                                            pretty='format:%ar/%s/%an')
            if log_line:
                log_line = core.decode(log_line)
                date, rest = log_line.split('/', 1)
                message, author = rest.rsplit('/', 1)
                self._data['date'] = date
                self._data['message'] = message
                self._data['author'] = author
            else:
                self._data['date'] = self.date()
                self._data['message'] = '-'
                self._data['author'] = cola.model().local_user_name
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
        encpath = core.encode(self.path)
        st = os.stat(encpath)
        elapsed = time.time() - st.st_mtime
        minutes = int(elapsed / 60.)
        if minutes < 60:
            return '%d minutes ago' % minutes
        hours = int(elapsed / 60. / 60.)
        if hours < 24:
            return '%d hours ago' % hours
        return '%d days ago' % int(elapsed / 60. / 60. / 24.)

    def status(self):
        """Return the status for the entry's path."""

        model = cola.model()
        unmerged = utils.add_parents(set(model.unmerged))
        modified = utils.add_parents(set(model.modified))
        staged = utils.add_parents(set(model.staged))
        untracked = utils.add_parents(set(model.untracked))
        upstream_changed = utils.add_parents(set(model.upstream_changed))

        if self.path in unmerged:
            return qtutils.tr('Unmerged')
        if self.path in modified and self.path in staged:
            return qtutils.tr('Partially Staged')
        if self.path in modified:
            return qtutils.tr('Modified')
        if self.path in staged:
            return qtutils.tr('Staged')
        if self.path in untracked:
            return qtutils.tr('Untracked')
        if self.path in upstream_changed:
            return qtutils.tr('Changed Upstream')
        return '-'

    def run(self):
        """Perform expensive lookups and post corresponding events."""
        app = QtGui.QApplication.instance()
        app.postEvent(self.entry,
                GitRepoInfoEvent(GitRepoSignals.Message, self.data('message')))
        app.postEvent(self.entry,
                GitRepoInfoEvent(GitRepoSignals.Age, self.data('date')))
        app.postEvent(self.entry,
                GitRepoInfoEvent(GitRepoSignals.Who, self.data('author')))
        app.postEvent(self.entry,
                GitRepoInfoEvent(GitRepoSignals.Status, self.status()))


class GitRepoInfoEvent(QtCore.QEvent):
    """Transport mechanism for communicating from a GitRepoInfoTask."""
    def __init__(self, *data):
        QtCore.QEvent.__init__(self, QtCore.QEvent.User + 1)
        self.signal = '%s(QString)' % data[0].lower()
        self.data = data[1:]


class GitRepoItem(QtGui.QStandardItem):
    """
    Represents a cell in a treeview.

    Many GitRepoItems map to a single repository path.
    Each GitRepoItem manages a different cell in the tree view.
    One is created for each column -- Name, Status, Age, etc.

    """
    def __init__(self, path, signal):
        QtGui.QStandardItem.__init__(self)
        self.entry = GitRepoEntryManager.entry(path)
        self.path = path
        self.signal = signal
        self.setEditable(False)
        self.setDragEnabled(False)
        self.connect()

    def connect(self):
        """Connect a signal from entry to our setText method."""
        signal = self.signal.lower() + '(QString)'
        QtCore.QObject.connect(self.entry, QtCore.SIGNAL(signal), self.setText)

    def type(self):
        """
        Indicate that this item is of a special user-defined type.

        'name' is the only column that registers a user-defined type.
        This is done to allow filtering out other columns when determining
        which paths are selected.

        """
        if self.signal == GitRepoSignals.Name:
            return QtGui.QStandardItem.UserType + 1
        return QtGui.QStandardItem.type(self)
