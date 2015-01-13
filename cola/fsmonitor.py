# Copyright (c) 2008 David Aguilar
"""Provides an inotify plugin for Linux and other systems with pyinotify"""
from __future__ import division, absolute_import, unicode_literals

import os
from threading import Timer
from threading import Lock


from cola import utils

AVAILABLE = None

if utils.is_win32():
    try:
        import pywintypes
        import win32con
        import win32event
        import win32file
    except ImportError:
        pass
    else:
        AVAILABLE = 'pywin32'
else:
    try:
        import pyinotify
        from pyinotify import EventsCodes
        from pyinotify import Notifier
        from pyinotify import ProcessEvent
        from pyinotify import WatchManager
        from pyinotify import WatchManagerError
    except Exception:
        pass
    else:
        AVAILABLE = 'pyinotify'

from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola import gitcfg
from cola import core
from cola.compat import ustr, PY3
from cola.git import git
from cola.git import STDOUT
from cola.i18n import N_
from cola.interaction import Interaction


class _Monitor(QtCore.QObject):
    def __init__(self, thread_class):
        QtCore.QObject.__init__(self)
        self._thread_class = thread_class
        self._thread = None

    def start(self):
        if self._thread_class is not None:
            assert self._thread is None
            self._thread = self._thread_class(self)
            self._thread.start()

    def stop(self):
        if self._thread_class is not None:
            assert self._thread is not None
            self._thread.stop()
            self._thread.wait()
            self._thread = None


class _BaseThread(QtCore.QThread):
    def __init__(self, monitor):
        QtCore.QThread.__init__(self)
        self._monitor = monitor
        self._timeout = 333
        self._running = True
        ## Timer used to prevent notification floods
        self._timer = None
        ## Lock to protect timer from threading issues
        self._lock = Lock()

    def trigger(self):
        """Start a timer which will notify all observers on expiry"""
        with self._lock:
            if self._timer is None:
                self._timer = Timer(0.888, self.notify)
                self._timer.start()

    def notify(self):
        """Notifies all observers"""
        self._monitor.emit(SIGNAL('files_changed'))
        with self._lock:
            self._timer = None

    def stop(self):
        self._timeout = 0
        self._running = False
        self.wait()


if AVAILABLE == 'pyinotify':
    class _InotifyThread(_BaseThread):
        ## Events to capture
        _MASK = (EventsCodes.ALL_FLAGS['IN_ATTRIB'] |
                 EventsCodes.ALL_FLAGS['IN_CLOSE_WRITE'] |
                 EventsCodes.ALL_FLAGS['IN_CREATE'] |
                 EventsCodes.ALL_FLAGS['IN_DELETE'] |
                 EventsCodes.ALL_FLAGS['IN_MODIFY'] |
                 EventsCodes.ALL_FLAGS['IN_MOVED_TO'])

        class _EventHandler(ProcessEvent):
            def __init__(self, monitor):
                ProcessEvent.__init__(self)
                self._monitor = monitor

            def process_default(self, event):
                if event.name:
                    self._monitor.trigger()

        def __init__(self, monitor):
            """Set up the pyinotify thread"""
            _BaseThread.__init__(self, monitor)
            ## Directories to watching
            self._dirs_seen = set()
            ## The inotify watch manager instantiated in run()
            self._manager = None
            ## Has add_watch() failed?
            self._add_watch_failed = False

        @staticmethod
        def _is_pyinotify_08x():
            """Is this pyinotify 0.8.x?

            The pyinotify API changed between 0.7.x and 0.8.x.
            This allows us to maintain backwards compatibility.
            """
            if hasattr(pyinotify, '__version__'):
                if pyinotify.__version__[:3] < '0.8':
                    return False
            return True

        def _watch_directory(self, directory):
            """Set up a directory for monitoring by inotify"""
            if self._manager is None or self._add_watch_failed:
                return
            directory = core.realpath(directory)
            if directory in self._dirs_seen:
                return
            self._dirs_seen.add(directory)
            if core.exists(directory):
                dir_arg = directory if PY3 else core.encode(directory)
                try:
                    self._manager.add_watch(dir_arg, self._MASK, quiet=False)
                except WatchManagerError as e:
                    self._add_watch_failed = True
                    self._add_watch_failed_warning(directory, e)

        @staticmethod
        def _add_watch_failed_warning(directory, e):
            msg = ('inotify: failed to watch "{}": {}\n'
                   'If you have run out of watches then you may be able to'
                       ' increase the number of allowed watches by running:\n'
                   '\n'
                   '    echo fs.inotify.max_user_watches=100000 |'
                       ' sudo tee -a /etc/sysctl.conf &&'
                       ' sudo sysctl -p\n'.format(directory, e))
            Interaction.safe_log(msg)

        def run(self):
            # Only capture events that git cares about
            self._manager = WatchManager()
            event_handler = self._EventHandler(self)
            if self._is_pyinotify_08x():
                notifier = Notifier(self._manager, event_handler,
                                    timeout=self._timeout)
            else:
                notifier = Notifier(self._manager, event_handler)

            self._watch_directory(self._worktree)

            # Register files/directories known to git
            for filename in git.ls_files()[STDOUT].splitlines():
                filename = core.realpath(filename)
                directory = os.path.dirname(filename)
                self._watch_directory(directory)

            msg = N_('inotify enabled.')
            Interaction.safe_log(msg)

            # self._running signals app termination.  The timeout is a tradeoff
            # between fast notification response and waiting too long to exit.
            while self._running:
                if self._is_pyinotify_08x():
                    check = notifier.check_events()
                else:
                    check = notifier.check_events(timeout=self._timeout)
                if not self._running:
                    break
                if check:
                    notifier.read_events()
                    notifier.process_events()
            notifier.stop()


