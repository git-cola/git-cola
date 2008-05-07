import subprocess
import os
import re
import sys
import time
import types
from cStringIO import StringIO
DIFF_CONTEXT = 3

def set_diff_context(ctxt):
	global DIFF_CONTEXT
	DIFF_CONTEXT = ctxt

def get_tmp_filename():
	# Allow TMPDIR/TMP with a fallback to /tmp
	env = os.environ
	return os.path.join(env.get('TMP', env.get('TMPDIR', '/tmp')),
		'.git.%s.%s' % ( os.getpid(), time.time()))

def run_cmd(cmd, *args, **kwargs):
	"""
	Returns an array of strings from the command's output.

	DEFAULTS:
		raw=False

	Passing raw=True prevents the output from being striped.

		with_status = False
	
	Passing with_status=True returns tuple(status,output)
	instead of just the command's output.

	run_command("git foo", bar, buzz,
		baz=value, bar=True, q=True, f='foo')

	Implies:
		argv = ["git", "foo",
			"-q", "-ffoo",
			"--bar", "--baz=value",
			"bar","buzz" ]
	"""

	def pop_key(d, key):
		val = d.get(key)
		try: del d[key]
		except: pass
		return val
	raw = pop_key(kwargs, 'raw')
	with_status = pop_key(kwargs,'with_status')
	with_stderr = not pop_key(kwargs,'without_stderr')
	cwd = os.getcwd()

	kwarglist = []
	for k,v in kwargs.iteritems():
		if len(k) > 1:
			k = k.replace('_','-')
			if v is True:
				kwarglist.append("--%s" % k)
			elif v is not None and type(v) is not bool:
				kwarglist.append("--%s=%s" % (k,v))
		else:
			if v is True:
				kwarglist.append("-%s" % k)
			elif v is not None and type(v) is not bool:
				kwarglist.append("-%s" % k)
				kwarglist.append(str(v))
	# Handle cmd as either a string or an argv list
	if type(cmd) is str:
		# we only call run_cmd(str) with str='git command'
		# or other simple commands
		cmd = cmd.split(' ')
		cmd += kwarglist
		cmd += tuple(args)
	else:
		cmd = tuple(cmd + kwarglist + list(args))

	stderr = None
	if with_stderr:
		stderr = subprocess.STDOUT
	# start the process
	proc = subprocess.Popen(cmd, cwd=cwd,
			stdout=subprocess.PIPE,
			stderr=stderr,
			stdin=None)
	# Wait for the process to return
	output, err = proc.communicate()
	# conveniently strip off trailing newlines
	if not raw:
		output = output.rstrip()
	if err:
		raise RuntimeError("%s return exit status %d"
				% ( str(cmd), err ))
	if with_status:
		return (err, output)
	else:
		return output

# union of functions in this file and dynamic functions
# defined in the git command string list below
def git(*args,**kwargs):
	"""This is a convenience wrapper around run_cmd that
	sets things up so that commands are run in the canonical
	'git command [options] [args]' form."""
	cmd = 'git %s' % args[0]
	return run_cmd(cmd, *args[1:], **kwargs)

class GitCommand(object):
	"""This class wraps this module so that arbitrary git commands
	can be dynamically called at runtime."""
	def __init__(self, module):
		self.module = module
		self.commands = {}
		# This creates git.foo() methods dynamically for each of the
		# following names at import-time.
		for cmd in """
			add
			apply
			branch
			checkout
			cherry_pick
			commit
			diff
			fetch
			format_patch
			grep
			log
			ls_tree
			merge
			pull
			push
			rebase
			remote
			reset
			read_tree
			rev_list
			rm
			show
			status
			tag
		""".split(): getattr(self, cmd)

	def setup_commands(self):
		# Import the functions from the module
		for name, val in self.module.__dict__.iteritems():
			if type(val) is types.FunctionType:
				setattr(self, name, val)
		# Import dynamic functions and those from the module
		# functions into self.commands
		for name, val in self.__dict__.iteritems():
			if type(val) is types.FunctionType:
				self.commands[name] = val

	def __getattr__(self, cmd):
		if hasattr(self.module, cmd):
			value = getattr(self.module, cmd)
			setattr(self, cmd, value)
			return value
		def git_cmd(*args, **kwargs):
			"""Runs "git <cmd> [options] [args]"
			The output is returned as a string.
			Pass with_stauts=True to merge stderr's into stdout.
			Pass raw=True to avoid stripping git's output.
			Finally, pass with_status=True to
			return a (status, output) tuple."""
			return git(cmd.replace('_','-'), *args, **kwargs)
		setattr(self, cmd, git_cmd)
		return git_cmd

# core git wrapper for use in this module
gitcmd = GitCommand(sys.modules[__name__])
sys.modules[__name__] = gitcmd

#+-------------------------------------------------------------------------
#+ A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile('([0-9a-f]+)\W(.*)')

