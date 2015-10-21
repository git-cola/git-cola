# Copyright (c) 2008 David Aguilar
# Copyright (c) 2015 Daniel Harding
"""Provides an filesystem monitoring for Linux (via inotify) and for Windows
(via pywin32 and the ReadDirectoryChanges function)"""
from __future__ import division, absolute_import, unicode_literals

import errno
import os
import os.path
import select
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
elif utils.is_linux():
    try:
        from cola import inotify
    except ImportError:
        pass
    else:
        AVAILABLE = 'inotify'

from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import gitcfg
from cola import gitcmds
from cola.compat import bchr
from cola.git import git
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

    def refresh(self):
        if self._thread is not None:
            self._thread.refresh()


class _BaseThread(QtCore.QThread):
    #: The delay, in milliseconds, between detecting file system modification
    #: and triggering the 'files_changed' signal, to coalesce multiple
    #: modifications into a single signal.
    _NOTIFICATION_DELAY = 888

    def __init__(self, monitor):
        QtCore.QThread.__init__(self)
        self._monitor = monitor
        self._running = True
        self._pending = False

    def refresh(self):
        """Do any housekeeping necessary in response to repository changes."""
        pass

    def notify(self):
        """Notifies all observers"""
        self._pending = False
        self._monitor.emit(SIGNAL('files_changed'))

    @staticmethod
    def _log_enabled_message():
        msg = N_('File system change monitoring: enabled.\n')
        Interaction.safe_log(msg)


