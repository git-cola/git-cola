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
from cola.decorators import memoize

random.seed(hash(time.time()))


def add_parents(paths):
    """Iterate over each item in the set and add its parent directories."""
    all_paths = set()
    for path in paths:
        while '//' in path:
            path = path.replace('//', '/')
        all_paths.add(path)
        if '/' in path:
            parent_dir = dirname(path)
            while parent_dir:
                all_paths.add(parent_dir)
                parent_dir = dirname(parent_dir)
    return all_paths


def format_exception(e):
    exc_type, exc_value, exc_tb = sys.exc_info()
    details = traceback.format_exception(exc_type, exc_value, exc_tb)
    details = '\n'.join(map(core.decode, details))
    if hasattr(e, 'msg'):
        msg = e.msg
    else:
        msg = core.decode(repr(e))
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
    """Strip one level of directory"""
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


def tmp_filename(label):
    label = 'git-cola-' + label.replace('/', '-').replace('\\', '-')
    fd = tempfile.NamedTemporaryFile(prefix=label+'-')
    fd.close()
    return fd.name


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


class Group(object):
    """Operate on a collection of objects as a single unit"""

    def __init__(self, *members):
        self._members = members

    def __getattr__(self, name):
        """Return a function that relays calls to the group"""
        def relay(*args, **kwargs):
            for member in self._members:
                method = getattr(member, name)
                method(*args, **kwargs)
        setattr(self, name, relay)
        return relay


class Proxy(object):
    """Wrap an object and override attributes"""

    def __init__(self, obj, **overrides):
        self._obj = obj
        for k, v in overrides.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        return getattr(self._obj, name)
