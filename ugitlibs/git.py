'''TODO: "import stgit"'''
import os
import re
import types
import utils
import defaults
from cStringIO import StringIO

# A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile('([0-9a-f]+)\W(.*)')

def quote(argv):
	return ' '.join([ utils.shell_quote(arg) for arg in argv ])

def git(*args,**kwargs):
	return utils.run_cmd('git', *args, **kwargs)

def add(to_add):
	'''Invokes 'git add' to index the filenames in to_add.'''
	if not to_add: return 'No files to add.'
	return git('add', '-v', *to_add)

def add_or_remove(to_process):
	'''Invokes 'git add' to index the filenames in to_process that exist
	and 'git rm' for those that do not exist.'''

	if not to_process:
		return 'No files to add or remove.'

	to_add = []
	to_remove = []

	for filename in to_process:
		if os.path.exists(filename):
			to_add.append(filename)

	output = add(to_add)

	if len(to_add) == len(to_process):
		# to_process only contained unremoved files --
		# short-circuit the removal checks
		return output

	# Process files to remote
	for filename in to_process:
		if not os.path.exists(filename):
			to_remove.append(filename)
	output + '\n\n' + git('rm',*to_remove)

def apply(filename, indexonly=True, reverse=False):
	argv = ['apply']
	if reverse: argv.append('--reverse')
	if indexonly: argv.extend(['--index', '--cached'])
	argv.append(filename)
	return git(*argv)

def branch(name=None, remote=False, delete=False):
	if delete and name:
		return git('branch', '-D', name)
	else:
		argv = ['branch']
		if remote: argv.append('-r')
		branches = map(lambda x: x.lstrip('* '),
				git(*argv).splitlines())
		if remote:
			remotes = []
			for branch in branches:
				if branch.endswith('/HEAD'): continue
				remotes.append(branch)
			return remotes
		return branches

def cat_file(objtype, sha1):
	return git('cat-file', objtype, sha1, raw=True)

def cherry_pick(revs, commit=False):
	'''Cherry-picks each revision into the current branch.'''
	if not revs:
		return 'No revision selected.'
	argv = [ 'cherry-pick' ]
	if not commit: argv.append('-n')

	cherries = []
	for rev in revs:
		new_argv = argv + [rev]
		cherries.append(git(*new_argv))

	return '\n'.join(cherries)

def checkout(rev):
	return git('checkout', rev)

def commit(msg, amend=False):
	'''Creates a git commit.'''

	if not msg.endswith('\n'):
		msg += '\n'

	# Sure, this is a potential "security risk," but if someone
	# is trying to intercept/re-write commit messages on your system,
	# then you probably have bigger problems to worry about.
	tmpfile = utils.get_tmp_filename()
	argv = [ 'commit', '-F', tmpfile ]
	if amend:
		argv.append('--amend')

	# Create the commit message file
	file = open(tmpfile, 'w')
	file.write(msg)
	file.close()

	# Run 'git commit'
	output = git(*argv)
	os.unlink(tmpfile)

	return 'git ' + quote(argv) + '\n\n' + output

def create_branch(name, base, track=False):
	'''Creates a branch starting from base.  Pass track=True
	to create a remote tracking branch.'''
	if track: return git('branch', '--track', name, base)
	else: return git('branch', name, base)

def current_branch():
	'''Parses 'git branch' to find the current branch.'''
	branches = git('branch').splitlines()
	for branch in branches:
		if branch.startswith('* '):
			return branch.lstrip('* ')
	return 'Detached HEAD'

def diff(commit=None,filename=None, color=False,
		cached=True, with_diff_header=False,
		suppress_header=True, reverse=False):
	"Invokes git diff on a filepath."

	argv = [ 'diff', '--unified='+str(defaults.DIFF_CONTEXT), '--patch-with-raw']
	if reverse: argv.append('-R')
	if color: argv.append('--color')
	if cached: argv.append('--cached')

	deleted = cached and not os.path.exists(filename)

	if filename:
		argv.append('--')
		argv.append(filename)

	if commit:
		argv.append('%s^..%s' % (commit,commit))

	diff = git(*argv)
	diff_lines = diff.splitlines()

	output = StringIO()
	start = False
	del_tag = 'deleted file mode '

	headers = []
	for line in diff_lines:
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
	return git('diff','--unified='+str(defaults.DIFF_CONTEXT),
			'--stat', 'HEAD^')
def diffindex():
	return git('diff', '--unified='+str(defaults.DIFF_CONTEXT),
			'--stat', '--cached')

