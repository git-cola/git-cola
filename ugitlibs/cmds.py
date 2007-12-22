import os
import re
import commands
import utils
from cStringIO import StringIO

from PyQt4.QtCore import QProcess

# A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile('([0-9a-f]+)\W(.*)')

def quote(argv):
	return ' '.join([ utils.shell_quote(arg) for arg in argv ])

def run_cmd(cmd, *args, **kwargs):
	# Handle cmd as either a string or an argv list
	if type(cmd) is str:
		cmd = cmd.split(' ')
		cmd += list(args)
	else:
		cmd = list(cmd + list(args))

	child = QProcess()
	child.setProcessChannelMode(QProcess.MergedChannels);
	child.start(cmd[0], cmd[1:])

	if(not child.waitForStarted()):
		raise Exception, "failed to start child"

	if(not child.waitForFinished()):
		raise Exception, "failed to start child"

	output = str(child.readAll())

	# Allow run_cmd(argv, raw=True) for when we
	# want the full, raw output(e.g. git cat-file)
	if 'raw' in kwargs and kwargs['raw']:
		return output
	else:
		return output.rstrip()

def git_add(to_add):
	'''Invokes 'git add' to index the filenames in to_add.'''
	if not to_add: return 'ERROR: No files to add.'
	argv = [ 'git', 'add' ]
	argv.extend(to_add)
	return 'Running:\t' + quote(argv) + '\n' + run_cmd(argv)

def git_add_or_remove(to_process):
	'''Invokes 'git add' to index the filenames in to_process that exist
	and 'git rm' for those that do not exist.'''

	if not to_process:
		return 'ERROR: No files to add or remove.'

	to_add = []
	output = ''

	for filename in to_process:
		if os.path.exists(filename):
			to_add.append(filename)
	
	if to_add:
		output += git_add(to_add) + '\n\n'

	if len(to_add) == len(to_process):
		# to_process only contained unremoved files --
		# short-circuit the removal checks
		return output

	# Process files to add
	argv = [ 'git', 'rm' ]
	for filename in to_process:
		if not os.path.exists(filename):
			argv.append(filename)

	return '%sRunning:\t%s\n%s' %( output, quote(argv), run_cmd(argv) )

def git_apply(filename, indexonly=True):
	argv = ['git', 'apply']
	if indexonly:
		argv.extend(['--index', '--cached'])
	argv.append(filename)
	return run_cmd(argv)

def git_branch(name=None, remote=False, delete=False):
	argv = ['git', 'branch']
	if delete and name:
		return run_cmd(argv, '-D', name)
	else:
		if remote: argv.append('-r')

		branches = run_cmd(argv).splitlines()
		return map(lambda(x): x.lstrip('* '), branches)

def git_cat_file(objtype, sha1):
	cmd = 'git cat-file %s %s' %( objtype, sha1 )
	return run_cmd(cmd, raw=True)

def git_cherry_pick(revs, commit=False):
	'''Cherry-picks each revision into the current branch.'''
	if not revs:
		return 'ERROR: No revisions selected for cherry-picking.'

	argv = [ 'git', 'cherry-pick' ]
	if not commit: argv.append('-n')

	output = []
	for rev in revs:
		output.append('Cherry-picking: ' + rev)
		output.append(run_cmd(argv, rev))
		output.append('')
	return '\n'.join(output)

def git_checkout(rev):
	return run_cmd('git','checkout', rev)

def git_commit(msg, amend, files):
	'''Creates a git commit.  'commit_all' triggers the -a
	flag to 'git commit.'  'amend' triggers --amend.
	'files' is a list of files to use for commits without -a.'''

	# Sure, this is a potential "security risk," but if someone
	# is trying to intercept/re-write commit messages on your system,
	# then you probably have bigger problems to worry about.
	tmpfile = utils.get_tmp_filename()
	argv = [ 'git', 'commit', '-F', tmpfile ]

	if amend: argv.append('--amend')
	
	if not files:
		return 'ERROR: No files selected for commit.'

	argv.append('--')
	argv.extend(files)

	# Create the commit message file
	file = open(tmpfile, 'w')
	file.write(msg)
	file.close()
	
	# Run 'git commit'
	output = run_cmd(argv)
	os.unlink(tmpfile)

	return 'Running:\t' + quote(argv) + '\n\n' + output

def git_create_branch(name, base, track=False):
	'''Creates a branch starting from base.  Pass track=True
	to create a remote tracking branch.'''
	argv = ['git','branch']
	if track: argv.append('--track')
	return run_cmd(argv, name, base)


