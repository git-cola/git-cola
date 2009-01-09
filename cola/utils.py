#!/usr/bin/env python
# Copyright (c) 2008 David Aguilar
"""This module provides miscellaneous utility functions."""

import os
import re
import sys
import platform
import subprocess
import mimetypes

from glob import glob
from cStringIO import StringIO

from cola import git
from cola.git import shell_quote
from cola.core import encode, decode
from cola.exception import ColaException

PREFIX = os.path.realpath(os.path.dirname(os.path.dirname(sys.argv[0])))
QMDIR = os.path.join(PREFIX, 'share', 'cola', 'qm')
ICONSDIR = os.path.join(PREFIX, 'share', 'cola', 'icons')
STYLEDIR = os.path.join(PREFIX, 'share', 'cola', 'styles')
DOCDIR = os.path.join(PREFIX, 'share', 'doc', 'cola')

KNOWN_FILE_MIME_TYPES = {
    'text':      'script.png',
    'image':     'image.png',
    'python':    'script.png',
    'ruby':      'script.png',
    'shell':     'script.png',
    'perl':      'script.png',
    'octet':     'binary.png',
}

KNOWN_FILE_EXTENSION = {
    '.java':    'script.png',
    '.groovy':  'script.png',
    '.cpp':     'script.png',
    '.c':       'script.png',
    '.h':       'script.png',
    '.cxx':     'script.png',
}

def run_cmd(*command):
    """
    Runs a *command argument list and returns the output.
    e.g. run_cmd("echo", "hello", "world")
    """
    return git.Git.execute(command)

def get_qm_for_locale(locale):
    """Returns the .qm file for a particular $LANG values."""
    regex = re.compile(r'([^\.])+\..*$')
    match = regex.match(locale)
    if match:
        locale = match.group(1)

    basename = locale.split('_')[0]

    return os.path.join(QMDIR, basename +'.qm')

def get_resource_dirs(styledir):
    """Returns all directories underneath the share/cola/styles directory."""
    return [ r for r in glob(styledir+ '/*') if os.path.isdir(r) ]

def get_stylesheet(name):
    """Returns the path to a stylesheet within the cola install tree."""
    stylesheet = os.path.join(STYLEDIR, name+'.qss')
    if os.path.exists(stylesheet):
        return stylesheet
    else:
        return None

def get_style_dir():
    """Returns the path to the style dir within the cola install tree."""
    return STYLEDIR

def get_htmldocs():
    """Returns the path to the cola html documentation."""
    return os.path.join(DOCDIR, 'git-cola.html')

def ident_file_type(filename):
    """Returns an icon based on the contents of filename."""
    if os.path.exists(filename):
        filemimetype = mimetypes.guess_type(filename)
        if filemimetype[0] != None:
            for filetype, iconname in KNOWN_FILE_MIME_TYPES.iteritems():
                if filetype in filemimetype[0].lower():
                    return iconname
        filename = filename.lower()
        for fileext, iconname in KNOWN_FILE_EXTENSION.iteritems():
            if filename.endswith(fileext):
                return iconname
        return 'generic.png'
    else:
        return 'removed.png'
    # Fallback for modified files of an unknown type
    return 'generic.png'

def get_file_icon(filename):
    """
    Returns the full path to an icon file corresponding to
    filename"s contents.
    """
    icon_file = ident_file_type(filename)
    return get_icon(icon_file)

def get_icon(icon_file):
    """Returns the full path to an icon file given a basename."""
    return os.path.join(ICONSDIR, icon_file)

def fork(*args):
    """Launches a command in the background."""
    args = tuple([ encode(a) for a in args ])
    if os.name in ('nt', 'dos'):
        for path in os.environ['PATH'].split(os.pathsep):
            filename = os.path.join(path, args[0]) + ".exe"
            if os.path.exists(filename):
                try:
                    return os.spawnv(os.P_NOWAIT, filename, args)
                except os.error:
                    pass
        raise IOError('cannot find executable: %s' % args[0])
    else:
        argv = map(shell_quote, args)
        return os.system(' '.join(argv) + '&')

def sublist(a,b):
    """Subtracts list b from list a and returns the resulting list."""
    # conceptually, c = a - b
    c = []
    for item in a:
        if item not in b:
            c.append(item)
    return c

__grep_cache = {}
def grep(pattern, items, squash=True):
    """Greps a list for items that match a pattern and return a list of
    matching items.  If only one item matches, return just that item.
    """
    isdict = type(items) is dict
    if pattern in __grep_cache:
        regex = __grep_cache[pattern]
    else:
        regex = __grep_cache[pattern] = re.compile(pattern)
    matched = []
    matchdict = {}
    for item in items:
        match = regex.match(item)
        if not match:
            continue
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
    """Avoid os.path.basename because we are explicitly
    parsing git"s output, which contains /"s regardless
    of platform (a.t.m.)
    """
    base_regex = re.compile('(.*?/)?([^/]+)$')
    match = base_regex.match(path)
    if match:
        return match.group(2)
    else:
        return pathstr


def slurp(path):
    """Slurps a filepath into a string."""
    file = open(path)
    slushy = file.read()
    file.close()
    return decode(slushy)

def write(path, contents):
    """Writes a string to a file."""
    file = open(path, 'w')
    file.write(encode(contents))
    file.close()

