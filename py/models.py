import os
import re
import commands
from model import Model

def get_config(key):
	return commands.getoutput('git config --get "%s"' % key)

class GitModel(Model):
	def __init__ (self):
		Model.__init__ (self, {
				'commitmsg':	'',
				'staged':	[],
				'unstaged':	[],
				'untracked':	[],
				'name':		get_config('user.name'),
				'email':	get_config('user.email'),
				})

class GitRepoBrowserModel (Model):
	def __init__ (self, branch=''):
		Model.__init__ (self, {
				'directory':	'',
				'branch':	branch,

				# These are parallel lists
				'files':	[],
				'sha1s':	[],
				'types':	[],

				# All items below here are re-calculated in
				# setup_items()
				'directories':	[],
				'directory_entries':	{},

				# These are also parallel lists
				'item_names':	[],
				'item_sha1s':	[],
				'item_types':	[],
				})

	def setup_items (self):
		'''This scans over self.(files, sha1s, types) to generate
		directories, directory_entries, itmes, item_sha1s,
		and item_types.'''

		self.item_names = []
		self.item_sha1s = []
		self.item_types = []
		self.directories = []
		self.directory_entries = {}

		if self.directory: self.directories.append ('..')

		dir_entries = self.directory_entries
		dir_regex = re.compile ('([^/]+)/')
		dirs_seen = {}
		subdirs_seen = {}

		for idx, file in enumerate (self.files):

			orig_file = str (file)
			if not orig_file.startswith (self.directory): continue
			file = file[ len (self.directory): ]

			if file.count (os.sep):
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
