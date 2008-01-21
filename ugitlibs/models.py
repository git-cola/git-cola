import os
import re

import git
import utils
import model

class Model(model.Model):
	def __init__(self):
		model.Model.__init__(self)
		self.init_config_data()
		# chdir to the root of the git tree.
		# This keeps paths relative.
		cdup = git.show_cdup()
		if cdup: os.chdir(cdup)

		# These methods are best left implemented in git.py
		for cmd in (
				'add',
				'add_or_remove',
				'cat_file',
				'checkout',
				'create_branch',
				'cherry_pick',
				'commit',
				'diff',
				'diffstat',
				'diffindex',
				'format_patch',
				'push',
				'show',
				'log',
				'rebase',
				'remote_url',
				'rev_list_range',
				):
			setattr(self, cmd, getattr(git,cmd))

		self.create(
			#####################################################
			# Used in various places
			branch = git.current_branch(),
			remotes = git.remote(),
			remote = '',
			local_branch = '',
			remote_branch = '',
			search_text = '',
			git_version = git.git('--version'),

			#####################################################
			# Used primarily by the main UI
			project = os.path.basename(os.getcwd()),
			commitmsg = '',
			changed = [],
			staged = [],
			unstaged = [],
			untracked = [],
			window_geom = utils.parse_geom(
					self.get_global_ugit_geometry()),

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

	def init_config_data(self):
		self.__saved_params = [
			'user_name',
			'user_email',
			'merge_summary',
			'merge_diffstat',
			'merge_verbosity',
			'gui_diffcontext',
			'gui_pruneduringfetch',
			'ugit_geometry',
			'ugit_fontui',
			'ugit_fontdiff',
			'ugit_historybrowser',
		]
		self.__config_types = {}
		self.__config_defaults = {
			'user_name': '',
			'user_email': '',
			'merge_summary': False,
			'merge_diffstat': True,
			'merge_verbosity': 2,
			'gui_diffcontext': 5,
			'gui_pruneduringfetch': False,
			}
		self.__global_defaults = {
			'ugit_geometry':'',
			'ugit_fontui': '',
			'ugit_fontui_size':12,
			'ugit_fontdiff': '',
			'ugit_fontdiff_size':12,
			'ugit_historybrowser': 'gitk',
			}

		default_dict = self.__config_defaults
		if self.__config_types: return
		for k,v in default_dict.iteritems():
			if type(v) is int:
				self.__config_types[k] = 'int'
			elif type(v) is bool:
				self.__config_types[k] = 'bool'

		def config_to_dict(config):
			newdict = {}
			for line in config.splitlines():
				k, v = line.split('=')
				k = k.replace('.','_') # git -> model
				try:
					linetype = self.__config_types[k]
					if linetype == 'int':
						v = int(v)
					elif linetype == 'bool':
						v = bool(eval(v.title()))
				except: pass
				newdict[k]=v
			return newdict

		local_conf = git.git('config', '--list')
		global_conf = git.git('config', '--global', '--list')
		local_dict = config_to_dict(local_conf)
		global_dict = config_to_dict(global_conf)

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
		for k,v in default_dict.iteritems():
			if k not in local_dict:
				self.set_param('local_'+k, v)
			if k not in global_dict:
				self.set_param('global_'+k, v)

		for k,v in self.__global_defaults.iteritems():
			if k not in global_dict:
				self.set_param('global_'+k, v)

	def save_config_param(self,param):
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
		if param not in self.__saved_params:
			return
		param = param.replace('_','.') # model -> git
		git.config(param, value, local=is_local)

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

	def get_history_browser(self):
		return self.get_param('global_ugit_historybrowser')

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
		self.set_param('remote',remote)
		branches = utils.grep( '%s/\S+$' % remote,
				git.branch(remote=True), squash=False)
		self.set_remote_branches(branches)

	def add_signoff(self,*rest):
		'''Adds a standard Signed-off by: tag to the end
		of the current commit message.'''

		msg = self.get_commitmsg()
		signoff =('\n\nSigned-off by: %s <%s>\n' % (
				self.get_local_user_name(),
				self.get_local_user_email()))

		if signoff not in msg:
			self.set_commitmsg(msg + signoff)

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
		self.set_commitmsg(self.get_squash_msg())

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
		# hold both changed and untracked files.
		self.staged = []
		self.changed = []
		self.untracked = []

		# Read git status items
		( staged_items,
		  changed_items,
		  untracked_items ) = git.status()

		# Gather items to be committed
		for staged in staged_items:
			if staged not in self.get_staged():
				self.add_staged(staged)

		# Gather unindexed items
		for changed in changed_items:
			if changed not in self.get_changed():
				self.add_changed(changed)

		# Gather untracked items
		for untracked in untracked_items:
			if untracked not in self.get_untracked():
				self.add_untracked(untracked)

		self.set_branch(git.current_branch())
		self.set_unstaged(self.get_changed() + self.get_untracked())
		self.set_remotes(git.remote())
		self.set_remote_branches(git.branch(remote=True))
		self.set_local_branches(git.branch(remote=False))
		self.set_tags(git.tag())
		self.set_revision('')
		self.set_local_branch('')
		self.set_remote_branch('')
		# Re-enable notifications and emit changes
		self.set_notify(notify_enabled)
		self.notify_observers('staged','unstaged')

	def delete_branch(self, branch):
		return git.branch(name=branch, delete=True)

	def get_revision_sha1(self, idx):
		return self.get_revisions()[idx]

	def get_config_params(self):
		params = []
		params.extend(map(lambda x: 'local_' + x,
				self.__config_defaults.keys()))
		params.extend(map(lambda x: 'global_' + x,
				self.__config_defaults.keys()))
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
			return (commit + '\n\n'
				+ self.diff(commit=sha1, cached=False,
					suppress_header=False))
		else:
			return commit

	def get_diff_and_status(self, idx, staged=True):
		if staged:
			filename = self.get_staged()[idx]
			if os.path.exists(filename):
				status = 'Staged for commit'
			else:
				status = 'Staged for removal'
			diff = self.diff(filename=filename, cached=True)
		else:
			filename = self.get_unstaged()[idx]
			if os.path.isdir(filename):
				status = 'Untracked directory'
				diff = '\n'.join(os.listdir(filename))
			elif filename in self.get_changed():
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
		output = git.add(self.get_changed())
		self.update_status()
		return output

	def stage_untracked(self):
		output = git.add(self.get_untracked())
		self.update_status()
		return output

	def reset(self, items):
		output = git.reset(items)
		self.update_status()
		return output

	def unstage_all(self):
		git.reset(self.get_staged())
		self.update_status()

	def save_window_geom(self):
		git.config('ugit.geometry', utils.get_geom(), local=False)
