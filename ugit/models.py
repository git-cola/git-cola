import os
import sys
import re

from ugit import git
from ugit import utils
from ugit import model

class Model(model.Model):
	"""Provides a friendly wrapper for doing commit git operations."""

	def init(self):
		"""Reads git repository settings and sets severl methods
		so that they refer to the git module.  This object is
		encapsulates ugit's interaction with git.
		The git module itself should know nothing about ugit
		whatsoever."""

		# chdir to the root of the git tree.
		# This keeps paths relative.
		cdup = git.rev_parse(show_cdup=True)
		if cdup:
			if cdup.startswith('fatal:'):
				# this is not a git repo
				sys.stderr.write(cdup+"\n")
				sys.exit(-1)
			os.chdir(cdup)

		# Read git config
		self.init_config_data()

		# Import all git commands from git.py
		for name, cmd in git.commands.iteritems():
			setattr(self, name, cmd)

		self.create(
			#####################################################
			# Used in various places
			currentbranch = '',
			remotes = [],
			remote = '',
			local_branch = '',
			remote_branch = '',
			search_text = '',
			git_version = git.version(),

			#####################################################
			# Used primarily by the main UI
			project = os.path.basename(os.getcwd()),
			commitmsg = '',
			modified = [],
			staged = [],
			unstaged = [],
			untracked = [],
			window_geom = utils.parse_geom(
					self.get_global_ugit_geometry()),

			#####################################################
			# Used by the create branch dialog
			revision = '',
			local_branches = [],
			remote_branches = [],
			tags = [],

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


	def init_config_data(self):
		"""Reads git config --list and creates parameters
		for each setting."""
		# These parameters are saved in .gitconfig,
		# so ideally these should be as short as possible.

		# config items that are controllable globally
		# and per-repository
		self.__local_and_global_defaults = {
			'user_name': '',
			'user_email': '',
			'merge_summary': False,
			'merge_diffstat': True,
			'merge_verbosity': 2,
			'gui_diffcontext': 3,
			'gui_pruneduringfetch': False,
		}
		# config items that are purely git config --global settings
		self.__global_defaults = {
			'ugit_geometry':'',
			'ugit_fontui': '',
			'ugit_fontui_size':12,
			'ugit_fontdiff': '',
			'ugit_fontdiff_size':12,
			'ugit_historybrowser': 'gitk',
			'ugit_savewindowsettings': False,
			'ugit_saveatexit': False,
		}

		local_dict = git.config_dict(local=True)
		global_dict = git.config_dict(local=False)

		for k,v in local_dict.iteritems():
			self.set_param('local_'+k, v)
		for k,v in global_dict.iteritems():
			self.set_param('global_'+k, v)
			if k not in local_dict:
				local_dict[k]=v
				self.set_param('local_'+k, v)

		# Bootstrap the internal font*_size variables
		for param in ('global_ugit_fontui', 'global_ugit_fontdiff'):
			if hasattr(self, param):
				font = self.get_param(param)
				if font:
					size = int(font.split(',')[1])
					self.set_param(param+'_size', size)
					param = param[len('global_'):]
					global_dict[param] = font
					global_dict[param+'_size'] = size

		# Load defaults for all undefined items
		local_and_global_defaults = self.__local_and_global_defaults
		for k,v in local_and_global_defaults.iteritems():
			if k not in local_dict:
				self.set_param('local_'+k, v)
			if k not in global_dict:
				self.set_param('global_'+k, v)

		global_defaults = self.__global_defaults
		for k,v in global_defaults.iteritems():
			if k not in global_dict:
				self.set_param('global_'+k, v)

		# Load the diff context
		git.set_diff_context( self.local_gui_diffcontext )

	def save_config_param(self, param):
		if param not in self.get_config_params():
			return
		value = self.get_param(param)
		if param == 'local_gui_diffcontext':
			git.DIFF_CONTEXT = value
		if param.startswith('local_'):
			param = param[len('local_'):]
			is_local = True
		elif param.startswith('global_'):
			param = param[len('global_'):]
			is_local = False
		else:
			raise Exception("Invalid param '%s' passed to " % param
					+ "save_config_param()")
		param = param.replace('_','.') # model -> git
		return git.config_set(param, value, local=is_local)

	def init_browser_data(self):
		'''This scans over self.(names, sha1s, types) to generate
		directories, directory_entries, and subtree_*'''

		# Collect data for the model
		if not self.get_currentbranch(): return

		self.subtree_types = []
		self.subtree_sha1s = []
		self.subtree_names = []
		self.directories = []
		self.directory_entries = {}

		# Lookup the tree info
		tree_info = git.parse_ls_tree(self.get_currentbranch())

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

	def get_history_browser(self):
		return self.global_ugit_historybrowser

	def remember_gui_settings(self):
		return self.global_ugit_savewindowsettings

	def save_at_exit(self):
		return self.global_ugit_saveatexit

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

	def set_remote(self, remote):
		if not remote: return
		self.set_param('remote', remote)
		branches = utils.grep( '%s/\S+$' % remote,
				git.branch_list(remote=True), squash=False)
		self.set_remote_branches(branches)

	def add_signoff(self,*rest):
		'''Adds a standard Signed-off by: tag to the end
		of the current commit message.'''

		msg = self.get_commitmsg()
		signoff =('\n\nSigned-off-by: %s <%s>\n' % (
				self.get_local_user_name(),
				self.get_local_user_email()))

		if signoff not in msg:
			self.set_commitmsg(msg + signoff)

	def apply_diff(self, filename):
		return git.apply(filename, index=True, cached=True)

	def load_commitmsg(self, path):
		file = open(path, 'r')
		contents = file.read()
		file.close()
		self.set_commitmsg(contents)

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
		self.set_commitmsg('\n'.join(commit_msg).rstrip())

	def update_status(self):
		# This allows us to defer notification until the
		# we finish processing data
		notify_enabled = self.get_notify()
		self.set_notify(False)

		# Reset the staged and unstaged model lists
		# NOTE: the model's unstaged list is used to
		# hold both modified and untracked files.
		self.staged = []
		self.modified = []
		self.untracked = []

		# Read git status items
		( staged_items,
		  modified_items,
		  untracked_items ) = git.parse_status()

		# Gather items to be committed
		for staged in staged_items:
			if staged not in self.get_staged():
				self.add_staged(staged)

		# Gather unindexed items
		for modified in modified_items:
			if modified not in self.get_modified():
				self.add_modified(modified)

		# Gather untracked items
		for untracked in untracked_items:
			if untracked not in self.get_untracked():
				self.add_untracked(untracked)

		self.set_currentbranch(git.current_branch())
		self.set_unstaged(self.get_modified() + self.get_untracked())
		self.set_remotes(git.remote().splitlines())
		self.set_remote_branches(git.branch_list(remote=True))
		self.set_local_branches(git.branch_list(remote=False))
		self.set_tags(git.tag().splitlines())
		self.set_revision('')
		self.set_local_branch('')
		self.set_remote_branch('')
		# Re-enable notifications and emit changes
		self.set_notify(notify_enabled)
		self.notify_observers('staged','unstaged')

	def delete_branch(self, branch):
		return git.branch(branch, D=True)

	def get_revision_sha1(self, idx):
		return self.get_revisions()[idx]

	def get_config_params(self):
		params = []
		params.extend(map(lambda x: 'local_' + x,
				self.__local_and_global_defaults.keys()))
		params.extend(map(lambda x: 'global_' + x,
				self.__local_and_global_defaults.keys()))
		params.extend(map(lambda x: 'global_' + x,
				self.__global_defaults.keys()))
		return params

	def apply_font_size(self, param, default):
		old_font = self.get_param(param)
		if not old_font:
			old_font = default

		size = self.get_param(param+'_size')
		props = old_font.split(',')
		props[1] = str(size)
		new_font = ','.join(props)

		self.set_param(param, new_font)

	def read_font_size(self, param, new_font):
		new_size = int(new_font.split(',')[1])
		self.set_param(param, new_size)

	def get_commit_diff(self, sha1):
		commit = git.show(sha1)
		first_newline = commit.index('\n')
		if commit[first_newline+1:].startswith('Merge:'):
			return (commit
				+ '\n\n'
				+ self.diff_helper(
					commit=sha1,
					cached=False,
					suppress_header=False,
					)
				)
		else:
			return commit

	def get_diff_and_status(self, idx, staged=True):
		if staged:
			filename = self.get_staged()[idx]
			if os.path.exists(filename):
				status = 'Staged for commit'
			else:
				status = 'Staged for removal'
			diff = self.diff_helper(
					filename=filename,
					cached=True,
					)
		else:
			filename = self.get_unstaged()[idx]
			if os.path.isdir(filename):
				status = 'Untracked directory'
				diff = '\n'.join(os.listdir(filename))
			elif filename in self.get_modified():
				status = 'Modified, not staged'
				diff = self.diff_helper(
						filename=filename,
						cached=False,
						)
			else:
				status = 'Untracked, not staged'

				file_type = utils.run_cmd('file',filename, b=True)
				if 'binary' in file_type or 'data' in file_type:
					diff = utils.run_cmd('hexdump', filename, C=True)
				else:
					if os.path.exists(filename):
						file = open(filename, 'r')
						diff = file.read()
						file.close()
					else:
						diff = ''
		return diff, status

	def stage_modified(self):
		output = git.add(self.get_modified())
		self.update_status()
		return output

	def stage_untracked(self):
		output = git.add(self.get_untracked())
		self.update_status()
		return output

	def reset(self, *items):
		output = git.reset('--', *items)
		self.update_status()
		return output

	def unstage_all(self):
		git.reset('--', *self.get_staged())
		self.update_status()

	def save_gui_settings(self):
		git.config_set('ugit.geometry', utils.get_geom(), local=False)
