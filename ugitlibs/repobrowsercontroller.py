#!/usr/bin/env python
import os
from PyQt4.QtGui import QDialog
from qobserver import QObserver
import utils
import qtutils
import defaults
from views import CommitBrowser

def browse_git_branch(model, parent, branch):
		if not branch: return
		# Clone the model to allow opening multiple browsers
		# with different sets of data
		model = model.clone(init=False)
		model.set_branch(branch)
		view = CommitBrowser(parent)
		controller = RepoBrowserController(model, view)
		view.show()
		return view.exec_() == QDialog.Accepted

class RepoBrowserController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self, model, view)

		view.setWindowTitle('File Browser')
		self.add_signals('itemSelectionChanged()', view.commitList,)
		self.add_actions('directory', self.action_directory_changed)
		self.add_callbacks({ 'commitList': self.item_changed, })
		self.connect(
			view.commitList, 'itemDoubleClicked(QListWidgetItem*)',
			self.item_double_clicked)

		# Start at the root of the tree
		model.set_directory('')

	######################################################################
	# Actions

	def action_directory_changed(self):
		'''This is called in response to a change in the the
		model's directory.'''
		self.model.init_browser_data()
		self.__display_items()

	######################################################################
	# Qt callbacks

	def item_changed(self,*rest):
		'''This is called when the current item changes in the
		file/directory list(aka the commitList).'''
		current = self.view.commitList.currentRow()
		item = self.view.commitList.item(current)
		if item is None or not item.isSelected():
			self.view.revisionLine.setText('')
			self.view.commitText.setText('')
			return

		directories = self.model.get_directories()
		directory_entries = self.model.get_directory_entries()

		if current < len(directories):
			# This is a directory...
			dirent = directories[current]
			if dirent != '..':
				# This is a real directory for which
				# we have child entries
				msg = utils.header('Directory:' + dirent)
				entries = directory_entries[dirent]
			else:
				# This is '..' which is a special case
				# since it doesn't really exist
				msg = utils.header('Parent Directory')
				entries = []

			contents = '\n'.join(entries)

			self.view.commitText.setText(msg + contents)
			self.view.revisionLine.setText('')
		else:
			# This is a file entry.  The current row is absolute,
			# so get a relative index by subtracting the number
			# of directory entries
			idx = current - len(directories)

			if idx >= len(self.model.get_subtree_sha1s()):
				# This can happen when changing directories
				return

			objtype, sha1, name = \
				self.model.get_subtree_node(idx)

			guts = self.model.cat_file(objtype, sha1)
			header = utils.header('File: ' + name)
			contents = guts

			self.view.commitText.setText(header + contents)

			self.view.revisionLine.setText(sha1)
			self.view.revisionLine.selectAll()

			# Copy the sha1 into the clipboard
			qtutils.set_clipboard(sha1)

	def item_double_clicked(self,*rest):
		'''This is called when an entry is double-clicked.
		This callback changes the model's directory when
		invoked on a directory item.  When invoked on a file
		it allows the file to be saved.'''

		current = self.view.commitList.currentRow()
		directories = self.model.get_directories()

		# A file item was double-clicked.
		# Create a save-as dialog and export the file.
		if current >= len(directories):
			idx = current - len(directories)

			objtype, sha1, name = \
				self.model.get_subtree_node(idx)

			nameguess = os.path.join(defaults.DIRECTORY, name)

			filename = qtutils.save_dialog(self.view, 'Save', nameguess)
			if not filename: return

			defaults.DIRECTORY = os.path.dirname(filename)
			contents = self.model.cat_file(objtype, sha1)

			utils.write(filename, contents)
			return

		dirent = directories[current]
		curdir = self.model.get_directory()

		# '..' is a special case--it doesn't really exist...
		if dirent == '..':
			newdir = os.path.dirname(os.path.dirname(curdir))
			if newdir == '':
				self.model.set_directory(newdir)
			else:
				self.model.set_directory(newdir + os.sep)
		else:
			self.model.set_directory(curdir + dirent)

	######################################################################

	def __display_items(self):
		'''This method populates the commitList(aka item list)
		with the current directories and items.  Directories are
		always listed first.'''

		self.view.commitText.setText('')
		self.view.revisionLine.setText('')

		dir_icon = utils.get_directory_icon()
		file_icon = utils.get_file_icon()

		qtutils.set_items(self.view.commitList,
				map(lambda d: qtutils.create_listwidget_item(d, dir_icon),
						self.model.get_directories()))

		qtutils.add_items(self.view.commitList,
				map(lambda s: qtutils.create_listwidget_item(s, file_icon),
						self.model.get_subtree_names()))
