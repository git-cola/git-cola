#!/usr/bin/env python
import os
import sys

from PyQt4 import QtGui

from ugit import utils
from ugit import qtutils
from ugit.qobserver import QObserver
from ugit.ugitrc import SettingsModel
from ugit.views import BookmarkView

def save_bookmark():
	model = SettingsModel()
	bookmark = os.getcwd()
	if bookmark not in model.bookmarks:
		model.add_bookmarks(bookmark)
	model.save_all_settings()
	qtutils.information("Bookmark Saved")

def manage_bookmarks():
	model = SettingsModel()
	view = BookmarkView(QtGui.qApp.activeWindow())
	ctl = BookmarkController(model, view)
	view.show()
	if view.exec_() == QtGui.QDialog.Accepted:
		model.save_all_settings()

class BookmarkController(QObserver):
	def init(self, model, view):
		self.add_observables( 'bookmarks' )

		self.add_callbacks(
			button_open = self.open,
			button_delete = self.delete,
			)
		self.refresh_view()
	
	def open(self):
		selection = qtutils.get_selection_list(
					self.view.bookmarks,
					self.model.bookmarks)
		if not selection:
			return
		for item in selection:
			utils.fork("git", "ugit", item)

	def delete(self):
		selection = qtutils.get_selection_list(
					self.view.bookmarks,
					self.model.bookmarks)
		if not selection:
			return
		for item in selection:
			self.model.bookmarks.remove(item)
		self.refresh_view()
