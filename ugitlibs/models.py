import os
import re
import commands
import cmds
import utils
from model import Model

class GitModel(Model):
	def __init__(self):

		# chdir to the root of the git tree.  This is critical
		# to being able to properly use the git porcelain.
		cdup = cmds.git_show_cdup()
		if cdup: os.chdir(cdup)

		Model.__init__(self, {
			#####################################################
			# Used in various places
			'remotes': cmds.git_remote(),
			'remote': '',
			'local_branch': '',
			'remote_branch': '',

			#####################################################
			# Used primarily by the main UI
			'project': os.path.basename(os.getcwd()),
			'name': cmds.git_config('user.name'),
			'email': cmds.git_config('user.email'),
			'commitmsg': '',
			'staged': [],
			'unstaged': [],
			'untracked': [],
			'all_unstaged': [], # unstaged+untracked

			#####################################################
			# Used by the create branch dialog
			'revision': '',
			'local_branches': cmds.git_branch(remote=False),
			'remote_branches': cmds.git_branch(remote=True),
			'tags': cmds.git_tag(),

			#####################################################
			# Used by the repo browser
			'directory': '',

			# These are parallel lists
			'types': [],
			'sha1s': [],
			'names': [],

			# All items below here are re-calculated in
			# init_browser_data()
			'directories': [],
			'directory_entries': {},

			# These are also parallel lists
			'subtree_types': [],
			'subtree_sha1s': [],
			'subtree_names': [],
			})
		

	def all_branches(self):
		return (self.get_local_branches()
			+ self.get_remote_branches())

	def init_branch_data(self):
		remotes = cmds.git_remote()
		remote_branches = cmds.git_branch(remote=True)
		local_branches = cmds.git_branch(remote=False)
		tags = cmds.git_tag()

		self.set_remotes(remotes)
		self.set_remote_branches(remote_branches)
		self.set_local_branches(local_branches)
		self.set_tags(tags)
		self.set_revision('')
		self.set_local_branch('')
		self.set_remote_branch('')

	def set_remote(self,remote):
		if not remote: return
		self.set('remote',remote)
		branches = utils.grep('%s/\S+$' % remote,
				cmds.git_branch(remote=True))
		self.set_remote_branches(branches)

	def init_browser_data(self):
		'''This scans over self.(names, sha1s, types) to generate
		directories, directory_entries, and subtree_*'''

		# Collect data for the model
		if not self.get_branch(): return

		self.subtree_types = []
		self.subtree_sha1s = []
		self.subtree_names = []
		self.directories = []
		self.directory_entries = {}

		# Lookup the tree info
		tree_info = cmds.git_ls_tree(self.get_branch())

		self.set_types(map( lambda(x): x[1], tree_info ))
		self.set_sha1s(map( lambda(x): x[2], tree_info ))
		self.set_names(map( lambda(x): x[3], tree_info ))

		if self.directory: self.directories.append('..')

		dir_entries = self.directory_entries
		dir_regex = re.compile('([^/]+)/')
		dirs_seen = {}
		subdirs_seen = {}

		for idx, name in enumerate(self.names):

			if not name.startswith(self.directory): continue
			name = name[ len(self.directory): ]

			if name.count('/'):
				# This is a directory...
				match = dir_regex.match(name)
				if not match: continue

				dirent = match.group(1) + '/'
				if dirent not in self.directory_entries:
					self.directory_entries[dirent] = []

				if dirent not in dirs_seen:
					dirs_seen[dirent] = True
					self.directories.append(dirent)

				entry = name.replace(dirent, '')
				entry_match = dir_regex.match(entry)
				if entry_match:
					subdir = entry_match.group(1) + '/'
					if subdir in subdirs_seen: continue
					subdirs_seen[subdir] = True
					dir_entries[dirent].append(subdir)
				else:
					dir_entries[dirent].append(entry)
			else:
				self.subtree_types.append(self.types[idx])
				self.subtree_sha1s.append(self.sha1s[idx])
				self.subtree_names.append(name)
	
	def get_tree_node(self, idx):
		return (self.get_types()[idx],
			self.get_sha1s()[idx],
			self.get_names()[idx] )

	def get_subtree_node(self, idx):
		return (self.get_subtree_types()[idx],
			self.get_subtree_sha1s()[idx],
			self.get_subtree_names()[idx] )

	def add_signoff(self,*rest):
		'''Adds a standard Signed-off by: tag to the end
		of the current commit message.'''

		msg = self.get_commitmsg()
		signoff =('Signed-off by: %s <%s>'
				%(self.get_name(), self.get_email()))

		if signoff not in msg:
			self.set_commitmsg(msg + '\n\n' + signoff)

	def apply_diff(self, filename):
		return cmds.git_apply(filename)

	def get_uncommitted_item(self, row):
		return(self.get_unstaged() + self.get_untracked())[row]
	
	def __get_squash_msg_path(self):
		return os.path.join(os.getcwd(), '.git', 'SQUASH_MSG')

	def has_squash_msg(self):
		squash_msg = self.__get_squash_msg_path()
		return os.path.exists(squash_msg)

	def get_squash_msg(self):
		return utils.slurp(self.__get_squash_msg_path())

	def get_prev_commitmsg(self,*rest):
		'''Queries git for the latest commit message and sets it in
		self.commitmsg.'''
		commit_msg = []
		commit_lines = cmds.git_show('HEAD').split('\n')
		for idx, msg in enumerate(commit_lines):
			if idx < 4: continue
			msg = msg.lstrip()
			if msg.startswith('diff --git'):
				commit_msg.pop()
				break
			commit_msg.append(msg)
		self.set_commitmsg('\n'.join(commit_msg).rstrip())

	def update_status(self):
		# This allows us to defer notification until the
		# we finish processing data
		notify_enabled = self.get_notify()
		self.set_notify(False)

		# Reset the staged and unstaged model lists
		# NOTE: the model's unstaged list is used to
		# hold both unstaged and untracked files.
		self.staged = []
		self.unstaged = []
		self.untracked = []

		# Read git status items
		( staged_items,
		  unstaged_items,
		  untracked_items ) = cmds.git_status()

		# Gather items to be committed
		for staged in staged_items:
			if staged not in self.get_staged():
				self.add_staged(staged)

		# Gather unindexed items
		for unstaged in unstaged_items:
			if unstaged not in self.get_unstaged():
				self.add_unstaged(unstaged)

		# Gather untracked items
		for untracked in untracked_items:
			if untracked not in self.get_untracked():
				self.add_untracked(untracked)

		# Provide a convenient representation of the unstaged list
		self.set_all_unstaged(self.get_unstaged() + self.get_untracked())

		# Re-enable notifications and emit changes
		self.set_notify(notify_enabled)
		self.notify_observers('all_unstaged', 'staged')
