#!/usr/bin/env python
# Copyright (c) 2008 David Aguilar
import os
import time
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtCore import QThread
from PyQt4.QtCore import QEvent
from PyQt4.QtCore import SIGNAL
from pyinotify import ProcessEvent
from pyinotify import WatchManager, Notifier, EventsCodes

from models import GitCola
import defaults

class FileSysEvent(ProcessEvent):
    def __init__(self, parent):
        ProcessEvent.__init__(self)
        self.parent = parent
        self.last_event_time = time.time()
    def process_default(self, event):
        # Prevent notificaiton floods
        if time.time() - self.last_event_time > 1.0:
            self.parent.notify()
        self.last_event_time = time.time()

class GitNotifier(QThread):
    def __init__(self, receiver, path):
        QThread.__init__(self)
        self.git = GitCola()
        self.receiver = receiver
        self.path = path
        self.abort = False
        self.dirs_seen = {}
        self.mask = (EventsCodes.IN_CREATE |
                     EventsCodes.IN_DELETE |
                     EventsCodes.IN_MODIFY |
                     EventsCodes.IN_MOVED_TO)

    def notify(self):
        if not self.abort:
            event_type = QEvent.Type(defaults.INOTIFY_EVENT)
            event = QEvent(event_type)
            QCoreApplication.postEvent(self.receiver, event)

    def watch_directory(self, directory):
        directory = os.path.realpath(directory)
        if directory not in self.dirs_seen:
            self.wm.add_watch(directory, self.mask)
            self.dirs_seen[directory] = True
    
    def run(self):
        # Only capture those events that git cares about
        self.wm = WatchManager()
        notifier = Notifier(self.wm, FileSysEvent(self))
        self.notifier = notifier
        dirs_seen = {}
        added_flag = False
        while not self.abort:
            if not added_flag:
                self.watch_directory(self.path)
                # Register files/directories known to git
                for file in self.git.ls_files().splitlines():
                    directory = os.path.dirname(file)
                    self.watch_directory(directory)
                added_flag = True
            notifier.process_events()
            if notifier.check_events(timeout=250):
                notifier.read_events()
        notifier.stop()
