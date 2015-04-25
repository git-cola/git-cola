# Copyright (c) 2008 David Aguilar
"""This module provides miscellaneous utility functions."""
from __future__ import division, absolute_import, unicode_literals

import os
import random
import re
import shlex
import sys
import tempfile
import time
import traceback

from cola import core

random.seed(hash(time.time()))


def add_parents(paths):
    """Iterate over each item in the set and add its parent directories."""
    path_entry_set = set(paths)
    for path in list(path_entry_set):
        while '//' in path:
            path = path.replace('//', '/')
        if path not in path_entry_set:
            path_entry_set.add(path)
        if '/' in path:
            parent_dir = dirname(path)
            while parent_dir and parent_dir not in path_entry_set:
                path_entry_set.add(parent_dir)
                parent_dir = dirname(parent_dir)
    return path_entry_set


def format_exception(e):
    exc_type, exc_value, exc_tb = sys.exc_info()
    details = traceback.format_exception(exc_type, exc_value, exc_tb)
    details = '\n'.join(details)
    if hasattr(e, 'msg'):
        msg = e.msg
    else:
        msg = str(e)
    return (msg, details)


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
    """
    An os.path.basename() implementation that always uses '/'

    Avoid os.path.basename because git's output always
    uses '/' regardless of platform.

    """
    return path.rsplit('/', 1)[-1]


def strip_one(path):
    """Strip one level of directory

    >>> strip_one('/usr/bin/git')
    u'bin/git'

    >>> strip_one('local/bin/git')
    u'bin/git'

    >>> strip_one('bin/git')
    u'git'

    >>> strip_one('git')
    u'git'

    """
    return path.strip('/').split('/', 1)[-1]


def dirname(path):
    """
    An os.path.dirname() implementation that always uses '/'

    Avoid os.path.dirname because git's output always
    uses '/' regardless of platform.

    """
    while '//' in path:
        path = path.replace('//', '/')
    path_dirname = path.rsplit('/', 1)[0]
    if path_dirname == path:
        return ''
    return path.rsplit('/', 1)[0]


def strip_prefix(prefix, string):
    """Return string, without the prefix. Blow up if string doesn't
    start with prefix."""
    assert string.startswith(prefix)
    return string[len(prefix):]


def sanitize(s):
    """Removes shell metacharacters from a string."""
    for c in """ \t!@#$%^&*()\\;,<>"'[]{}~|""":
        s = s.replace(c, '_')
    return s


def tablength(word, tabwidth):
    """Return length of a word taking tabs into account

    >>> tablength("\\t\\t\\t\\tX", 8)
    33

    """
    return len(word.replace('\t', '')) + word.count('\t') * tabwidth


def _shell_split(s):
    """Split string apart into utf-8 encoded words using shell syntax"""
    try:
        return shlex.split(core.encode(s))
    except ValueError:
        return [core.encode(s)]


if sys.version_info[0] == 3:
    # In Python 3, we don't need the encode/decode dance
    shell_split = shlex.split
else:
    def shell_split(s):
        """Returns a unicode list instead of encoded strings"""
        return [core.decode(arg) for arg in _shell_split(s)]


def tmp_file_pattern():
    return os.path.join(tempfile.gettempdir(), 'git-cola-%s-*' % os.getpid())


def tmp_filename(label):
    prefix = 'git-cola-%s-' % (os.getpid())
    suffix = '-%s' % label.replace('/', '-').replace('\\', '-')
    fd, path = tempfile.mkstemp(suffix, prefix)
    os.close(fd)
    return path


def is_linux():
    """Is this a linux machine?"""
    return sys.platform.startswith('linux')


def is_debian():
    """Is it debian?"""
    return os.path.exists('/usr/bin/apt-get')


def is_darwin():
    """Return True on OSX."""
    return sys.platform == 'darwin'


def is_win32():
    """Return True on win32"""
    return sys.platform == 'win32' or sys.platform == 'cygwin'


def expandpath(path):
    """Expand ~user/ and environment $variables"""
    path = os.path.expandvars(path)
    if path.startswith('~'):
        path = os.path.expanduser(path)
    return path
