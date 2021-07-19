"""Miscellaneous utility functions"""
from __future__ import absolute_import, division, print_function, unicode_literals
import copy
import os
import random
import re
import shlex
import sys
import tempfile
import time
import traceback

from . import core
from . import compat

random.seed(hash(time.time()))


def asint(obj, default=0):
    """Make any value into an int, even if the cast fails"""
    try:
        value = int(obj)
    except (TypeError, ValueError):
        value = default
    return value


def clamp(value, lo, hi):
    """Clamp a value to the specified range"""
    return min(hi, max(lo, value))


def epoch_millis():
    return int(time.time() * 1000)


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


def sublist(a, b):
    """Subtracts list b from list a and returns the resulting list."""
    # conceptually, c = a - b
    c = []
    for item in a:
        if item not in b:
            c.append(item)
    return c


__grep_cache = {}


def grep(pattern, items, squash=True):
    """Greps a list for items that match a pattern

    :param squash: If only one item matches, return just that item
    :returns: List of matching items

    """
    isdict = isinstance(items, dict)
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
        result = matchdict
    elif squash and len(matched) == 1:
        result = matched[0]
    else:
        result = matched

    return result


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


def dirname(path, current_dir=''):
    """
    An os.path.dirname() implementation that always uses '/'

    Avoid os.path.dirname because git's output always
    uses '/' regardless of platform.

    """
    while '//' in path:
        path = path.replace('//', '/')
    path_dirname = path.rsplit('/', 1)[0]
    if path_dirname == path:
        return current_dir
    return path.rsplit('/', 1)[0]


def splitpath(path):
    """Split paths using '/' regardless of platform"""
    return path.split('/')


def join(*paths):
    """Join paths using '/' regardless of platform"""
    return '/'.join(paths)


def pathset(path):
    """Return all of the path components for the specified path

    >>> pathset('foo/bar/baz') == ['foo', 'foo/bar', 'foo/bar/baz']
    True

    """
    result = []
    parts = splitpath(path)
    prefix = ''
    for part in parts:
        result.append(prefix + part)
        prefix += part + '/'

    return result


def select_directory(paths):
    """Return the first directory in a list of paths"""
    if not paths:
        return core.getcwd()

    for path in paths:
        if core.isdir(path):
            return path

    return os.path.dirname(paths[0])


def strip_prefix(prefix, string):
    """Return string, without the prefix. Blow up if string doesn't
    start with prefix."""
    assert string.startswith(prefix)
    return string[len(prefix) :]


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


def _shell_split_py2(s):
    """Python2 requires bytes inputs to shlex.split().  Returns [unicode]"""
    try:
        result = shlex.split(core.encode(s))
    except ValueError:
        result = core.encode(s).strip().split()
    # Decode to unicode strings
    return [core.decode(arg) for arg in result]


def _shell_split_py3(s):
    """Python3 requires unicode inputs to shlex.split().  Converts to unicode"""
    try:
        result = shlex.split(s)
    except ValueError:
        result = core.decode(s).strip().split()
    # Already unicode
    return result


def shell_split(s):
    if compat.PY2:
        # Encode before calling split()
        values = _shell_split_py2(s)
    else:
        # Python3 does not need the encode/decode dance
        values = _shell_split_py3(s)
    return values


def tmp_filename(label, suffix=''):
    label = 'git-cola-' + label.replace('/', '-').replace('\\', '-')
    fd = tempfile.NamedTemporaryFile(prefix=label + '-', suffix=suffix)
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


def slice_fn(input_items, map_fn):
    """Slice input_items and call map_fn over every slice

    This exists because of "errno: Argument list too long"

    """
    # This comment appeared near the top of include/linux/binfmts.h
    # in the Linux source tree:
    #
    # /*
    #  * MAX_ARG_PAGES defines the number of pages allocated for arguments
    #  * and envelope for the new program. 32 should suffice, this gives
    #  * a maximum env+arg of 128kB w/4KB pages!
    #  */
    # #define MAX_ARG_PAGES 32
    #
    # 'size' is a heuristic to keep things highly performant by minimizing
    # the number of slices.  If we wanted it to run as few commands as
    # possible we could call "getconf ARG_MAX" and make a better guess,
    # but it's probably not worth the complexity (and the extra call to
    # getconf that we can't do on Windows anyways).
    #
    # In my testing, getconf ARG_MAX on Mac OS X Mountain Lion reported
    # 262144 and Debian/Linux-x86_64 reported 2097152.
    #
    # The hard-coded max_arg_len value is safely below both of these
    # real-world values.

    # 4K pages x 32 MAX_ARG_PAGES
    max_arg_len = (32 * 4096) // 4  # allow plenty of space for the environment
    max_filename_len = 256
    size = max_arg_len // max_filename_len

    status = 0
    outs = []
    errs = []

    items = copy.copy(input_items)
    while items:
        stat, out, err = map_fn(items[:size])
        if stat < 0:
            status = min(stat, status)
        else:
            status = max(stat, status)
        outs.append(out)
        errs.append(err)
        items = items[size:]

    return (status, '\n'.join(outs), '\n'.join(errs))


class seq(object):
    def __init__(self, sequence):
        self.seq = sequence

    def index(self, item, default=-1):
        try:
            idx = self.seq.index(item)
        except ValueError:
            idx = default
        return idx

    def __getitem__(self, idx):
        return self.seq[idx]