if AVAILABLE == 'pywin32':
    class _Win32Thread(_BaseThread):
        _FLAGS = (win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
                  win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
                  win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                  win32con.FILE_NOTIFY_CHANGE_SIZE |
                  win32con.FILE_NOTIFY_CHANGE_LAST_WRITE |
                  win32con.FILE_NOTIFY_CHANGE_SECURITY)

        def __init__(self, monitor):
            _BaseThread.__init__(self, monitor)
            self._worktree = self._transform_path(core.abspath(git.worktree()))
            self._git_dir = self._transform_path(git.git_dir())

        @staticmethod
        def _transform_path(path):
            return path.replace('\\', '/').lower()

        def run(self):
            hdir = win32file.CreateFile(
                    self._worktree,
                    0x0001,
                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                    None,
                    win32con.OPEN_EXISTING,
                    win32con.FILE_FLAG_BACKUP_SEMANTICS |
                    win32con.FILE_FLAG_OVERLAPPED,
                    None)

            buf = win32file.AllocateReadBuffer(8192)
            overlapped = pywintypes.OVERLAPPED()
            overlapped.hEvent = win32event.CreateEvent(None, 0, 0, None)

            msg = N_('File notification enabled.')
            Interaction.safe_log(msg)

            while self._running:
                win32file.ReadDirectoryChangesW(hdir, buf, True, self._FLAGS,
                                                overlapped)

                rc = win32event.WaitForSingleObject(overlapped.hEvent,
                                                    self._timeout)
                if rc != win32event.WAIT_OBJECT_0:
                    continue
                nbytes = win32file.GetOverlappedResult(hdir, overlapped, True)
                if not nbytes:
                    continue
                results = win32file.FILE_NOTIFY_INFORMATION(buf, nbytes)
                for action, path in results:
                    if not self._running:
                        break
                    path = self._worktree + '/' + self._transform_path(path)
                    if (path != self._git_dir
                            and not path.startswith(self._git_dir + '/')):
                        self.trigger()


_instance = None

def instance():
    global _instance
    if _instance is None:
        _instance = _create_instance()
    return _instance


def _create_instance():
    thread_class = None
    cfg = gitcfg.current()
    if not cfg.get('cola.inotify', True):
        msg = N_('inotify is disabled because "cola.inotify" is false')
        Interaction.log(msg)
    elif AVAILABLE == 'pyinotify':
        thread_class = _InotifyThread
    elif AVAILABLE == 'pywin32':
        thread_class = _Win32Thread
    else:
        if utils.is_win32():
            msg = N_('file notification: disabled\n'
                     'Note: install pywin32 to enable.\n')
            Interaction.log(msg)
        elif utils.is_linux():
            msg = N_('inotify: disabled\n'
                     'Note: install python-pyinotify to enable inotify.\n')
            if utils.is_debian():
                msg += N_('On Debian-based systems '
                          'try: sudo apt-get install python-pyinotify\n')
            Interaction.log(msg)
    return _Monitor(thread_class)
