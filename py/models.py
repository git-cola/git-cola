import os
import re
import commands
import cmds
from model import Model

class GitModel(Model):
	def __init__ (self):
		Model.__init__ (self, {
			# ===========================================
			# Used in various places
			# ===========================================
			'branch': '',

			# ===========================================
			# Used primarily by the main UI
			# ===========================================
			'name': cmds.git_config('user.name'),
			'email': cmds.git_config('user.email'),
			'commitmsg': '',
			'staged': [],
			'unstaged': [],
			'untracked': [],

			# ===========================================
			# Used by the create branch dialog
			# ===========================================
			'revision': '',
			'local_branches': cmds.git_branch (remote=False),
			'remote_branches': cmds.git_branch (remote=True),
			'tags': cmds.git_tag(),

			# ===========================================
			# Used by the repo browser
			# ===========================================
			'directory': '',

			# These are parallel lists
			'files': [],
			'sha1s': [],
			'types': [],

			# All items below here are re-calculated in
			# init_browser_data()
			'directories': [],
			'directory_entries': {},

			# These are also parallel lists
			'item_names': [],
			'item_sha1s': [],
			'item_types': [],
			})
		

	def init_branch_data (self):
		remote_branches = cmds.git_branch (remote=True)
		local_branches = cmds.git_branch (remote=False)
		tags = cmds.git_tag()

		self.set_branch ('')
		self.set_revision ('')
		self.set_local_branches (local_branches)
		self.set_remote_branches (remote_branches)
		self.set_tags (tags)

	def init_browser_data (self):
		'''This scans over self.(files, sha1s, types) to generate
		directories, directory_entries, itmes, item_sha1s,
		and item_types.'''

		# Collect data for the model
		if not self.get_branch(): return

		self.item_names = []
		self.item_sha1s = []
		self.item_types = []
		self.directories = []
		self.directory_entries = {}

		# Lookup the tree info
		tree_info = cmds.git_ls_tree (self.get_branch())

		self.set_types (map ( lambda (x): x[1], tree_info ))
		self.set_sha1s (map ( lambda (x): x[2], tree_info ))
		self.set_files (map ( lambda (x): x[3], tree_info ))

		if self.directory: self.directories.append ('..')

		dir_entries = self.directory_entries
		dir_regex = re.compile ('([^/]+)/')
		dirs_seen = {}
		subdirs_seen = {}

		for idx, file in enumerate (self.files):

			orig_file = str (file)
			if not orig_file.startswith (self.directory): continue
			file = file[ len (self.directory): ]

			if file.count ('/'):
				# This is a directory...
				match = dir_regex.match (file)
				if not match: continue

				dirent = match.group (1) + '/'
				if dirent not in self.directory_entries:
					self.directory_entries[dirent] = []

				if dirent not in dirs_seen:
					dirs_seen[dirent] = True
					self.directories.append (dirent)

				entry = file.replace (dirent, '')
				entry_match = dir_regex.match (entry)
				if entry_match:
					subdir = entry_match.group (1) + '/'
					if subdir in subdirs_seen: continue
					subdirs_seen[subdir] = True
					dir_entries[dirent].append (subdir)
				else:
					dir_entries[dirent].append (entry)
			else:
				self.item_names.append (file)
				self.item_sha1s.append (self.sha1s[idx])
				self.item_types.append (self.types[idx])

	def add_signoff (self):
		'''Adds a standard Signed-off by: tag to the end
		of the current commit message.'''

		msg = self.get_commitmsg()
		signoff = ('Signed-off by: %s <%s>'
				% (self.get_name(), self.get_email()))

		if signoff not in msg:
			self.set_commitmsg (msg + '\n\n' + signoff)

	def set_latest_commitmsg (self):
		'''Queries git for the latest commit message and sets it in
		self.commitmsg.'''
		commit_msg = []
		commit_lines = cmds.git_show ('HEAD').split ('\n')
		for idx, msg in enumerate (commit_lines):
			if idx < 4: continue
			msg = msg.lstrip()
			if msg.startswith ('diff --git'):
				commit_msg.pop()
				break
			commit_msg.append (msg)
		self.set_commitmsg ('\n'.join (commit_msg).rstrip())
	
	def get_uncommitted_item (self, row):
		return (self.get_unstaged() + self.get_untracked())[row]