def git_current_branch():
	'''Parses 'git branch' to find the current branch.'''
	branches = run_cmd('git branch').splitlines()
	for branch in branches:
		if branch.startswith('* '):
			return branch.lstrip('* ')
	raise Exception, 'No current branch.  Detached HEAD?'

def git_diff(filename, staged=True, color=False, with_diff_header=False):
	'''Invokes git_diff on filename.  Passing staged=True adds
	diffs the index against HEAD(i.e. --cached).'''

	deleted = False
	argv = [ 'git', 'diff']
	if color:
		argv.append('--color')

	if staged:
		deleted = not os.path.exists(filename)
		argv.append('--cached')

	argv.append('--')
	argv.append(filename)

	diff = run_cmd(argv)
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
			headers.append(line)
	
	result = output.getvalue()
	output.close()

	if with_diff_header:
		return(os.linesep.join(headers), result)
	else:
		return result

def git_diff_stat():
	'''Returns the latest diffstat.'''
	return run_cmd('git diff --stat HEAD^')

def git_format_patch(revs, use_range):
	'''Exports patches revs in the 'ugit-patches' subdirectory.
	If use_range is True, a commit range is passed to git format-patch.'''

	argv = ['git','format-patch','--thread','--patch-with-stat',
		'-o','ugit-patches']
	if len(revs) > 1:
		argv.append('-n')

	header = 'Generated Patches:'
	if use_range:
		rev_range = '%s^..%s' %( revs[-1], revs[0] )
		return(header + '\n'
			+ run_cmd(argv, rev_range))

	output = [ header ]
	num_patches = 1
	for idx, rev in enumerate(revs):
		real_idx = str(idx + num_patches)
		output.append(
			run_cmd(argv, '-1', '--start-number', real_idx, rev))

		num_patches += output[-1].count('\n')

	return '\n'.join(output)

def git_config(key, value=None):
	'''Gets or sets git config values.  If value is not None, then
	the config key will be set.  Otherwise, the config value of the
	config key is returned.'''
	if value is not None:
		return run_cmd('git', 'config', key, value)
	else:
		return run_cmd('git', 'config', '--get', key)

def git_log(oneline=True, all=False):
	'''Returns a pair of parallel arrays listing the revision sha1's
	and commit summaries.'''
	argv = [ 'git', 'log' ]
	if oneline:
		argv.append('--pretty=oneline')
	if all:
		argv.append('--all')
	revs = []
	summaries = []
	regex = REV_LIST_REGEX
	output = run_cmd(argv)
	for line in output.splitlines():
		match = regex.match(line)
		if match:
			revs.append(match.group(1))
			summaries.append(match.group(2))
	return( revs, summaries )

def git_ls_files():
	return run_cmd('git ls-files').splitlines()

def git_ls_tree(rev):
	'''Returns a list of(mode, type, sha1, path) tuples.'''

	lines = run_cmd('git', 'ls-tree', '-r', rev).splitlines()
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

def git_rebase(newbase):
	if not newbase: return
	return run_cmd('git','rebase', newbase)

def git_reset(to_unstage):
	'''Use 'git reset' to unstage files from the index.'''

	if not to_unstage: return 'ERROR: No files to reset.'

	argv = [ 'git', 'reset', '--' ]
	argv.extend(to_unstage)

	return 'Running:\t' + quote(argv) + '\n' + run_cmd(argv)

def git_rev_list_range(start, end):

	argv = [ 'git', 'rev-list', '--pretty=oneline', start, end ]

	raw_revs = run_cmd(argv).splitlines()
	revs = []
	regex = REV_LIST_REGEX
	for line in raw_revs:
		match = regex.match(line)
		if match:
			rev_id = match.group(1)
			summary = match.group(2)
			revs.append((rev_id, summary,) )
	
	return revs

def git_show(sha1, color=False):
	cmd = 'git show '
	if color: cmd += '--color '
	return run_cmd(cmd + sha1)

def git_show_cdup():
	'''Returns a relative path to the git project root.'''
	return run_cmd('git rev-parse --show-cdup')

def git_status():
	'''RETURNS: A tuple of staged, unstaged and untracked files.
	( array(staged), array(unstaged), array(untracked) )'''

	status_lines = run_cmd('git status').splitlines()

	unstaged_header_seen = False
	untracked_header_seen = False

	modified_header = '# Changed but not updated:'
	modified_regex = re.compile('(#\tmodified:\W{3}'
			+ '|#\tnew file:\W{3}'
			+ '|#\tdeleted:\W{4})')

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

def git_tag():
	return run_cmd('git tag').splitlines()