def abort_merge():
	# Reset the worktree
	output = gitcmd.read_tree("HEAD", reset=True, u=True, v=True)
	# remove MERGE_HEAD
	merge_head = git_repo_path('MERGE_HEAD')
	if os.path.exists(merge_head):
		os.unlink(merge_head)
	# remove MERGE_MESSAGE, etc.
	merge_msg_path = get_merge_message_path()
	while merge_msg_path is not None:
		os.unlink(merge_msg_path)
		merge_msg_path = get_merge_message_path()

def add_or_remove(*to_process):
	"""Invokes 'git add' to index the filenames in to_process that exist
	and 'git rm' for those that do not exist."""

	if not to_process:
		return 'No files to add or remove.'

	to_add = []
	to_remove = []

	for filename in to_process:
		if os.path.exists(filename):
			to_add.append(filename)

	output = gitcmd.add(verbose=True, *to_add)

	if len(to_add) == len(to_process):
		# to_process only contained unremoved files --
		# short-circuit the removal checks
		return output

	# Process files to remote
	for filename in to_process:
		if not os.path.exists(filename):
			to_remove.append(filename)
	output + '\n\n' + gitcmd.rm(*to_remove)

def branch_list(remote=False):
	branches = map(lambda x: x.lstrip('* '),
			gitcmd.branch(r=remote).splitlines())
	if remote:
		remotes = []
		for branch in branches:
			if branch.endswith('/HEAD'):
				continue
			remotes.append(branch)
		return remotes
	return branches

def cherry_pick_list(revs, **kwargs):
	"""Cherry-picks each revision into the current branch.
	Returns a list of command output strings (1 per cherry pick)"""
	if not revs:
		return []
	cherries = []
	for rev in revs:
		cherries.append(gitcmd.cherry_pick(rev, **kwargs))
	return '\n'.join(cherries)

def commit_with_msg(msg, amend=False):
	"""Creates a git commit."""

	if not msg.endswith('\n'):
		msg += '\n'
	# Sure, this is a potential "security risk," but if someone
	# is trying to intercept/re-write commit messages on your system,
	# then you probably have bigger problems to worry about.
	tmpfile = get_tmp_filename()
	kwargs = {
		'F': tmpfile,
		'amend': amend,
	}
	# Create the commit message file
	file = open(tmpfile, 'w')
	file.write(msg)
	file.close()

	# Run 'git commit'
	output = gitcmd.commit(F=tmpfile, amend=amend)
	os.unlink(tmpfile)

	return ('git commit -F %s --amend %s\n\n%s'
		% ( tmpfile, amend, output ))

def create_branch(name, base, track=False):
	"""Creates a branch starting from base.  Pass track=True
	to create a remote tracking branch."""
	return gitcmd.branch(name, base, track=track)

def current_branch():
	"""Parses 'git branch' to find the current branch."""

	branches = gitcmd.branch().splitlines()
	for branch in branches:
		if branch.startswith('* '):
			return branch.lstrip('* ')
	return 'Detached HEAD'

def diff_helper(commit=None,
		filename=None,
		color=False,
		cached=True,
		with_diff_header=False,
		suppress_header=True,
		reverse=False):
	"Invokes git diff on a filepath."

	argv = []
	if commit:
		argv.append('%s^..%s' % (commit, commit))

	if filename:
		argv.append('--')
		if type(filename) is list:
			argv.extend(filename)
		else:
			argv.append(filename)

	diff = gitcmd.diff(
			R=reverse,
			color=color,
			cached=cached,
			patch_with_raw=True,
			unified=DIFF_CONTEXT,
			*argv
		).splitlines()

	output = StringIO()
	start = False
	del_tag = 'deleted file mode '

	headers = []
	deleted = cached and not os.path.exists(filename)
	for line in diff:
		if not start and '@@ ' in line and ' @@' in line:
			start = True
		if start or(deleted and del_tag in line):
			output.write(line + '\n')
		else:
			if with_diff_header:
				headers.append(line)
			elif not suppress_header:
				output.write(line + '\n')
	result = output.getvalue()
	output.close()
	if with_diff_header:
		return('\n'.join(headers), result)
	else:
		return result

def diffstat():
	return gitcmd.diff(
			'HEAD^',
			unified=DIFF_CONTEXT,
			stat=True)

def diffindex():
	return gitcmd.diff(
			unified=DIFF_CONTEXT,
			stat=True,
			cached=True)

def format_patch_helper(*revs):
	"""writes patches named by revs to the "patches" directory."""
	num_patches = 1
	output = []
	for idx, rev in enumerate(revs):
		real_idx = idx + num_patches
		revarg = '%s^..%s' % (rev,rev)
		output.append(
			gitcmd.format_patch(
				revarg,
				o='patches',
				start_number=real_idx,
				n=len(revs) > 1,
				thread=True,
				patch_with_stat=True
				)
			)
		num_patches += output[-1].count('\n')
	return '\n'.join(output)

def get_merge_message():
	return gitcmd.fmt_merge_msg('--file', git_repo_path('FETCH_HEAD'))

def config_dict(local=True):
	if local:
		argv = [ '--list' ]
	else:
		argv = ['--global', '--list' ]
	return config_to_dict(
		gitcmd.config(*argv).splitlines())

