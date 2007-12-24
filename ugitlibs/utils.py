#!/usr/bin/env python
import os
import re
import time
import commands
import defaults
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

ICONSDIR = os.path.join(os.path.dirname(__file__), 'icons')

def ident_file_type(filename):
	'''Returns an icon based on the contents of filename.'''
	if os.path.exists(filename):
		quoted_filename = shell_quote(filename)
		fileinfo = commands.getoutput('file -b %s' % quoted_filename)
		for filetype, iconname in KNOWN_FILE_TYPES.iteritems():
			if filetype in fileinfo.lower():
				return iconname
	else:
		return 'removed.png'
	# Fallback for modified files of an unknown type
	return 'generic.png'

def get_icon(filename):
	'''Returns the full path to an icon file corresponding to
	filename's contents.'''
	icon_file = ident_file_type(filename)
	return os.path.join(ICONSDIR, icon_file)

def get_staged_icon(filename):
	'''Special-case method for staged items.  These are only
	ever 'staged' and 'removed' items in the staged list.'''

	if os.path.exists(filename):
		return os.path.join(ICONSDIR, 'staged.png')
	else:
		return os.path.join(ICONSDIR, 'removed.png')

def get_untracked_icon():
	return os.path.join(ICONSDIR, 'untracked.png')

def get_directory_icon():
	return os.path.join(ICONSDIR, 'dir.png')

def get_file_icon():
	return os.path.join(ICONSDIR, 'generic.png')

def grep(pattern, items, indices=[1]):
	regex = re.compile(pattern)
	matched = []
	for item in items:
		match = regex.match(item)
		if not match: continue
		if len(indices) == 1:
			subitems = match.group(indices[0])
		else:
			subitems = []
			for idx in indices:
				subitems.append(match.group(idx))
		matched.append(subitems)
	if len(matched) == 1:
		return matched[0]
	else:
		return matched

def basename(path):
	'''Avoid os.path.basename because we are explicitly
	parsing git's output, which contains /'s regardless
	of platform (a.t.m.)
	'''
	base_regex = re.compile('(.*?/)?([^/]+)$')
	match = base_regex.match(path)
	if match:
		return match.group(2)
	else:
		return pathstr

def shell_quote(*inputs):
	'''Quote strings so that they can be suitably martialled
	off to the shell.  This method supports POSIX sh syntax.
	This is crucial to properly handle command line arguments
	with spaces, quotes, double-quotes, etc.'''

	regex = re.compile('[^\w!%+,\-./:@^]')
	quote_regex = re.compile("((?:'\\''){2,})")

	ret = []
	for input in inputs:
		if not input:
			continue

		if '\x00' in input:
		    raise AssertionError,('No way to quote strings '
				'containing null(\\000) bytes')

		# = does need quoting else in command position it's a
		# program-local environment setting
		match = regex.search(input)
		if match and '=' not in input:
			# ' -> '\''
			input = input.replace("'", "'\\''")

			# make multiple ' in a row look simpler
			# '\'''\'''\'' -> '"'''"'
			quote_match = quote_regex.match(input)
			if quote_match:
				quotes = match.group(1)
				input.replace(quotes,
					("'" *(len(quotes)/4)) + "\"'")

			input = "'%s'" % input
			if input.startswith("''"):
				input = input[2:]

			if input.endswith("''"):
				input = input[:-2]
		ret.append(input)
	return ' '.join(ret)

def get_tmp_filename():
	# Allow TMPDIR/TMP with a fallback to /tmp
	return '.ugit.%s.%s' %( os.getpid(), time.time() )

HEADER_LENGTH = 80
def header(msg):
	pad = HEADER_LENGTH - len(msg) - 4 # len(':+') + len('+:')
	extra = pad % 2
	pad /= 2
	return(':+'
		+(' ' * pad)
		+ msg
		+(' ' *(pad + extra))
		+ '+:'
		+ '\n')

def parse_geom(geomstr):
	regex = re.compile('^(\d+)x(\d+)\+(\d+),(\d+) (\d+),(\d+) (\d+),(\d+)')
	match = regex.match(geomstr)
	if match:
		defaults.WIDTH = int(match.group(1))
		defaults.HEIGHT = int(match.group(2))
		defaults.X = int(match.group(3))
		defaults.Y = int(match.group(4))
		defaults.SPLITTER_TOP_0 = int(match.group(5))
		defaults.SPLITTER_TOP_1 = int(match.group(6))
		defaults.SPLITTER_BOTTOM_0 = int(match.group(7))
		defaults.SPLITTER_BOTTOM_1 = int(match.group(8))

	return (defaults.WIDTH, defaults.HEIGHT,
		defaults.X, defaults.Y,
		defaults.SPLITTER_TOP_0, defaults.SPLITTER_TOP_1,
		defaults.SPLITTER_BOTTOM_0, defaults.SPLITTER_BOTTOM_1)

def get_geom():
	return '%dx%d+%d,%d %d,%d %d,%d' % (
		defaults.WIDTH, defaults.HEIGHT,
		defaults.X, defaults.Y,
		defaults.SPLITTER_TOP_0, defaults.SPLITTER_TOP_1,
		defaults.SPLITTER_BOTTOM_0, defaults.SPLITTER_BOTTOM_1)

def project_name():
	return os.path.basename(defaults.DIRECTORY)

def slurp(path):
	file = open(path)
	slushy = file.read()
	file.close()
	return slushy

def write(path, contents):
	file = open(path, 'w')
	file.write(contents)
	file.close()


class DiffParser(object):
	def __init__(self, diff):
		self.__diff_header = re.compile('^@@\s[^@]+\s@@.*')

		self.__idx = -1
		self.__diffs = []
		self.__diff_spans = []
		self.__diff_offsets = []

		self.parse_diff(diff)
	
	def get_diffs(self):
		return self.__diffs
	
	def get_spans(self):
		return self.__diff_spans
	
	def get_offsets(self):
		return self.__diff_offsets
	
	def get_diff_for_offset(self, offset):
		for idx, diff_offset in enumerate(self.__diff_offsets):
			if offset < diff_offset:
				return os.linesep.join(self.__diffs[idx])
		return None
	
	def get_diffs_for_range(self, start, end):
		diffs = []
		for idx, span in enumerate(self.__diff_spans):

			has_end_of_diff = start >= span[0] and start < span[1]
			has_all_of_diff = start <= span[0] and end >= span[1]
			has_head_of_diff = end >= span[0] and end <= span[1]

			selected_diff =(has_end_of_diff
					or has_all_of_diff
					or has_head_of_diff)

			if selected_diff:
				diff = os.linesep.join(self.__diffs[idx])
				diffs.append(diff)


		return diffs

	def parse_diff(self, diff):
		total_offset = 0
		for idx, line in enumerate(diff.splitlines()):

			if self.__diff_header.match(line):
				self.__diffs.append( [line] )

				line_len = len(line) + 1
				self.__diff_spans.append([total_offset,
						total_offset + line_len])

				total_offset += line_len
				self.__diff_offsets.append(total_offset)

				self.__idx += 1
			else:
				if self.__idx < 0:
					errmsg = 'Malformed diff?\n\n%s' % diff
					raise AssertionError, errmsg

				line_len = len(line) + 1
				total_offset += line_len

				self.__diffs[self.__idx].append(line)
				self.__diff_spans[-1][-1] += line_len
				self.__diff_offsets[self.__idx] += line_len

