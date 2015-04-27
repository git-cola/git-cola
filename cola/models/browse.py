from __future__ import division, absolute_import, unicode_literals

import collections
import time

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import gitcfg
from cola import gitcmds
from cola import core
from cola import utils
from cola import qtutils
from cola import version
from cola import resources
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
    ALL = (NAME, STATUS, AGE, MESSAGE, AUTHOR)

    @classmethod
    def text(cls, column):
        if column == cls.NAME:
            return N_('Name')
        elif column == cls.STATUS:
            return N_('Status')
        elif column == cls.AGE:
            return N_('Age')
        elif column == cls.MESSAGE:
            return N_('Message')
        elif column == cls.AUTHOR:
            return N_('Author')
        else:
            raise NotImplementedError('Mapping required for "%s"' % column)


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
        self._interesting_paths = self._get_paths()
        self._known_paths = set()

        self.connect(self, SIGNAL('updated()'),
                     self._updated_callback, Qt.QueuedConnection)
        model = main.model()
        model.add_observer(model.message_updated, self._model_updated)
        self._dir_rows = collections.defaultdict(int)
        self.setColumnCount(len(Columns.ALL))
        for idx, header in enumerate(Columns.ALL):
            text = Columns.text(header)
            self.setHeaderData(idx, Qt.Horizontal, QtCore.QVariant(text))

        self._direntries = {'': self.invisibleRootItem()}
        self._initialize()

    def mimeData(self, indexes):
        paths = qtutils.paths_from_indexes(self, indexes,
                                           item_type=GitRepoNameItem.TYPE)
        return qtutils.mimedata_from_paths(paths)

    def mimeTypes(self):
        return qtutils.path_mimetypes()

    def _create_column(self, col, path):
        """Creates a StandardItem for use in a treeview cell."""
        # GitRepoNameItem is the only one that returns a custom type(),
        # so we use to infer selections.
        if col == Columns.NAME:
            return GitRepoNameItem(path)
        return GitRepoItem(col, path)

    def _create_row(self, path):
        """Return a list of items representing a row."""
        return [self._create_column(c, path) for c in Columns.ALL]

    def _add_file(self, parent, path, insert=False):
        """Add a file entry to the model."""

        # Create model items
        row_items = self._create_row(path)

        # Use a standard file icon for the name field
        row_items[0].setIcon(qtutils.file_icon())

        if not insert:
            # Add file paths at the end of the list
            parent.appendRow(row_items)
            self.entry(path).update_name()
            self._known_paths.add(path)
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
        self._known_paths.add(path)

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""

        # Create model items
        row_items = self._create_row(path)

        # Use a standard directory icon
        row_items[0].setIcon(qtutils.dir_icon())

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

    def _get_paths(self):
        """Return paths of interest; e.g. paths with a status."""
        model = main.model()
        paths = model.staged + model.unstaged
        return utils.add_parents(paths)

    def _model_updated(self):
        """Observes model changes and updates paths accordingly."""
        self.emit(SIGNAL('updated()'))

    def _updated_callback(self):
        old_paths = self._interesting_paths
        new_paths = self._get_paths()
        for path in new_paths.union(old_paths):
            if path not in self._known_paths:
                continue
            self.entry(path).update()

        self._interesting_paths = new_paths

    def _initialize(self):
        """Iterate over the cola model and create GitRepoItems."""
        for path in gitcmds.all_files():
            self.add_file(path)

    def add_file(self, path, insert=False):
        """Add a file to the model."""
        dirname = utils.dirname(path)
        if dirname in self._direntries:
            parent = self._direntries[dirname]
        else:
            parent = self._create_dir_entry(dirname, self._direntries)
            self._direntries[dirname] = parent
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
        return GitRepoEntryManager.entry(path)


class GitRepoEntryManager(object):
    """
    Provides access to shared GitRepoEntry items and model data.
    """
    static_entries = {}

    @classmethod
    def entry(cls, path, _static_entries=static_entries):
        """Return the shared GitRepoEntry for a path."""
        try:
            e = _static_entries[path]
        except KeyError:
            e = _static_entries[path] = GitRepoEntry(path)
        return e