def format_patch(revs):
	'''writes patches named by revs to the "patches" directory.'''
	num_patches = 1
	output = []
	argv = ['format-patch','--thread','--patch-with-stat', '-o','patches']
	if len(revs) > 1:
		argv.append('-n')
	for idx, rev in enumerate(revs):
		real_idx = str(idx + num_patches)
		new_argv = argv + ['--start-number', real_idx,
				'%s^..%s'%(rev,rev)]
		output.append(git(*new_argv))
		num_patches += output[-1].count('\n')
	return '\n'.join(output)

def config(key, value=None, local=True):
	argv = ['config']
	if not local:
		argv.append('--global')
	if value is None:
		argv.append('--get')
		argv.append(key)
	else:
		argv.append(key)
		if type(value) is bool:
			value = str(value).lower()
		argv.append(str(value))
	return git(*argv)

def log(oneline=True, all=False):
	'''Returns a pair of parallel arrays listing the revision sha1's
	and commit summaries.'''
	argv = [ 'log' ]
	if oneline:
		argv.append('--pretty=oneline')
	if all:
		argv.append('--all')
	revs = []
	summaries = []
	regex = REV_LIST_REGEX
	output = git(*argv)
	for line in output.splitlines():
		match = regex.match(line)
		if match:
			revs.append(match.group(1))
			summaries.append(match.group(2))
	return( revs, summaries )

def ls_files():
	return git('ls-files').splitlines()

def ls_tree(rev):
	'''Returns a list of(mode, type, sha1, path) tuples.'''
	lines = git('ls-tree', '-r', rev).splitlines()
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

def push(remote, local_branch, remote_branch, ffwd=True, tags=False):
	argv = ['push']
	if tags:
		argv.append('--tags')
	argv.append(remote)
	if local_branch == remote_branch:
		argv.append(local_branch)
	else:
		if not ffwd and local_branch:
			argv.append('+%s:%s' % ( local_branch, remote_branch ))
		else:
			argv.append('%s:%s' % ( local_branch, remote_branch ))
	return git(with_status=True, *argv)

def rebase(newbase):
	if not newbase: return 'No base branch specified to rebase.'
	return git('rebase', newbase)

def remote(*args):
	return git('remote', stderr=False, *args).splitlines()

def remote_url(name):
	return config('remote.%s.url' % name)

def reset(to_unstage):
	'''Use 'git reset' to unstage files from the index.'''
	if not to_unstage:
		return 'No files to reset.'

	argv = [ 'reset', '--' ]
	argv.extend(to_unstage)
	return git(*argv)

def rev_list_range(start, end):
	argv = [ 'rev-list', '--pretty=oneline', start, end ]
	raw_revs = git(*argv).splitlines()
	revs = []
	for line in raw_revs:
		match = REV_LIST_REGEX.match(line)
		if match:
			rev_id = match.group(1)
			summary = match.group(2)
			revs.append((rev_id, summary,) )
	return revs

def show(sha1):
	return git('show',sha1)

def show_cdup():
	'''Returns a relative path to the git project root.'''
	return git('rev-parse','--show-cdup')

def status():
	'''RETURNS: A tuple of staged, unstaged and untracked files.
	( array(staged), array(unstaged), array(untracked) )'''

	status_lines = git('status').splitlines()

	unstaged_header_seen = False
	untracked_header_seen = False

	modified_header = '# Changed but not updated:'
	modified_regex = re.compile('(#\tmodified:\W{3}'
			'|#\tnew file:\W{1}'
			'|#\tdeleted:\W{4})')

	renamed_regex = re.compile('(#\trenamed:\W{4})(.*?)\W->\W(.*)')

	untracked_header = '# Untracked files:'
	untracked_regex = re.compile('#\t(.+)')

	staged = []
	unstaged = []
	untracked = []

	# Untracked files
	for status_line in status_lines:
		if untracked_header in status_line:
			untracked_header_seen = True
			continue
		if not untracked_header_seen:
			continue
		match = untracked_regex.match(status_line)
		if match:
			filename = match.group(1)
			untracked.append(filename)

	# Staged, unstaged, and renamed files
	for status_line in status_lines:
		if modified_header in status_line:
			unstaged_header_seen = True
			continue
		match = modified_regex.match(status_line)
		if match:
			tag = match.group(0)
			filename = status_line.replace(tag, '')
			if unstaged_header_seen:
				unstaged.append(filename)
			else:
				staged.append(filename)
			continue
		# Renamed files
		match = renamed_regex.match(status_line)
		if match:
			oldname = match.group(2)
			newname = match.group(3)
			staged.append(oldname)
			staged.append(newname)

	return( staged, unstaged, untracked )

def tag():
	return git('tag').splitlines()
