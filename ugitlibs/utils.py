#!/usr/bin/env python
import sys
import os
import re
import time
from cStringIO import StringIO

from PyQt4.QtCore import QProcess

import defaults

PREFIX = os.path.realpath(os.path.dirname(os.path.dirname(sys.argv[0])))
QMDIR = os.path.join(PREFIX, 'share', 'ugit', 'qm')

def get_qm_for_locale(locale):
	regex = re.compile(r'([^\.])+\..*$')
	match = regex.match(locale)
	if match:
		locale = match.group(1)

	basename = locale.split('_')[0]

	return os.path.join(QMDIR, basename +'.qm')


ICONSDIR = os.path.join(PREFIX, 'share', 'ugit', 'icons')
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

def ident_file_type(filename):
	'''Returns an icon based on the contents of filename.'''
	if os.path.exists(filename):
		fileinfo = run_cmd('file','-b',filename)
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

def run_cmd(cmd, *args, **kwargs):
	# Handle cmd as either a string or an argv list
	if type(cmd) is str:
		cmd = cmd.split(' ')
		cmd += list(args)
	else:
		cmd = list(cmd + list(args))

	child = QProcess()

	if 'stderr' not in kwargs:
		child.setProcessChannelMode(QProcess.MergedChannels);

	child.start(cmd[0], cmd[1:])

	if not child.waitForStarted(): return ''
	if not child.waitForFinished(): return ''

	output = str(child.readAll())

	# run_cmd(argv, raw=True) if we want the full, raw output
	if 'raw' in kwargs:
		return output
	else:
		if 'with_status' in kwargs:
			return child.exitCode(), output.rstrip()
		else:
			return output.rstrip()

def fork(*argv):
	pid = os.fork()
	if pid: return
	os.execlp(*argv)

# c = a - b
def sublist(a,b):
	c = []
	for item in a:
		if item not in b:
			c.append(item)
	return c

__grep_cache = {}
def grep(pattern, items, squash=True):
	isdict = type(items) is dict
	if pattern in __grep_cache:
		regex = __grep_cache[pattern]
	else:
		regex = __grep_cache[pattern] = re.compile(pattern)
	matched = []
	matchdict = {}
	for item in items:
		match = regex.match(item)
		if not match: continue
		groups = match.groups()
		if not groups:
			subitems = match.group(0)
		else:
			if len(groups) == 1:
				subitems = groups[0]
			else:
				subitems = list(groups)
		if isdict:
			matchdict[item] = items[item]
		else:
			matched.append(subitems)

	if isdict:
		return matchdict
	else:
		if squash and len(matched) == 1:
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
	def __init__(self, model,
				filename='', cached=True):
		self.__header_pattern = re.compile('^@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*')
		self.__headers = []

		self.__idx = -1
		self.__diffs = []
		self.__diff_spans = []
		self.__diff_offsets = []

		self.start = None
		self.end = None
		self.offset = None
		self.diffs = []
		self.selected = []

		(header, diff) = \
			model.diff(filename=filename, with_diff_header=True,
				cached=cached, reverse=cached)

		self.model = model
		self.diff = diff
		self.header = header
		self.parse_diff(diff)

		# Always index into the non-reversed diff
		self.fwd_header, self.fwd_diff = \
			model.diff(filename=filename, with_diff_header=True,
					cached=cached, reverse=False)

	def write_diff(self,filename,which,selected=False,noop=False):
		if not noop and which < len(self.diffs):
			diff = self.diffs[which]
			write(filename, self.header + os.linesep + diff + os.linesep)
			return True
		else:
			return False

	def get_diffs(self):
		return self.__diffs

	def get_diff_subset(self, diff, start, end):
		newdiff = []
		diffguts = os.linesep.join(self.__diffs[diff])

		offset = self.__diff_spans[diff][0]

		local_offset = 0

		adds = 0
		deletes = 0

		for line in self.__diffs[diff]:

			line_start = offset + local_offset
			local_offset += len(line) + 1
			line_end = offset + local_offset

			# |line1 |line2 |line3|
			#   |selection----|
			#   '-start   '-end

			# selection has head of diff (line3)
			if start < line_start and end > line_start and end < line_end:
				newdiff.append(line)
				if line.startswith('+'):
					adds += 1
				if line.startswith('-'):
					deletes += 1
			# selection has all of diff (line2)
			elif start <= line_start and end >= line_end:
				newdiff.append(line)
				if line.startswith('+'):
					adds += 1
				if line.startswith('-'):
					deletes += 1
			# selection has tail of diff (line1)
			elif start >= line_start and start < line_end - 1:
				newdiff.append(line)
				if line.startswith('+'):
					adds += 1
				if line.startswith('-'):
					deletes += 1
			else:
				# Don't add new lines unless selected
				if line.startswith('+'):
					continue
				elif line.startswith('-'):
					# Don't remove lines unless selected
					newdiff.append(' ' + line[1:])
				else:
					newdiff.append(line)

		new_count = self.__headers[diff][1] + adds - deletes

		if new_count != self.__headers[diff][3]:
			header = '@@ -%d,%d +%d,%d @@' % (
							self.__headers[diff][0],
							self.__headers[diff][1],
							self.__headers[diff][2],
							new_count)
			newdiff[0] = header

		return (self.header
				+ os.linesep
				+ os.linesep.join(newdiff)
				+ os.linesep)
	
	def get_spans(self):
		return self.__diff_spans
	
	def get_offsets(self):
		return self.__diff_offsets
	
	def set_diff_to_offset(self, offset):
		self.offset = offset
		self.diffs, self.selected = self.get_diff_for_offset(offset)

	def set_diffs_to_range(self, start, end):
		self.start = start
		self.end = end
		self.diffs, self.selected = self.get_diffs_for_range(start,end)

	def get_diff_for_offset(self, offset):
		for idx, diff_offset in enumerate(self.__diff_offsets):
			if offset < diff_offset:
				return ([os.linesep.join(self.__diffs[idx])],
						[idx])
		return ([],[])
	
	def get_diffs_for_range(self, start, end):
		diffs = []
		indices = []
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
				indices.append(idx)
		return diffs, indices

	def parse_diff(self, diff):
		total_offset = 0
		self.__idx = -1
		self.__headers = []

		for idx, line in enumerate(diff.splitlines()):

			match = self.__header_pattern.match(line)
			if match:
				self.__headers.append([
						int(match.group(1)),
						int(match.group(2)),
						int(match.group(3)),
						int(match.group(4))
						])

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

	def process_diff_selection(self, selected, offset, selection):
		if selection:
			start = self.fwd_diff.index(selection)
			end = start + len(selection)
			self.set_diffs_to_range(start, end)
		else:
			self.set_diff_to_offset(offset)
			selected = False

		# Process diff selection only
		if selected:
			for idx in self.selected:
				contents = self.get_diff_subset(idx, start, end)
				if contents:
					tmpfile = get_tmp_filename()
					write(tmpfile, contents)
					self.model.apply_diff(tmpfile)
					os.unlink(tmpfile)
		# Process a complete hunk
		else:
			for idx, diff in enumerate(self.diffs):
				tmpfile = get_tmp_filename()
				if self.write_diff(tmpfile,idx):
					self.model.apply_diff(tmpfile)
					os.unlink(tmpfile)