class DiffParser(object):
    """Handles parsing diff for use by the interactive index editor."""
    def __init__(self, model, filename='',
                 cached=True, branch=None, reverse=False):

        self.__header_re = re.compile('^@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*')
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

        (header, diff) = model.diff_helper(filename=filename,
                                           branch=branch,
                                           with_diff_header=True,
                                           cached=cached and not bool(branch),
                                           reverse=cached or bool(branch) or reverse)
        self.model = model
        self.diff = diff
        self.header = header
        self.parse_diff(diff)

        # Always index into the non-reversed diff
        self.fwd_header, self.fwd_diff = \
            model.diff_helper(filename=filename,
                              branch=branch,
                              with_diff_header=True,
                              cached=cached and not bool(branch),
                              reverse=bool(branch))

    def write_diff(self,filename,which,selected=False,noop=False):
        """Writes a new diff corresponding to the user's selection."""
        if not noop and which < len(self.diffs):
            diff = self.diffs[which]
            write(filename, self.header + '\n' + diff + '\n')
            return True
        else:
            return False

    def get_diffs(self):
        """Returns the list of diffs."""
        return self.__diffs

    def get_diff_subset(self, diff, start, end):
        """Processes the diffs and returns a selected subset from that diff.
        """
        adds = 0
        deletes = 0
        newdiff = []
        local_offset = 0
        offset = self.__diff_spans[diff][0]
        diffguts = '\n'.join(self.__diffs[diff])

        for line in self.__diffs[diff]:
            line_start = offset + local_offset
            local_offset += len(line) + 1 #\n
            line_end = offset + local_offset
            # |line1 |line2 |line3 |
            #   |--selection--|
            #   '-start       '-end
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

        return (self.header + '\n' + '\n'.join(newdiff) + '\n')

    def get_spans(self):
        """Returns the line spans of each hunk."""
        return self.__diff_spans

    def get_offsets(self):
        """Returns the offsets."""
        return self.__diff_offsets

    def set_diff_to_offset(self, offset):
        """Sets the diff selection to be the hunk at a particular offset."""
        self.offset = offset
        self.diffs, self.selected = self.get_diff_for_offset(offset)

    def set_diffs_to_range(self, start, end):
        """Sets the diff selection to be a range of hunks."""
        self.start = start
        self.end = end
        self.diffs, self.selected = self.get_diffs_for_range(start,end)

    def get_diff_for_offset(self, offset):
        """Returns the hunks for a particular offset."""
        for idx, diff_offset in enumerate(self.__diff_offsets):
            if offset < diff_offset:
                return (['\n'.join(self.__diffs[idx])], [idx])
        return ([],[])

    def get_diffs_for_range(self, start, end):
        """Returns the hunks for a selected range."""
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
                diff = '\n'.join(self.__diffs[idx])
                diffs.append(diff)
                indices.append(idx)
        return diffs, indices

    def parse_diff(self, diff):
        """Parses a diff and extracts headers, offsets, hunks, etc.
        """
        total_offset = 0
        self.__idx = -1
        self.__headers = []

        for idx, line in enumerate(diff.split('\n')):
            match = self.__header_re.match(line)
            if match:
                self.__headers.append([
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                        int(match.group(4))
                        ])
                self.__diffs.append( [line] )

                line_len = len(line) + 1 #\n
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

    def process_diff_selection(self, selected, offset, selection,
                               apply_to_worktree=False):
        """Processes a diff selection and applies changes to the work tree
        or index."""
        if selection:
            # qt destroys \r\n and makes it \n with no way of going back.
            # boo!  we work around that here
            if selection not in self.fwd_diff:
                special_selection = selection.replace('\n', '\r\n')
                if special_selection in self.fwd_diff:
                    selection = special_selection
                else:
                    return
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
                    tmpfile = self.model.get_tmp_filename()
                    write(tmpfile, contents)
                    if apply_to_worktree:
                        self.model.apply_diff_to_worktree(tmpfile)
                    else:
                        self.model.apply_diff(tmpfile)
                    os.unlink(tmpfile)
        # Process a complete hunk
        else:
            for idx, diff in enumerate(self.diffs):
                tmpfile = self.model.get_tmp_filename()
                if self.write_diff(tmpfile,idx):
                    if apply_to_worktree:
                        self.model.apply_diff_to_worktree(tmpfile)
                    else:
                        self.model.apply_diff(tmpfile)
                    os.unlink(tmpfile)

def strip_prefix(prefix, string):
    """Return string, without the prefix. Blow up if string doesn't
    start with prefix."""
    assert string.startswith(prefix)
    return string[len(prefix):]

def sanitize_input(input):
    """Removes shell metacharacters from a string."""
    for c in """ \t!@#$%^&*()\\;,<>"'[]{}~|""":
        input = input.replace(c, '_')
    return input

def is_linux():
    """Is this a linux machine?"""
    return platform.system() == 'Linux'

def is_debian():
    """Is it debian?"""
    return os.path.exists('/usr/bin/apt-get')

def is_broken():
    """Is it windows or mac? (e.g. is running git-mergetool non-trivial?)"""
    return (platform.system() == 'Windows'
            or 'Macintosh' in platform.platform())
