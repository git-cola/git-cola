"""Miscellaneous utility functions"""
import copy
import hashlib
import os
import re
import shlex
import shutil
import sys
import tempfile
import time
import traceback
import urllib.parse

from . import core
from . import compat


_SSH_REGEX = re.compile(r'^(?P<user>[^@]+)@(?P<hostname>[^:]+):(?P<path>.+)')


def asint(obj, default=0):
    """Make any value into an int, even if the cast fails"""
    try:
        value = int(obj)
    except (TypeError, ValueError):
        value = default
    return value


def clamp(value, low, high):
    """Clamp a value to the specified range"""
    return min(high, max(low, value))


def clamp_zero(value, maximum):
    """Clamp a value between 0 and the maximum value"""
    return clamp(value, 0, maximum)


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


def format_exception(exc):
    """Format an exception object for display"""
    exc_type, exc_value, exc_tb = sys.exc_info()
    details = traceback.format_exception(exc_type, exc_value, exc_tb)
    details = '\n'.join(map(core.decode, details))
    if hasattr(exc, 'msg'):
        msg = exc.msg
    else:
        msg = core.decode(repr(exc))
    return (msg, details)


def sublist(values, remove):
    """Subtracts list b from list a and returns the resulting list."""
    # conceptually, c = a - b
    result = []
    for item in values:
        if item not in remove:
            result.append(item)
    return result


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


def split(name):
    """Split a path-like name. Returns tuple "(head, tail)" where "tail" is
    everything after the final slash. The "head" may be empty.

    This is the same as os.path.split() but only uses '/' as the delimiter.

    >>> split('a/b/c')
    ('a/b', 'c')

    >>> split('xyz')
    ('', 'xyz')

    """
    return (dirname(name), basename(name))


def join(*paths):
    """Join paths using '/' regardless of platform

    >>> join('a', 'b', 'c')
    'a/b/c'

    """
    return '/'.join(paths)


def normalize_slash(value):
    """Strip and normalize slashes in a string

    >>> normalize_slash('///Meow///Cat///')
    'Meow/Cat'

    """
    value = value.strip('/')
    new_value = value.replace('//', '/')
    while new_value != value:
        value = new_value
        new_value = value.replace('//', '/')
    return value


def pathjoin(paths):
    """Join a list of paths using '/' regardless of platform

    >>> pathjoin(['a', 'b', 'c'])
    'a/b/c'

    """
    return join(*paths)


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

    return os.path.dirname(paths[0]) or core.getcwd()


def strip_prefix(prefix, string):
    """Return string, without the prefix. Blow up if string doesn't
    start with prefix."""
    assert string.startswith(prefix)
    return string[len(prefix) :]


def tablength(word, tabwidth):
    """Return length of a word taking tabs into account

    >>> tablength("\\t\\t\\t\\tX", 8)
    33

    """
    return len(word.replace('\t', '')) + word.count('\t') * tabwidth


def _shell_split_py2(value):
    """Python2 requires bytes inputs to shlex.split().  Returns [unicode]"""
    try:
        result = shlex.split(core.encode(value))
    except ValueError:
        result = core.encode(value).strip().split()
    # Decode to Unicode strings
    return [core.decode(arg) for arg in result]


def _shell_split_py3(value):
    """Python3 requires Unicode inputs to shlex.split().  Convert to Unicode"""
    try:
        result = shlex.split(value)
    except ValueError:
        result = core.decode(value).strip().split()
    # Already Unicode
    return result


def shell_split(value):
    if compat.PY2:
        # Encode before calling split()
        values = _shell_split_py2(value)
    else:
        # Python3 does not need the encode/decode dance
        values = _shell_split_py3(value)
    return values


def tmp_filename(label, suffix=''):
    label = 'git-cola-' + label.replace('/', '-').replace('\\', '-')
    with tempfile.NamedTemporaryFile(
        prefix=label + '-', suffix=suffix, delete=False
    ) as handle:
        return handle.name


def find_bash_exe():
    """
    Locate bash.exe bundled with Git for Windows.

    Git for Windows ships its own bash.exe, but it is not added to PATH.
    This function finds git.exe via PATH, derives the Git installation root,
    and searches typical subdirectories for bash.exe.
    """
    # Find git.exe in PATH
    git_path = shutil.which('git.exe') or shutil.which('git')
    if not git_path:
        return None

    # Estimate Git root directory (e.g., C:\Program Files\Git)
    cmd_dir = os.path.dirname(os.path.abspath(git_path))
    git_root = os.path.dirname(cmd_dir)

    # Typical relative locations for bash.exe under Git for Windows
    candidates = ['bin', 'mingw64/bin', 'usr/bin']

    # Search and return the first match
    for rel in candidates:
        bash = os.path.join(git_root, rel, 'bash.exe')
        if os.path.exists(bash):
            return bash.replace('\\', '/')

    return None


def is_linux():
    """Is this a Linux machine?"""
    return sys.platform.startswith('linux')


def is_debian():
    """Is this a Debian/Linux machine?"""
    return os.path.exists('/usr/bin/apt-get')


def is_darwin():
    """Is this a macOS machine?"""
    return sys.platform == 'darwin'


