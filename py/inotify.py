#!/usr/bin/env python
import os
import cmds
from PyQt4.QtCore import QThread, SIGNAL
from pyinotify import ProcessEvent
from pyinotify import WatchManager, Notifier, EventsCodes

class FileSysEvent (ProcessEvent):
	def __init__ (self, parent):
		ProcessEvent.__init__ (self)
		self.parent = parent
	def process_default (self, event):
		self.parent.notify()

class GitNotifier (QThread):
	def __init__ (self, path):
		QThread.__init__ (self)
		self.path = path
		self.abort = False

	def notify (self):
		self.emit ( SIGNAL ('timeForRescan()') )

	def run (self):
		# Only capture those events that git cares about
		mask = ( EventsCodes.IN_CREATE
			| EventsCodes.IN_DELETE
			| EventsCodes.IN_MOVED_TO
			| EventsCodes.IN_MODIFY )

		wm = WatchManager()
		notifier = Notifier (wm, FileSysEvent(self))
		self.notifier = notifier

		dirs_seen = {}
		added_flag = False
		while not self.abort:

			if not added_flag:
				wm.add_watch (self.path, mask)
				# Register files/directories known to git
				for file in cmds.git_ls_files():
					wm.add_watch (file, mask)
					directory = os.path.dirname (file)
					if directory not in dirs_seen:
						wm.add_watch (directory, mask)
						dirs_seen[directory] = True
				added_flag = True
			notifier.process_events()

			if notifier.check_events():
				notifier.read_events()

			self.msleep (200)

		notifier.stop()