def config_set(key=None, value=None, local=True):
	if key and value is not None:
		# git config category.key value
		strval = str(value)
		if type(value) is bool:
			# git uses "true" and "false"
			strval = strval.lower()
		if local:
			argv = [ key, strval ]
		else:
			argv = [ '--global', key, strval ]
		return gitcmd.config(*argv)
	else:
		msg = "oops in git.config_set(key=%s,value=%s,local=%s"
		raise Exception(msg % (key, value, local))

def config_to_dict(config_lines):
	"""parses the lines from git config --list into a dictionary"""

	newdict = {}
	for line in config_lines:
		k, v = line.split('=', 1)
		k = k.replace('.','_') # git -> model
		if v == 'true' or v == 'false':
			v = bool(eval(v.title()))
		try:
			v = int(eval(v))
		except:
			pass
		newdict[k]=v
	return newdict

def log_helper(all=False):
	"""Returns a pair of parallel arrays listing the revision sha1's
	and commit summaries."""
	revs = []
	summaries = []
	regex = REV_LIST_REGEX
	output = gitcmd.log(pretty='oneline', all=all)
	for line in output.splitlines():
		match = regex.match(line)
		if match:
			revs.append(match.group(1))
			summaries.append(match.group(2))
	return( revs, summaries )

def parse_ls_tree(rev):
	"""Returns a list of(mode, type, sha1, path) tuples."""
	lines = gitcmd.ls_tree(rev, r=True).splitlines()
	output = []
	regex = re.compile('^(\d+)\W(\w+)\W(\w+)[ \t]+(.*)$')
	for line in lines:
		match = regex.match(line)
		if match:
			mode = match.group(1)
			objtype = match.group(2)
			sha1 = match.group(3)
			filename = match.group(4)
			output.append((mode, objtype, sha1, filename,) )
	return output

def push_helper(remote, local_branch, remote_branch, ffwd=True, tags=False):
	if ffwd:
		branch_arg = '%s:%s' % ( local_branch, remote_branch )
	else:
		branch_arg = '+%s:%s' % ( local_branch, remote_branch )
	return gitcmd.push(remote, branch_arg, with_status=True, tags=tags)

def remote_url(name):
	return gitcmd.config('remote.%s.url' % name, get=True)

def rev_list_range(start, end):
	range = '%s..%s' % ( start, end )
	raw_revs = gitcmd.rev_list(range, pretty='oneline')
	return parse_rev_list(raw_revs)

def git_repo_path(*subpaths):
	paths = [ gitcmd.rev_parse(git_dir=True) ]
	paths.extend(subpaths)
	return os.path.realpath(os.path.join(*paths))

def get_merge_message_path():
	for file in ('MERGE_MSG', 'SQUASH_MSG'):
		path = git_repo_path(file)
		if os.path.exists(path):
			return path
	return None

def reset_helper(*args, **kwargs):
	return gitcmd.reset('--', *args, **kwargs)

def parse_rev_list(raw_revs):
	revs = []
	for line in raw_revs.splitlines():
		match = REV_LIST_REGEX.match(line)
		if match:
			rev_id = match.group(1)
			summary = match.group(2)
			revs.append((rev_id, summary,) )
	return revs

def parse_status():
	"""RETURNS: A tuple of staged, unstaged and untracked file lists."""

	def eval_path(path):
		"""handles quoted paths."""
		if path.startswith('"') and path.endswith('"'):
			return eval(path)
		else:
			return path

	MODIFIED_TAG = '# Changed but not updated:'
	UNTRACKED_TAG = '# Untracked files:'

	RGX_RENAMED = re.compile(
				'(#\trenamed:\s+)'
				'(.*?)\s->\s(.*)'
				)

	RGX_MODIFIED = re.compile(
				'(#\tmodified:\s+'
				'|#\tnew file:\s+'
				'|#\tdeleted:\s+)'
				)
	staged = []
	unstaged = []
	untracked = []

	STAGED_MODE = 0
	UNSTAGED_MODE = 1
	UNTRACKED_MODE = 2

	mode = STAGED_MODE
	current_dest = staged

	for status_line in gitcmd.status().splitlines():
		if status_line == MODIFIED_TAG:
			mode = UNSTAGED_MODE
			current_dest = unstaged
			continue

		elif status_line == UNTRACKED_TAG:
			mode = UNTRACKED_MODE
			current_dest = untracked
			continue

		# Staged/unstaged modified/renamed/deleted files
		if mode == STAGED_MODE or mode == UNSTAGED_MODE:
			match = RGX_MODIFIED.match(status_line)
			if match:
				tag = match.group(0)
				filename = status_line.replace(tag, '')
				current_dest.append(eval_path(filename))
				continue
			match = RGX_RENAMED.match(status_line)
			if match:
				oldname = match.group(2)
				newname = match.group(3)
				current_dest.append(eval_path(oldname))
				current_dest.append(eval_path(newname))
				continue
		# Untracked files
		elif mode is UNTRACKED_MODE:
			if status_line.startswith('#\t'):
				current_dest.append(eval_path(status_line[2:]))

	return( staged, unstaged, untracked )

# Must be executed after all functions are defined
gitcmd.setup_commands()
