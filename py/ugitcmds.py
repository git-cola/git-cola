from commands import getoutput
import re

def git_branch ():
	return getoutput('git branch').split ('\n')

def git_current_branch ():
	for branch in git_branch():
		if branch.startswith ('* '):
			return branch.lstrip ('* ')
	raise Exception, 'No current branch'

def git_status ():
	return getoutput('git status').split ('\n')

def git_modified (status_lines = None, staged=True):
	if status_lines is None:
		status_lines = git_status().split ('\n')

	modified_header_seen = staged
	modified_header = '# Changed but not updated:'

	modified_regex = re.compile('(#\tmodified:|#\tnew file:)')
	modified = []
	for status_line in status_lines:
		if modified_header in status_line:
			modified_header_seen = not staged
			continue
		if not modified_header_seen:
			continue

		match = modified_regex.match (status_line)
		if match:
			tag = match.group (0)
			filename = status_line.replace (tag, '')
			modified.append (filename.lstrip())
	return modified

def git_untracked (status_lines):
	untracked_header_seen = False
	untracked_header = '# Untracked files:'
	untracked_regex = re.compile ('#\t(.+)')

	untracked = []

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
	return untracked


def git_show_cdup ():
	return getoutput('git rev-parse --show-cdup')

def git_reset (to_unstage):
	output_lines = []
	for filename in to_unstage:
		cmd = 'git reset -- "%s"' % filename
		output = getoutput (cmd)

		output_lines.append ('Running: ' + cmd)
		output_lines.append (output)
		output_lines.append ('')
	return "\n".join (output_lines)

def git_add (to_add):
	output_lines = []
	for filename in to_add:
		cmd = 'git add "%s"' % filename
		output = getoutput (cmd)

		output_lines.append ('Running: ' + cmd)
		if output:
			output_lines.append (output)
		else:
			msg = '%s added successfully' % filename
			output_lines.append (msg)
		output_lines.append ('')
	return "\n".join (output_lines)
