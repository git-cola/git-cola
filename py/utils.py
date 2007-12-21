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

class DiffParser (object):
	def __init__ (self, diff):
		self.__diff_header = re.compile ('@@\s.*\s@@$')

		self.__idx = -1
		self.__diffs = []
		self.__diff_offsets = []
		self.__diff_positions = []

		self.parse_diff (diff)
	
	def get_diffs (self):
		return self.__diffs
	
	def get_offsets (self):
		return self.__diff_offsets
	
	def get_positions (self):
		return self.__diff_positions

	def parse_diff (self, diff):
		last_idx = -1

		for idx, line in enumerate (diff.splitlines()):

			if self.__diff_header.match (line):
				self.__diffs.append ( [line] )
				self.__diff_offsets.append ([idx, idx])
				self.__diff_positions.append (len (line))
				self.__idx += 1
			else:
				# skip pre-diff output, if any
				if self.__idx == -1: continue
				self.__diffs[self.__idx].append (line)
				self.__diff_offsets[-1][-1] = idx
				self.__diff_positions[self.__idx] += len (line)

			last_idx = idx

		if self.__idx >= 0 and last_idx >= 0:
			self.__diff_offsets[-1][-1] = last_idx

		return self.__diffs
