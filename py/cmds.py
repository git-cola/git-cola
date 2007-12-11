import os
import re
import time
import commands
import utils

def git_add (to_add):
	'''Invokes 'git add' to index the filenames in to_add.'''

	if not to_add: return 'ERROR: No files to add.'

	argv = [ 'git', 'add' ]
	for filename in to_add:
		argv.append (utils.shell_quote (filename))

	cmd = ' '.join (argv)
	return 'Running:\t%s\n%s\n%s added successfully' % (
			cmd, commands.getoutput (cmd), ', '.join (to_add) )

def git_add_or_remove (to_process):
	'''Invokes 'git add' to index the filenames in to_process that exist
	and 'git rm' for those that do not exist.'''

	if not to_process: return 'ERROR: No files to add or remove.'

	to_add = []
	output = ''

	for filename in to_process:
		if os.path.exists (filename):
			to_add.append (filename)
	
	if to_add:
		output += git_add (to_add) + '\n\n'

	if len(to_add) == len(to_process):
		# to_process only contained unremoved files --
		# short-circuit the removal checks
		return output

	# Process files to add
	argv = [ 'git', 'rm' ]
	for filename in to_process:
		if not os.path.exists (filename):
			argv.append (utils.shell_quote (filename))

	cmd = ' '.join (argv)
	return output + 'Running: %s\n%s' % ( cmd, commands.getoutput (cmd) )

def git_branch():
	'''Returns 'git branch''s output in a list.'''
	return commands.getoutput ('git branch').split ('\n')

def git_branch_list():
	return map (lambda (x): x.lstrip ('* '), git_branch())

def git_cat_file (objtype, sha1, target_file=None):
	cmd = 'git cat-file %s %s' % ( objtype, sha1 )
	if target_file:
		cmd += '> %s' % utils.shell_quote (target_file)
	return commands.getoutput (cmd)

def git_cherry_pick (revs, commit=False):
	'''Cherry-picks each revision into the current branch.'''
	if not revs:
		return 'ERROR: No revisions selected for cherry-picking.'''

	cmd = 'git cherry-pick '
	if not commit: cmd += '-n '
	output = []
	for rev in revs:
		output.append ('Cherry-picking: ' + rev)
		output.append (commands.getoutput (cmd + rev))
		output.append ('')
	return '\n'.join (output)

def git_commit (msg, amend, files):
	'''Creates a git commit.  'commit_all' triggers the -a
	flag to 'git commit.'  'amend' triggers --amend.
	'files' is a list of files to use for commits without -a.'''

	# Allow TMPDIR/TMP with a fallback to /tmp
	tmpdir = os.getenv ('TMPDIR', os.getenv ('TMP', '/tmp'))

	# Sure, this is a potential "security risk," but if someone
	# is trying to intercept/re-write commit messages on your system,
	# then you probably have bigger problems to worry about.
	tmpfile = os.path.join (tmpdir,
			'ugit.%s.%s' % ( os.getuid(), time.time() ))

	argv = [ 'git', 'commit', '-F', tmpfile ]

	if amend: argv.append ('--amend')
	
	if not files:
		return 'ERROR: No files selected for commit.'

	argv.append ('--')
	for file in files:
		argv.append (utils.shell_quote (file))

	# Create the commit message file
	file = open (tmpfile, 'w')
	file.write (msg)
	file.close()
	
	# Run 'git commit'
	cmd = ' '.join (argv)
	output = commands.getoutput (cmd)
	os.unlink (tmpfile)

	return 'Running:\t%s\n%s' % (cmd, output)

def git_current_branch():
	'''Parses 'git branch' to find the current branch.'''
	for branch in git_branch():
		if branch.startswith ('* '):
			return branch.lstrip ('* ')
	raise Exception, 'No current branch.  Detached HEAD?'

def git_diff (filename, staged=True):
	'''Invokes git_diff on filename.  Passing staged=True adds
	diffs the index against HEAD (i.e. --cached).'''

	deleted = False
	argv = [ 'git', 'diff', '--color']
	if staged:
		deleted = not os.path.exists (filename)
		argv.append ('--cached')

	argv.append ('--')
	argv.append (utils.shell_quote (filename))

	diff = commands.getoutput (' '.join (argv))
	diff_lines = diff.split ('\n')

	output = []
	start = False
	del_tag = 'deleted file mode '

	for line in diff_lines:
		if not start and '@@ ' in line and ' @@' in line:
			start = True
		if start or (deleted and del_tag in line):
			output.append (line)
	return '\n'.join (output)

