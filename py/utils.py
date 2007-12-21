#!/usr/bin/env python
import os
import re
import time
import commands
from cStringIO import StringIO

KNOWN_FILE_TYPES = {
	'ascii c':   'c.png',
	'python':    'script.png',
	'ruby':      'script.png',
	'shell':     'script.png',
	'perl':      'script.png',
	'java':      'script.png',
	'assembler': 'binary.png',
	'binary':    'binary.png',
	'byte':      'binary.png',
	'image':     'image.png',
}

ICONSDIR = os.path.join (os.path.dirname (__file__), 'icons')

def ident_file_type (filename):
	'''Returns an icon based on the contents of filename.'''
	if os.path.exists (filename):
		quoted_filename = shell_quote (filename)
		fileinfo = commands.getoutput('file -b %s' % quoted_filename)
		for filetype, iconname in KNOWN_FILE_TYPES.iteritems():
			if filetype in fileinfo.lower():
				return iconname
	else:
		return 'removed.png'
	# Fallback for modified files of an unknown type
	return 'generic.png'

def get_icon (filename):
	'''Returns the full path to an icon file corresponding to
	filename's contents.'''
	icon_file = ident_file_type (filename)
	return os.path.join (ICONSDIR, icon_file)

def get_staged_icon (filename):
	'''Special-case method for staged items.  These are only
	ever 'staged' and 'removed' items in the staged list.'''

	if os.path.exists (filename):
		return os.path.join (ICONSDIR, 'staged.png')
	else:
		return os.path.join (ICONSDIR, 'removed.png')

def get_untracked_icon():
	return os.path.join (ICONSDIR, 'untracked.png')

def get_directory_icon():
	return os.path.join (ICONSDIR, 'dir.png')

def get_file_icon():
	return os.path.join (ICONSDIR, 'generic.png')

def shell_quote (*inputs):
	'''Quote strings so that they can be suitably martialled
	off to the shell.  This method supports POSIX sh syntax.
	This is crucial to properly handle command line arguments
	with spaces, quotes, double-quotes, etc.'''

	regex = re.compile ('[^\w!%+,\-./:@^]')
	quote_regex = re.compile ("((?:'\\''){2,})")

	ret = []
	for input in inputs:
		if not input:
			continue

		if '\x00' in input:
		    raise AssertionError, ('No way to quote strings '
				'containing null (\\000) bytes')

		# = does need quoting else in command position it's a
		# program-local environment setting
		match = regex.search (input)
		if match and '=' not in input:
			# ' -> '\''
			input = input.replace ("'", "'\\''")

			# make multiple ' in a row look simpler
			# '\'''\'''\'' -> '"'''"'
			quote_match = quote_regex.match (input)
			if quote_match:
				quotes = match.group (1)
				input.replace (quotes,
					("'" * (len(quotes)/4)) + "\"'")

			input = "'%s'" % input
			if input.startswith ("''"):
				input = input[2:]

			if input.endswith ("''"):
				input = input[:-2]
		ret.append (input)
	return ' '.join (ret)

def get_tmp_filename():
	# Allow TMPDIR/TMP with a fallback to /tmp
	return '.ugit.%s.%s' % ( os.getpid(), time.time() )

HEADER_LENGTH = 80
def header (msg):
	pad = HEADER_LENGTH - len (msg) - 4 # len (':+') + len ('+:')
	extra = pad % 2
	pad /= 2
	return (':+'
		+ (' ' * pad)
		+ msg
		+ (' ' * (pad + extra))
		+ '+:'
		+ '\n')