if AVAILABLE == 'inotify':
    class _InotifyThread(_BaseThread):
        _TRIGGER_MASK = (
                inotify.IN_ATTRIB |
                inotify.IN_CLOSE_WRITE |
                inotify.IN_CREATE |
                inotify.IN_DELETE |
                inotify.IN_MODIFY |
                inotify.IN_MOVED_FROM |
                inotify.IN_MOVED_TO
        )
        _ADD_MASK = (
                _TRIGGER_MASK |
                inotify.IN_EXCL_UNLINK |
                inotify.IN_ONLYDIR
        )

        def __init__(self, monitor):
            _BaseThread.__init__(self, monitor)
            self._worktree = core.abspath(git.worktree())
            self._git_dir = git.git_dir()
            self._lock = Lock()
            self._inotify_fd = None
            self._pipe_r = None
            self._pipe_w = None
            self._worktree_wds = set()
            self._worktree_wd_map = {}
            self._git_dir_wds = set()
            self._git_dir_wd_map = {}

        @staticmethod
        def _log_out_of_wds_message():
            msg = N_('File system change monitoring: disabled because the'
                         ' limit on the total number of inotify watches was'
                         ' reached.  You may be able to increase the limit on'
                         ' the number of watches by running:\n'
                     '\n'
                     '    echo fs.inotify.max_user_watches=100000 |'
                         ' sudo tee -a /etc/sysctl.conf &&'
                         ' sudo sysctl -p\n')
            Interaction.safe_log(msg)

        def run(self):
            try:
                with self._lock:
                    self._inotify_fd = inotify.init()
                    self._pipe_r, self._pipe_w = os.pipe()

                poll_obj = select.poll()
                poll_obj.register(self._inotify_fd, select.POLLIN)
                poll_obj.register(self._pipe_r, select.POLLIN)

                self.refresh()

                self._log_enabled_message()

                while self._running:
                    if self._pending:
                        timeout = self._NOTIFICATION_DELAY
                    else:
                        timeout = None
                    try:
                        events = poll_obj.poll(timeout)
                    except OSError as e:
                        if e.errno == errno.EINTR:
                            continue
                        else:
                            raise
                    else:
                        if not self._running:
                            break
                        elif not events:
                            self.notify()
                        else:
                            for fd, event in events:
                                if fd == self._inotify_fd:
                                    self._handle_events()
            finally:
                with self._lock:
                    if self._inotify_fd is not None:
                        os.close(self._inotify_fd)
                        self._inotify_fd = None
                    if self._pipe_r is not None:
                        os.close(self._pipe_r)
                        self._pipe_r = None
                        os.close(self._pipe_w)
                        self._pipe_w = None

        def refresh(self):
            with self._lock:
                if self._inotify_fd is None:
                    return
                try:
                    tracked_dirs = set(os.path.dirname(
                                           os.path.join(self._worktree, path))
                                       for path in gitcmds.tracked_files())
                    self._refresh_watches(tracked_dirs, self._worktree_wds,
                                          self._worktree_wd_map)
                    git_dirs = set()
                    git_dirs.add(self._git_dir)
                    for dirpath, dirnames, filenames in core.walk(
                            os.path.join(self._git_dir, 'refs')):
                        git_dirs.add(dirpath)
                    self._refresh_watches(git_dirs, self._git_dir_wds,
                                          self._git_dir_wd_map)
                except OSError as e:
                    if e.errno == errno.ENOSPC:
                        self._log_out_of_wds_message()
                        self._running = False
                    else:
                        raise

        def _refresh_watches(self, paths_to_watch, wd_set, wd_map):
            watched_paths = set(wd_map)
            for path in watched_paths - paths_to_watch:
                wd = wd_map.pop(path)
                wd_set.remove(wd)
                try:
                    inotify.rm_watch(self._inotify_fd, wd)
                except OSError as e:
                    if e.errno == errno.EINVAL:
                        # This error can occur if the target of the wd was
                        # removed on the filesystem before we call
                        # inotify.rm_watch() so ignore it.
                        pass
                    else:
                        raise
            for path in paths_to_watch - watched_paths:
                try:
                    wd = inotify.add_watch(self._inotify_fd, core.encode(path),
                                           self._ADD_MASK)
                except OSError as e:
                    if e.errno in (errno.ENOENT, errno.ENOTDIR):
                        # These two errors should only occur as a result of
                        # race conditions:  the first if the directory
                        # referenced by path was removed or renamed before the
                        # call to inotify.add_watch(); the second if the
                        # directory referenced by path was replaced with a file
                        # before the call to inotify.add_watch().  Therefore we
                        # simply ignore them.
                        pass
                    else:
                        raise
                else:
                    wd_set.add(wd)
                    wd_map[path] = wd

        def _filter_event(self, wd, mask, name):
            # An event is relevant iff:
            # 1) it is an event queue overflow
            # 2) the wd is for the worktree
            # 3) the wd is for the git dir and
            #    a) the event is for a file, and
            #    b) the file name does not end with ".lock"
            if mask & inotify.IN_Q_OVERFLOW:
                return True
            if mask & self._TRIGGER_MASK:
                if wd in self._worktree_wds:
                    return True
                if (wd in self._git_dir_wds
                        and not mask & inotify.IN_ISDIR
                        and not core.decode(name).endswith('.lock')):
                    return True
            return False

        def _handle_events(self):
            for wd, mask, cookie, name in \
                    inotify.read_events(self._inotify_fd):
                if self._filter_event(wd, mask, name):
                    self._pending = True

        def stop(self):
            self._running = False
            with self._lock:
                if self._pipe_w is not None:
                    os.write(self._pipe_w, bchr(0))
            self.wait()