def git_diff_stat ():
	'''Returns the latest diffstat.'''
	return commands.getoutput ('git diff --color --stat HEAD^')

def git_format_patch (revs, use_range):
	'''Exports patches revs in the 'ugit-patches' subdirectory.
	If use_range is True, a commit range is passed to git format-patch.'''

	cmd = 'git format-patch --thread --patch-with-stat -o ugit-patches '
	header = 'Generated Patches:'
	if len (revs) > 1:
		cmd += '-n '

	if use_range:
		rev_range = '%s^..%s' % ( revs[-1], revs[0] )
		return header + '\n' + commands.getoutput (cmd + rev_range)

	output = [ header ]
	num_patches = 1
	for idx, rev in enumerate (revs):
		real_idx = idx + num_patches
		revcmd = cmd + '-1 --start-number %d %s' % (real_idx, rev)
		output.append (commands.getoutput (revcmd))
		num_patches += output[-1].count ('\n')
	return '\n'.join (output)

def git_log (oneline=True, all=False):
	'''Returns a pair of parallel arrays listing the revision sha1's
	and commit summaries.'''
	argv = [ 'git', 'log' ]
	if oneline: argv.append ('--pretty=oneline')
	if all: argv.append ('--all')
	revs = []
	summaries = []
	regex = re.compile ('(\w+)\W(.*)')
	output = commands.getoutput (' '.join (argv))
	for line in output.split ('\n'):
		match = regex.match (line)
		if match:
			revs.append (match.group (1))
			summaries.append (match.group (2))
	return ( revs, summaries )

def git_ls_tree (rev):
	'''Returns a list of (mode, type, sha1, path) tuples.'''
	regex = re.compile ('^(\d+)\W(\w+)\W(\w+)[ \t]+(.*)$')
	sh_rev = utils.shell_quote (rev)
	lines = commands.getoutput ('git ls-tree -r ' + sh_rev).split ('\n')
	output = []
	for line in lines:
		match = regex.match (line)
		if match:
			mode = match.group (1)
			objtype = match.group (2)
			sha1 = match.group (3)
			filename = match.group (4)
			output.append ( (mode, objtype, sha1, filename,) )
	return output

def git_reset (to_unstage):
	'''Use 'git reset' to unstage files from the index.'''

	if not to_unstage: return 'ERROR: No files to reset.'

	argv = [ 'git', 'reset', '--' ]
	for filename in to_unstage:
		argv.append (utils.shell_quote (filename))

	cmd = ' '.join (argv)
	return 'Running:\t%s\n%s' % ( cmd, commands.getoutput (cmd) )

def git_show (sha1, color=False):
	cmd = 'git show '
	if color: cmd += '--color '
	return commands.getoutput (cmd + sha1)

def git_show_cdup():
	'''Returns a relative path to the git project root.'''
	return commands.getoutput ('git rev-parse --show-cdup')

def git_status():
	'''RETURNS: A tuple of staged, unstaged and untracked files.
	( array(staged), array(unstaged), array(untracked) )'''

	status_lines = commands.getoutput ('git status').split ('\n')

	unstaged_header_seen = False
	untracked_header_seen = False

	modified_header = '# Changed but not updated:'
	modified_regex = re.compile ('(#\tmodified:\W{3}'
			+ '|#\tnew file:\W{3}'
			+ '|#\tdeleted:\W{4})')

	renamed_regex = re.compile ('(#\trenamed:\W{4})(.*?)\W->\W(.*)')

	untracked_header = '# Untracked files:'
	untracked_regex = re.compile ('#\t(.+)')

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
		match = untracked_regex.match (status_line)
		if match:
			filename = match.group (1)
			untracked.append (filename)

	# Staged, unstaged, and renamed files
	for status_line in status_lines:
		if modified_header in status_line:
			unstaged_header_seen = True
			continue
		match = modified_regex.match (status_line)
		if match:
			tag = match.group (0)
			filename = status_line.replace (tag, '')
			if unstaged_header_seen:
				unstaged.append (filename)
			else:
				staged.append (filename)
			continue
		# Renamed files
		match = renamed_regex.match (status_line)
		if match:
			oldname = match.group (2)
			newname = match.group (3)
			staged.append (oldname)
			staged.append (newname)

	return ( staged, unstaged, untracked )
