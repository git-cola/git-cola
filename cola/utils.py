# Copyright (c) 2008 David Aguilar
"""This module provides miscellaneous utility functions."""

import os
import re
import sys
import errno
import platform
import subprocess
import mimetypes

from cola import git
from cola import core
from cola import resources
from cola.compat import hashlib
from cola.decorators import memoize


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


def add_parents(path_entry_set):
    """Iterate over each item in the set and add its parent directories."""
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


def run_cmd(command):
    """
    Run arguments as a command and return output.

    >>> run_cmd(["echo", "hello", "world"])
    'hello world'

    """
    return git.Git.execute(command)


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


def file_icon(filename):
    """
    Returns the full path to an icon file corresponding to
    filename"s contents.
    """
    return resources.icon(ident_file_type(filename))


def win32_abspath(exe):
    """Return the absolute path to an .exe if it exists"""
    if os.path.exists(exe):
        return exe
    if not exe.endswith('.exe'):
        exe += '.exe'
    if os.path.exists(exe):
        return exe
    for path in os.environ['PATH'].split(os.pathsep):
        abspath = os.path.join(path, exe)
        if os.path.exists(abspath):
            return abspath
    return None


def fork(args):
    """Launch a command in the background."""
    if is_win32():
        # Windows is absolutely insane.
        enc_args = map(core.encode, args)
        abspath = win32_abspath(args[0])
        if abspath:
            # e.g. fork(['git', 'difftool', '--no-prompt', '--', 'path'])
            return os.spawnv(os.P_NOWAIT, abspath, enc_args)
        else:
            # e.g. fork(['gitk', '--all'])
            cmdstr = subprocess.list2cmdline(enc_args)
            sh_exe = win32_abspath('sh')
            cmd = ['sh.exe', '-c', cmdstr]
            return os.spawnv(os.P_NOWAIT, sh_exe, cmd)
    else:
        # I like having a sane os.system()
        enc_args = [core.encode(a) for a in args]
        cmdstr = subprocess.list2cmdline(enc_args)
        return os.system(cmdstr + '&')


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


def slurp(path):
    """Slurps a filepath into a string."""
    fh = open(core.encode(path))
    slushy = core.read_nointr(fh)
    fh.close()
    return core.decode(slushy)


def write(path, contents):
    """Writes a raw string to a file."""
    fh = open(core.encode(path), 'wb')
    core.write_nointr(fh, core.encode(contents))
    fh.close()


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

def is_linux():
    """Is this a linux machine?"""
    while True:
        try:
            return platform.system() == 'Linux'
        except IOError, e:
            if e.errno == errno.EINTR:
                continue
            raise e

def is_debian():
    """Is it debian?"""
    return os.path.exists('/usr/bin/apt-get')


def is_darwin():
    """Return True on OSX."""
    while True:
        try:
            p = platform.platform()
            break
        except IOError, e:
            if e.errno == errno.EINTR:
                continue
            raise e
    p = p.lower()
    return 'macintosh' in p or 'darwin' in p


@memoize
def is_win32():
    """Return True on win32"""
    return os.name in ('nt', 'dos')


@memoize
def is_broken():
    """Is it windows or mac? (e.g. is running git-mergetool non-trivial?)"""
    if is_darwin():
        return True
    while True:
        try:
            return platform.system() == 'Windows'
        except IOError, e:
            if e.errno == errno.EINTR:
                continue
            raise e
    return False


def checksum(path):
    """Return a cheap md5 hexdigest for a path."""
    md5 = hashlib.new('md5')
    md5.update(slurp(path))
    return md5.hexdigest()


def quote_repopath(repopath):
    """Quote a path for nt/dos only."""
    if is_win32():
        repopath = '"%s"' % repopath
    return repopath

# From git.git
"""Misc. useful functionality used by the rest of this package.

This module provides common functionality used by the other modules in
this package.

"""
# Whether or not to show debug messages
DEBUG = False

def notify(msg, *args):
    """Print a message to stderr."""
    print >> sys.stderr, msg % args

def debug (msg, *args):
    """Print a debug message to stderr when DEBUG is enabled."""
    if DEBUG:
        print >> sys.stderr, msg % args

def error (msg, *args):
    """Print an error message to stderr."""
    print >> sys.stderr, "ERROR:", msg % args

def warn(msg, *args):
    """Print a warning message to stderr."""
    print >> sys.stderr, "warning:", msg % args

def die (msg, *args):
    """Print as error message to stderr and exit the program."""
    error(msg, *args)
    sys.exit(1)


class ProgressIndicator(object):

    """Simple progress indicator.

    Displayed as a spinning character by default, but can be customized
    by passing custom messages that overrides the spinning character.

    """

    States = ("|", "/", "-", "\\")

    def __init__ (self, prefix = "", f = sys.stdout):
        """Create a new ProgressIndicator, bound to the given file object."""
        self.n = 0  # Simple progress counter
        self.f = f  # Progress is written to this file object
        self.prev_len = 0  # Length of previous msg (to be overwritten)
        self.prefix = prefix  # Prefix prepended to each progress message
        self.prefix_lens = [] # Stack of prefix string lengths

    def pushprefix (self, prefix):
        """Append the given prefix onto the prefix stack."""
        self.prefix_lens.append(len(self.prefix))
        self.prefix += prefix

    def popprefix (self):
        """Remove the last prefix from the prefix stack."""
        prev_len = self.prefix_lens.pop()
        self.prefix = self.prefix[:prev_len]

    def __call__ (self, msg = None, lf = False):
        """Indicate progress, possibly with a custom message."""
        if msg is None:
            msg = self.States[self.n % len(self.States)]
        msg = self.prefix + msg
        print >> self.f, "\r%-*s" % (self.prev_len, msg),
        self.prev_len = len(msg.expandtabs())
        if lf:
            print >> self.f
            self.prev_len = 0
        self.n += 1

    def finish (self, msg = "done", noprefix = False):
        """Finalize progress indication with the given message."""
        if noprefix:
            self.prefix = ""
        self(msg, True)


def start_command (args, cwd = None, shell = False, add_env = None,
                   stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                   stderr = subprocess.PIPE):
    """Start the given command, and return a subprocess object.

    This provides a simpler interface to the subprocess module.

    """
    env = None
    if add_env is not None:
        env = os.environ.copy()
        env.update(add_env)
    return subprocess.Popen(args, bufsize = 1, stdin = stdin, stdout = stdout,
                            stderr = stderr, cwd = cwd, shell = shell,
                            env = env, universal_newlines = True)


def run_command (args, cwd = None, shell = False, add_env = None,
                 flag_error = True):
    """Run the given command to completion, and return its results.

    This provides a simpler interface to the subprocess module.

    The results are formatted as a 3-tuple: (exit_code, output, errors)

    If flag_error is enabled, Error messages will be produced if the
    subprocess terminated with a non-zero exit code and/or stderr
    output.

    The other arguments are passed on to start_command().

    """
    process = start_command(args, cwd, shell, add_env)
    (output, errors) = process.communicate()
    exit_code = process.returncode
    if flag_error and errors:
        error("'%s' returned errors:\n---\n%s---", " ".join(args), errors)
    if flag_error and exit_code:
        error("'%s' returned exit code %i", " ".join(args), exit_code)
    return (exit_code, output, errors)
