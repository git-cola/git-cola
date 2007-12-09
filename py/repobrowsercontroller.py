#!/usr/bin/env python
import os
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFileDialog
from qobserver import QObserver
import cmds
import utils
import qtutils
import defaults

class GitRepoBrowserController (QObserver):
	def __init__ (self, model, view):
		QObserver.__init__ (self, model, view)

		model.add_observer (self)

		view.setWindowTitle ('Git Repo Browser')

		self.add_signals ('itemSelectionChanged()',
				view.commitList,)

		self.add_actions (model, 'directory',
				self.action_directory_changed)

		self.add_callbacks (model, {
				'commitList': self.cb_item_changed,
				})

		self.connect (view.commitList,
				SIGNAL ('itemDoubleClicked(QListWidgetItem*)'),
				lambda(x): self.cb_item_double_clicked (model))

		# Collect data for the model
		tree_info = cmds.git_ls_tree (model.get_branch())

		types = map ( lambda (x): x[1], tree_info )
		sha1s = map ( lambda (x): x[2], tree_info )
		files = map ( lambda (x): x[3], tree_info )

		model.add_types (*types)
		model.add_files (*files)
		model.add_sha1s (*sha1s)

		model.setup_items()

		self.__display_items (model)

	######################################################################
	# ACTIONS
	######################################################################

	def action_directory_changed (self, model, *args):
		'''This is called in response to a change in the the
		model's directory.'''
		model.setup_items()
		self.__display_items (model)

	######################################################################
	# CALLBACKS
	######################################################################

	def cb_item_changed (self, model, *args):
		'''This is called when the current item changes in the
		file/directory list (aka the commitList).'''
		current = self.view.commitList.currentRow()
		item = self.view.commitList.item (current)
		if item is None or not item.isSelected():
			self.view.revisionLine.setText ('')
			self.view.commitText.setText ('')
			return
		item_names = model.get_item_names()
		item_sha1s = model.get_item_sha1s()
		item_types = model.get_item_types()
		directories = model.get_directories()
		directory_entries = model.get_directory_entries()

		if current < len (directories):
			# This is a directory...
			dirent = directories[current]
			if dirent != '..':
				# This is a real directory for which
				# we have child entries
				msg = 'Directory: ' + dirent
				header = utils.html_header (msg)
				entries = directory_entries[dirent]
			else:
				# This is '..' which is a special case
				# since it doesn't really exist
				msg = 'Parent Directory'
				header = utils.html_header (msg)
				entries = []

			contents = '<pre>%s</pre>' % '\n'.join (entries)

			self.view.commitText.setHtml (header + contents)
			self.view.revisionLine.setText ('')
		else:
			# This is a file entry.  The current row is absolute,
			# so get a relative index by subtracting the number
			# of directory entries
			idx = current - len (directories)

			if idx >= len (item_sha1s):
				# This can happen when changing directories
				return

			sha1 = item_sha1s[idx]
			objtype = item_types[idx]
			filename = item_names[idx]

			guts = cmds.git_cat_file (objtype, sha1)
			header = utils.html_header ('File: ' + filename)
			contents = '<pre>%s</pre>' % utils.html_encode (guts)

			self.view.commitText.setHtml (header + contents)

			self.view.revisionLine.setText (sha1)
			self.view.revisionLine.selectAll()

			# Copy the sha1 into the clipboard
			qtutils.set_clipboard (sha1)

	def cb_item_double_clicked (self, model):
		'''This is called when an entry is double-clicked.
		This callback changes the model's directory when
		invoked on a directory item.  When invoked on a file
		it allows the file to be saved.'''

		current = self.view.commitList.currentRow()
		directories = model.get_directories()

		# A file item was double-clicked.
		# Create a save-as dialog and export the file.
		if current >= len (directories):
			idx = current - len (directories)

			names = model.get_item_names()
			sha1s = model.get_item_sha1s()
			types = model.get_item_types()

			objtype = types[idx]
			sha1 = sha1s[idx]
			name = names[idx]

			file_to_save = os.path.join(defaults.DIRECTORY, name)

			qstr_filename = QFileDialog.getSaveFileName(self.view,
					'Git File Export', file_to_save)
			if not qstr_filename: return

			filename = str (qstr_filename)
			defaults.DIRECTORY = os.path.dirname (filename)
			cmds.git_cat_file (objtype, sha1, filename)
			return

		dirent = directories[current]
		curdir = model.get_directory()

		if dirent == '..':
			newdir = os.path.normpath (curdir + '..')
			if newdir == '.' or not newdir:
				model.set_directory ('')
			else:
				model.set_directory (newdir + '/')
		else:
			model.set_directory (curdir + dirent)

	######################################################################
	# PRIVATE HELPER METHODS
	######################################################################

	def __display_items (self, model):
		'''This method populates the commitList (aka item list)
		with the current directories and items.  Directories are
		always listed first.'''

		self.view.commitList.clear()
		self.view.commitText.setText ('')
		self.view.revisionLine.setText ('')

		dir_icon = utils.get_directory_icon()
		file_icon = utils.get_file_icon()

		for entry in model.get_directories():
			item = qtutils.create_listwidget_item(entry, dir_icon)
			self.view.commitList.addItem (item)

		for entry in model.get_item_names():
			item = qtutils.create_listwidget_item(entry, file_icon)
			self.view.commitList.addItem (item)