def is_win32():
    """Return True on win32"""
    return sys.platform in {'win32', 'cygwin'}


def launch_default_app(paths):
    """Execute the default application on the specified paths"""
    if is_win32():
        for path in paths:
            if hasattr(os, 'startfile'):
                os.startfile(os.path.abspath(path))
        return

    if is_darwin():
        launcher = 'open'
    else:
        launcher = 'xdg-open'

    core.fork([launcher] + paths)


def expandpath(path):
    """Expand ~user/ and environment $variables"""
    path = os.path.expandvars(path)
    if path.startswith('~'):
        path = os.path.expanduser(path)
    return path


def get_hostname_from_url(url_str):
    """Extract the hostname component from a URL

    >>> get_hostname_from_url('user@example.org:namespace/project')
    'example.org'

    >>> get_hostname_from_url('user@example.org:namespace/project.git/')
    'example.org'

    >>> get_hostname_from_url('https://example.org/namespace/project.git')
    'example.org'

    >>> get_hostname_from_url('ssh://user@example.org/namespace/project.git')
    'example.org'

    """
    if not url_str:
        return None
    url = urllib.parse.urlparse(url_str)
    if not url or url.scheme == '' or url.netloc == '':
        # Handle <user>@<host>:path.git URLs
        match = _SSH_REGEX.match(url_str)
        if match is None:
            return None
        hostname = match.group('hostname')
        if not hostname:
            return None
    else:
        hostname = url.netloc

    if '@' in hostname:
        _, hostname = hostname.split('@', 1)

    return hostname


def get_path_from_url(url_str):
    """Extract the path component from a URL

    >>> get_path_from_url('user@example.org:namespace/project')
    'namespace/project'

    >>> get_path_from_url('user@example.org:namespace/project.git/')
    'namespace/project'

    >>> get_path_from_url('https://example.org/namespace/project.git')
    'namespace/project'

    >>> get_path_from_url('ssh://user@example.org/namespace/project.git')
    'namespace/project'

    """
    if not url_str:
        return None
    url = urllib.parse.urlparse(url_str)
    if not url or url.scheme == '' or url.path == '':
        # Handle <user>@<host>:path.git URLs
        match = _SSH_REGEX.match(url_str)
        if match is None:
            return None
        path = match.group('path')
        if not path:
            return None
    else:
        path = url.path

    path = path.strip('/')  # Strip leading and trailing slashes.
    if path.endswith('.git'):
        path = path[: -len('.git')]

    return path


class Group:
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


def strip_prefixes_and_suffixes(values, prefix, suffix):
    """Strip prefixes and suffixes from a sequence of values

    Values are assumed to begin and end with the specified prefix and suffix.
    """
    prefix_len = len(prefix)
    suffix_len = len(suffix)
    if suffix_len == 0:
        return sorted(name[prefix_len:] for name in values)
    return sorted(name[prefix_len:-suffix_len] for name in values)


def strip_prefixes_and_suffixes_from_keys(values, prefix, suffix):
    """Transform dictionary keys to remove prefixes and suffixes

    Values are assumed to begin and end with the specified prefix and suffix.
    """
    prefix_len = len(prefix)
    suffix_len = len(suffix)
    if suffix_len == 0:
        return {key[prefix_len:]: value for (key, value) in values.items()}
    return {key[prefix_len:-suffix_len]: value for (key, value) in values.items()}


def strip_prefixes_from_keys(values, prefix):
    """Transform dictionary keys to remove prefixes

    Values are assumed to begin with the specified prefix.
    """
    return strip_prefixes_and_suffixes_from_keys(values, prefix, '')


class Proxy:
    """Wrap an object and override attributes"""

    def __init__(self, obj, **overrides):
        self._obj = obj
        for k, v in overrides.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        return getattr(self._obj, name)


def slice_func(input_items, map_func):
    """Slice input_items and call `map_func` over every slice

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
        stat, out, err = map_func(items[:size])
        if stat < 0:
            status = min(stat, status)
        else:
            status = max(stat, status)
        outs.append(out)
        errs.append(err)
        items = items[size:]

    return (status, '\n'.join(outs), '\n'.join(errs))


class Sequence:
    def __init__(self, sequence):
        self.sequence = sequence

    def index(self, item, default=-1):
        try:
            idx = self.sequence.index(item)
        except ValueError:
            idx = default
        return idx

    def __getitem__(self, idx):
        return self.sequence[idx]


def catch_runtime_error(func, *args, **kwargs):
    """Run the function safely.

    Catch RuntimeError to avoid tracebacks during application shutdown.

    """
    # Signals and callbacks can sometimes get triggered during application shutdown.
    # This can happen when exiting while background tasks are still processing.
    # Guard against this by making this operation a no-op.
    try:
        valid = True
        result = func(*args, **kwargs)
    except RuntimeError:
        valid = False
        result = None
    return (valid, result)


def sha256hex(value):
    """Return a hexdigest of the SHA-256 hash of the specified value"""
    hash = hashlib.new('sha256')
    hash.update(value.encode('utf-8', 'replace'))
    return hash.hexdigest()