if AVAILABLE == 'pywin32':
    class _Win32Watch(object):
        def __init__(self, path, flags):
            self.flags = flags

            self.handle = None
            self.event = None

            try:
                self.handle = win32file.CreateFileW(
                        path,
                        0x0001, # FILE_LIST_DIRECTORY
                        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                        None,
                        win32con.OPEN_EXISTING,
                        win32con.FILE_FLAG_BACKUP_SEMANTICS |
                            win32con.FILE_FLAG_OVERLAPPED,
                        None)

                self.buffer = win32file.AllocateReadBuffer(8192)
                self.event = win32event.CreateEvent(None, True, False, None)
                self.overlapped = pywintypes.OVERLAPPED()
                self.overlapped.hEvent = self.event
                self._start()
            except:
                self.close()
                raise

        def _start(self):
            win32file.ReadDirectoryChangesW(self.handle, self.buffer, True,
                                            self.flags, self.overlapped)

        def read(self):
            if win32event.WaitForSingleObject(self.event, 0) \
                    == win32event.WAIT_TIMEOUT:
                result = []
            else:
                nbytes = win32file.GetOverlappedResult(self.handle,
                                                       self.overlapped, False)
                result = win32file.FILE_NOTIFY_INFORMATION(self.buffer, nbytes)
                self._start()
            return result

        def close(self):
            if self.handle is not None:
                win32file.CancelIo(self.handle)
                win32file.CloseHandle(self.handle)
            if self.event is not None:
                win32file.CloseHandle(self.event)


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
            self._worktree_watch = None
            self._git_dir = self._transform_path(core.abspath(git.git_dir()))
            self._git_dir_watch = None
            self._stop_event_lock = Lock()
            self._stop_event = None

        @staticmethod
        def _transform_path(path):
            return path.replace('\\', '/').lower()

        def _read_watch(self, watch):
            if win32event.WaitForSingleObject(watch.event, 0) \
                    == win32event.WAIT_TIMEOUT:
                nbytes = 0
            else:
                nbytes = win32file.GetOverlappedResult(watch.handle,
                                                       watch.overlapped, False)
            return win32file.FILE_NOTIFY_INFORMATION(watch.buffer, nbytes)

        def run(self):
            try:
                with self._stop_event_lock:
                    self._stop_event = win32event.CreateEvent(None, True,
                                                              False, None)

                self._worktree_watch = _Win32Watch(self._worktree, self._FLAGS)
                self._git_dir_watch = _Win32Watch(self._git_dir, self._FLAGS)

                self._log_enabled_message()

                events = [self._worktree_watch.event,
                          self._git_dir_watch.event,
                          self._stop_event]
                while self._running:
                    if self._pending:
                        timeout = self._NOTIFICATION_DELAY
                    else:
                        timeout = win32event.INFINITE
                    rc = win32event.WaitForMultipleObjects(events, False,
                                                           timeout)
                    if not self._running:
                        break
                    elif rc == win32event.WAIT_TIMEOUT:
                        self.notify()
                    else:
                        self._handle_results()
            finally:
                with self._stop_event_lock:
                    if self._stop_event is not None:
                        win32file.CloseHandle(self._stop_event)
                        self._stop_event = None
                if self._worktree_watch is not None:
                    self._worktree_watch.close()
                if self._git_dir_watch is not None:
                    self._git_dir_watch.close()

        def _handle_results(self):
            for action, path in self._worktree_watch.read():
                if not self._running:
                    break
                path = self._worktree + '/' + self._transform_path(path)
                if (path != self._git_dir
                        and not path.startswith(self._git_dir + '/')):
                    self._pending = True
            for action, path in self._git_dir_watch.read():
                if not self._running:
                    break
                if not path.endswith('.lock'):
                    self._pending = True

        def stop(self):
            self._running = False
            with self._stop_event_lock:
                if self._stop_event is not None:
                    win32event.SetEvent(self._stop_event)
            self.wait()


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
        msg = N_('File system change monitoring: disabled because'
                 ' "cola.inotify" is false.\n')
        Interaction.log(msg)
    elif AVAILABLE == 'inotify':
        thread_class = _InotifyThread
    elif AVAILABLE == 'pywin32':
        thread_class = _Win32Thread
    else:
        if utils.is_win32():
            msg = N_('File system change monitoring: disabled because pywin32'
                     ' is not installed.\n')
            Interaction.log(msg)
        elif utils.is_linux():
            msg = N_('File system change monitoring: disabled because libc'
                     ' does not support the inotify system calls.\n')
            Interaction.log(msg)
    return _Monitor(thread_class)
