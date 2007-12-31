import os
import re

import git
import utils
import model

class Model(model.Model):
	def __init__(self, init=True):
		model.Model.__init__(self)

		# These methods are best left implemented in git.py
		for attr in ('add', 'add_or_remove', 'cat_file', 'checkout',
					'create_branch', 'cherry_pick', 'commit', 'diff',
					'diff_stat', 'format_patch', 'push', 'show','log',
					'rebase', 'remote_url', 'rev_list_range'):
			setattr(self, attr, getattr(git,attr))

		# chdir to the root of the git tree.  This is critical
		# to being able to properly use the git porcelain.
		cdup = git.show_cdup()
		if cdup: os.chdir(cdup)
		if not init: return

		self.create(
			#####################################################
			# Used in various places
			branch = git.current_branch(),
			remotes = git.remote(),
			remote = '',
			local_branch = '',
			remote_branch = '',

			#####################################################
			# Used primarily by the main UI
			window_geom = utils.parse_geom(git.config('ugit.geometry')),
			project = os.path.basename(os.getcwd()),
			local_name = git.config('user.name'),
			local_email = git.config('user.email'),
			global_name = git.config('user.name', local=False),
			global_email = git.config('user.email', local=False),
			commitmsg = '',
			staged = [],
			unstaged = [],
			untracked = [],
			all_unstaged = [], # unstaged+untracked

			#####################################################
			# Used by the create branch dialog
			revision = '',
			local_branches = git.branch(remote=False),
			remote_branches = git.branch(remote=True),
			tags = git.tag(),

			#####################################################
			# Used by the commit/repo browser
			directory = '',
			revisions = [],
			summaries = [],

			# These are parallel lists
			types = [],
			sha1s = [],
			names = [],

			# All items below here are re-calculated in
			# init_browser_data()
			directories = [],
			directory_entries = {},

			# These are also parallel lists
			subtree_types = [],
			subtree_sha1s = [],
			subtree_names = [],
			)

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
		tree_info = git.ls_tree(self.get_branch())

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

	def get_all_branches(self):
		return (self.get_local_branches() + self.get_remote_branches())

	def set_remote(self,remote):
		if not remote: return
		self.set('remote',remote)
		branches = utils.grep( '%s/\S+$' % remote, git.branch(remote=True))
		self.set_remote_branches(branches)

	def add_signoff(self,*rest):
		'''Adds a standard Signed-off by: tag to the end
		of the current commit message.'''

		msg = self.get_commitmsg()
		signoff =('Signed-off by: %s <%s>'
			% (self.get_local_name(), self.get_local_email()))

		if signoff not in msg:
			self.set_commitmsg(msg + os.linesep*2 + signoff)

	def apply_diff(self, filename):
		return git.apply(filename)

	def __get_squash_msg_path(self):
		return os.path.join(os.getcwd(), '.git', 'SQUASH_MSG')

	def has_squash_msg(self):
		squash_msg = self.__get_squash_msg_path()
		return os.path.exists(squash_msg)

	def get_squash_msg(self):
		return utils.slurp(self.__get_squash_msg_path())

	def set_squash_msg(self):
		self.model.set_commitmsg(self.model.get_squash_msg())

	def get_prev_commitmsg(self,*rest):
		'''Queries git for the latest commit message and sets it in
		self.commitmsg.'''
		commit_msg = []
		commit_lines = git.show('HEAD').split('\n')
		for idx, msg in enumerate(commit_lines):
			if idx < 4: continue
			msg = msg.lstrip()
			if msg.startswith('diff --git'):
				commit_msg.pop()
				break
			commit_msg.append(msg)
		self.set_commitmsg(os.linesep.join(commit_msg).rstrip())

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
		  untracked_items ) = git.status()

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

		self.set_branch(git.current_branch())
		self.set_all_unstaged(self.get_unstaged() + self.get_untracked())
		self.set_remotes(git.remote())
		self.set_remote_branches(git.branch(remote=True))
		self.set_local_branches(git.branch(remote=False))
		self.set_tags(git.tag())
		self.set_revision('')
		self.set_local_branch('')
		self.set_remote_branch('')

		# Re-enable notifications and emit changes
		self.set_notify(notify_enabled)
		self.notify_observers(
				'branch', 'all_unstaged', 'staged',
				'revision', 'remote', 'remotes',
				'local_branches','remote_branches', 'tags')

	def delete_branch(self, branch):
		return git.branch(name=branch, delete=True)

	def get_revision_sha1(self, idx):
		return self.get_revisions()[idx]

	def get_commit_diff(self, sha1):
		commit = self.show(sha1)
		first_newline = commit.index(os.linesep)
		merge = commit[first_newline+1:].startswith('Merge:')
		if merge:
			return (commit + os.linesep*2
				+ self.diff(commit=sha1, cached=False,
					suppress_header=False))
		else:
			return commit

	def get_unstaged_item(self, idx):
		return self.get_all_unstaged()[idx]

	def get_diff_and_status(self, idx, staged=True):
		if staged:
			filename = self.get_staged()[idx]
			if os.path.exists(filename):
				status = 'Staged for commit'
			else:
				status = 'Staged for removal'
			diff = self.diff(filename=filename, cached=True)
		else:
			filename = self.get_all_unstaged()[idx]
			if os.path.isdir(filename):
				status = 'Untracked directory'
				diff = os.linesep.join(os.listdir(filename))
			elif filename in self.get_unstaged():
				status = 'Modified, not staged'
				diff = self.diff(filename=filename, cached=False)
			else:
				status = 'Untracked, not staged'

				file_type = utils.run_cmd('file','-b',filename)
				if 'binary' in file_type or 'data' in file_type:
					diff = utils.run_cmd('hexdump','-C',filename)
				else:
					if os.path.exists(filename):
						file = open(filename, 'r')
						diff = file.read()
						file.close()
					else:
						diff = ''
		return diff, status

	def stage_changed(self):
		git.add(self.get_unstaged())
		self.update_status()

	def stage_untracked(self):
		git.add(self.get_untracked())
		self.update_status()

	def reset(self, items):
		git.reset(items)
		self.update_status()

	def unstage_all(self):
		git.reset(self.get_staged())
		self.update_status()

	def save_window_geom(self):
		git.config('ugit.geometry', utils.get_geom())