class TaskRunner(object):
    """Manages QRunnable tasks to avoid python's garbage collector

    When PyQt stops referencing a QRunnable Python cleans it up which leads to
    segfaults, e.g. the dreaded "C++ object has gone away".

    This class keeps track of tasks and cleans up references to them as they
    complete.

    """
    singleton = None

    @classmethod
    def current(cls):
        if cls.singleton is None:
            cls.singleton = TaskRunner()
        return cls.singleton

    def __init__(self):
        self.tasks = set()
        self.threadpool = QtCore.QThreadPool.globalInstance()
        self.notifier = QtCore.QObject()
        self.notifier.connect(self.notifier, SIGNAL('task_done(PyQt_PyObject)'),
                              self.task_done, Qt.QueuedConnection)

    def run(self, task):
        self.tasks.add(task)
        self.threadpool.start(task)

    def task_done(self, task):
        if task in self.tasks:
            self.tasks.remove(task)

    def cleanup_task(self, task):
        self.notifier.emit(SIGNAL('task_done(PyQt_PyObject)'), task)


class GitRepoEntry(QtCore.QObject):
    """
    Provides asynchronous lookup of repository data for a path.

    Emits signal names matching those defined in Columns.

    """
    def __init__(self, path):
        QtCore.QObject.__init__(self)
        self.path = path

    def update_name(self):
        """Emits a signal corresponding to the entry's name."""
        # 'name' is cheap to calculate so simply emit a signal
        self.emit(SIGNAL(Columns.NAME), utils.basename(self.path))
        if '/' not in self.path:
            self.update()

    def update(self):
        """Starts a GitRepoInfoTask to calculate info for entries."""
        # GitRepoInfoTask handles expensive lookups
        task = GitRepoInfoTask(self.path)
        TaskRunner.current().run(task)

    def event(self, e):
        """Receive GitRepoInfoEvents and emit corresponding Qt signals."""
        if e.type() == INFO_EVENT_TYPE:
            e.accept()
            self.emit(SIGNAL(e.signal), *e.data)
            return True
        return QtCore.QObject.event(self, e)


# Support older versions of PyQt
if version.check('pyqt_qrunnable', QtCore.PYQT_VERSION_STR):
    QRunnable = QtCore.QRunnable
else:
    class QRunnable(object):
        pass

class GitRepoInfoTask(QRunnable):
    """Handles expensive git lookups for a path."""
    def __init__(self, path):
        QRunnable.__init__(self)
        self.path = path
        self._cfg = gitcfg.current()
        self._data = {}

    def data(self, key):
        """
        Return git data for a path.

        Supported keys are 'date', 'message', and 'author'

        """
        if not self._data:
            log_line = main.model().git.log('-1', '--', self.path,
                                            M=True,
                                            all=False,
                                            no_color=True,
                                            pretty='format:%ar%x01%s%x01%an'
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
            return (resources.icon('modified.png'), N_('Unmerged'))
        if self.path in modified and self.path in staged:
            return (resources.icon('partial.png'), N_('Partially Staged'))
        if self.path in modified:
            return (resources.icon('modified.png'), N_('Modified'))
        if self.path in staged:
            return (resources.icon('staged.png'), N_('Staged'))
        if self.path in upstream_changed:
            return (resources.icon('upstream.png'), N_('Changed Upstream'))
        if self.path in untracked:
            return (None, '?')
        return (None, '')

    def run(self):
        """Perform expensive lookups and post corresponding events."""
        app = QtGui.QApplication.instance()
        entry = GitRepoEntryManager.entry(self.path)
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.MESSAGE, self.data('message')))
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.AGE, self.data('date')))
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.AUTHOR, self.data('author')))
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.STATUS, self.status()))

        TaskRunner.current().cleanup_task(self)


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
    def __init__(self, column, path):
        QtGui.QStandardItem.__init__(self)
        self.path = path
        self.setDragEnabled(False)
        self.setEditable(False)
        entry = GitRepoEntryManager.entry(path)
        if column == Columns.STATUS:
            QtCore.QObject.connect(entry, SIGNAL(column), self.set_status)
        else:
            QtCore.QObject.connect(entry, SIGNAL(column), self.setText)

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

    def __init__(self, path):
        GitRepoItem.__init__(self, Columns.NAME, path)
        self.path = path
        self.setDragEnabled(True)

    def type(self):
        """
        Indicate that this item is of a special user-defined type.

        'name' is the only column that registers a user-defined type.
        This is done to allow filtering out other columns when determining
        which paths are selected.

        """
        return GitRepoNameItem.TYPE
