#!/usr/bin/env python
import os
import time
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtCore import QThread
from PyQt4.QtCore import QEvent
from PyQt4.QtCore import SIGNAL
from pyinotify import ProcessEvent
from pyinotify import WatchManager, Notifier, EventsCodes

import git
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
		self.receiver = receiver
		self.path = path
		self.abort = False

	def notify(self):
		if not self.abort:
			event_type = QEvent.Type(defaults.INOTIFY_EVENT)
			event = QEvent(event_type)
			QCoreApplication.postEvent(self.receiver, event)

	def run(self):
		# Only capture those events that git cares about
		mask =  ( EventsCodes.IN_CREATE
			| EventsCodes.IN_DELETE
			| EventsCodes.IN_MODIFY
			| EventsCodes.IN_MOVED_TO)
		wm = WatchManager()
		notifier = Notifier(wm, FileSysEvent(self))
		self.notifier = notifier
		dirs_seen = {}
		added_flag = False
		while not self.abort:
			if not added_flag:
				wm.add_watch(self.path, mask)
				# Register files/directories known to git
				for file in git.ls_files():
					wm.add_watch(file, mask)
					directory = os.path.dirname(file)
					if directory not in dirs_seen:
						wm.add_watch(directory, mask)
						dirs_seen[directory] = True
				added_flag = True
			notifier.process_events()
			if notifier.check_events():
				notifier.read_events()
		notifier.stop()
