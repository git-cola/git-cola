# Copyright (c) 2008 David Aguilar
"""This module provides miscellaneous utility functions."""

import os
import re
import sys
import errno
import platform
import subprocess
import hashlib
import mimetypes

from glob import glob
from cStringIO import StringIO

from cola import git
from cola import core
from cola import resources
from cola.git import shell_quote

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


def qm_for_locale(locale):
    """Returns the .qm file for a particular $LANG values."""
    regex = re.compile(r'([^\.])+\..*$')
    match = regex.match(locale)
    if match:
        locale = match.group(1)
    return resources.qm(locale.split('_')[0])


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


def win32_expand_paths(args):
    """Expand filenames after the double-dash"""
    if '--' not in args:
        return args
    dashes_idx = args.index('--')
    cmd = args[:dashes_idx+1]
    for path in args[dashes_idx+1:]:
        cmd.append(shell_quote(os.path.join(os.getcwd(), path)))
    return cmd


def fork(args):
    """Launch a command in the background."""
    if is_win32():
        # Windows is absolutely insane.
        #
        # If we want to launch 'gitk' we have to use the 'sh -c' trick.
        #
        # If we want to launch 'git.exe' we have to expand all filenames
        # after the double-dash.
        #
        # os.spawnv wants an absolute path in the command name but not in
        # the command vector.  Wow.
        enc_args = win32_expand_paths([core.encode(a) for a in args])
        abspath = win32_abspath(enc_args[0])
        if abspath:
            # e.g. fork(['git', 'difftool', '--no-prompt', '--', 'path'])
            return os.spawnv(os.P_NOWAIT, abspath, enc_args)

        # e.g. fork(['gitk', '--all'])
        sh_exe = win32_abspath('sh')
        enc_argv = map(shell_quote, enc_args)
        cmdstr = ' '.join(enc_argv)
        cmd = ['sh.exe', '-c', cmdstr]
        return os.spawnv(os.P_NOWAIT, sh_exe, cmd)
    else:
        # Unix is absolutely simple
        enc_args = [core.encode(a) for a in args]
        enc_argv = map(shell_quote, enc_args)
        cmdstr = ' '.join(enc_argv)
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
    fh = open(path)
    slushy = core.read_nointr(fh)
    fh.close()
    return core.decode(slushy)


def write(path, contents):
    """Writes a string to a file."""
    fh = open(path, 'w')
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


_is_win32 = None
def is_win32():
    """Return True on win32"""
    global _is_win32
    if _is_win32 is None:
        _is_win32 = os.name in ('nt', 'dos')
    return _is_win32


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
