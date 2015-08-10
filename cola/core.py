"""This module provides core functions for handling unicode and UNIX quirks

The @interruptable functions retry when system calls are interrupted,
e.g. when python raises an IOError or OSError with errno == EINTR.

"""
from __future__ import division, absolute_import, unicode_literals

import os
import sys
import itertools
import platform
import subprocess

from cola.decorators import interruptable
from cola.compat import ustr
from cola.compat import PY2
from cola.compat import PY3
from cola.compat import WIN32

# Some files are not in UTF-8; some other aren't in any codification.
# Remember that GIT doesn't care about encodings (saves binary data)
_encoding_tests = [
    'utf-8',
    'iso-8859-15',
    'windows1252',
    'ascii',
    # <-- add encodings here
]

def decode(enc, encoding=None, errors='strict'):
    """decode(encoded_string) returns an unencoded unicode string
    """
    if enc is None or type(enc) is ustr:
        return enc

    if encoding is None:
        encoding_tests = _encoding_tests
    else:
        encoding_tests = itertools.chain([encoding], _encoding_tests)

    for encoding in encoding_tests:
        try:
            return enc.decode(encoding, errors)
        except:
            pass
    # this shouldn't ever happen... FIXME
    return ustr(enc)


def encode(string, encoding=None):
    """encode(unencoded_string) returns a string encoded in utf-8
    """
    if type(string) is not ustr:
        return string
    return string.encode(encoding or 'utf-8', 'replace')


def mkpath(path, encoding=None):
    # The Windows API requires unicode strings regardless of python version
    if WIN32:
        return decode(path, encoding=encoding)
    # UNIX prefers bytes
    return encode(path, encoding=encoding)


def read(filename, size=-1, encoding=None, errors='strict'):
    """Read filename and return contents"""
    with xopen(filename, 'rb') as fh:
        return fread(fh, size=size, encoding=encoding, errors=errors)


def write(path, contents, encoding=None):
    """Writes a unicode string to a file"""
    with xopen(path, 'wb') as fh:
        return fwrite(fh, contents, encoding=encoding)


@interruptable
def fread(fh, size=-1, encoding=None, errors='strict'):
    """Read from a filehandle and retry when interrupted"""
    return decode(fh.read(size), encoding=encoding, errors=errors)


@interruptable
def fwrite(fh, content, encoding=None):
    """Write to a filehandle and retry when interrupted"""
    return fh.write(encode(content, encoding=encoding))


@interruptable
def wait(proc):
    """Wait on a subprocess and retry when interrupted"""
    return proc.wait()


@interruptable
def readline(fh, encoding=None):
    return decode(fh.readline(), encoding=encoding)


@interruptable
def start_command(cmd, cwd=None, add_env=None,
                  universal_newlines=False,
                  stdin=subprocess.PIPE,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
                  **extra):
    """Start the given command, and return a subprocess object.

    This provides a simpler interface to the subprocess module.

    """
    env = None
    if add_env is not None:
        env = os.environ.copy()
        env.update(add_env)

    # Python3 on windows always goes through list2cmdline() internally inside
    # of subprocess.py so we must provide unicode strings here otherwise
    # Python3 breaks when bytes are provided.
    #
    # Additionally, the preferred usage on Python3 is to pass unicode
    # strings to subprocess.  Python will automatically encode into the
    # default encoding (utf-8) when it gets unicode strings.
    cmd = prep_for_subprocess(cmd)

    if WIN32 and cwd == getcwd():
        # Windows cannot deal with passing a cwd that contains unicode
        # but we luckily can pass None when the supplied cwd is the same
        # as our current directory and get the same effect.
        # Not doing this causes unicode encoding errors when launching
        # the subprocess.
        cwd = None

    return subprocess.Popen(cmd, bufsize=1, stdin=stdin, stdout=stdout,
                            stderr=stderr, cwd=cwd, env=env,
                            universal_newlines=universal_newlines, **extra)


def prep_for_subprocess(cmd):
    """Decode on Python3, encode on Python2"""
    # See the comment in start_command()
    if PY3:
        cmd = [decode(c) for c in cmd]
    else:
        cmd = [encode(c) for c in cmd]
    return cmd


@interruptable
def communicate(proc):
    return proc.communicate()


def run_command(cmd, encoding=None, *args, **kwargs):
    """Run the given command to completion, and return its results.

    This provides a simpler interface to the subprocess module.
    The results are formatted as a 3-tuple: (exit_code, output, errors)
    The other arguments are passed on to start_command().

    """
    process = start_command(cmd, *args, **kwargs)
    (output, errors) = communicate(process)
    output = decode(output, encoding=encoding)
    errors = decode(errors, encoding=encoding)
    exit_code = process.returncode
    return (exit_code, output or '', errors or '')


@interruptable
def _fork_posix(args, cwd=None):
    """Launch a process in the background."""
    encoded_args = [encode(arg) for arg in args]
    return subprocess.Popen(encoded_args, cwd=cwd).pid


def _fork_win32(args, cwd=None):
    """Launch a background process using crazy win32 voodoo."""
    # This is probably wrong, but it works.  Windows.. wow.
    if args[0] == 'git-dag':
        # win32 can't exec python scripts
        args = [sys.executable] + args
    args[0] = _win32_find_exe(args[0])

    if PY3:
        # see comment in start_command()
        argv = [decode(arg) for arg in args]
    else:
        argv = [encode(arg) for arg in args]
    DETACHED_PROCESS = 0x00000008 # Amazing!
    return subprocess.Popen(argv, cwd=cwd, creationflags=DETACHED_PROCESS).pid


def _win32_find_exe(exe):
    """Find the actual file for a Windows executable.

    This function goes through the same process that the Windows shell uses to
    locate an executable, taking into account the PATH and PATHEXT environment
    variables.  This allows us to avoid passing shell=True to subprocess.Popen.

    For reference, see:
    http://technet.microsoft.com/en-us/library/cc723564.aspx#XSLTsection127121120120

    """
    # try the argument itself
    candidates = [exe]
    # if argument does not have an extension, also try it with each of the
    # extensions specified in PATHEXT
    if '.' not in exe:
        extensions = getenv('PATHEXT', '').split(os.pathsep)
        candidates.extend([exe+ext for ext in extensions
                            if ext.startswith('.')])
    # search the current directory first
    for candidate in candidates:
        if exists(candidate):
            return candidate
    # if the argument does not include a path separator, search each of the
    # directories on the PATH
    if not os.path.dirname(exe):
        for path in getenv('PATH').split(os.pathsep):
            if path:
                for candidate in candidates:
                    full_path = os.path.join(path, candidate)
                    if exists(full_path):
                        return full_path
    # not found, punt and return the argument unchanged
    return exe


# Portability wrappers
if sys.platform == 'win32' or sys.platform == 'cygwin':
    fork = _fork_win32
else:
    fork = _fork_posix


def wrap(action, fn, decorator=None):
    """Wrap arguments with `action`, optionally decorate the result"""
    if decorator is None:
        decorator = lambda x: x
    def wrapped(*args, **kwargs):
        return decorator(fn(action(*args, **kwargs)))
    return wrapped


def decorate(decorator, fn):
    """Decorate the result of `fn` with `action`"""
    def decorated(*args, **kwargs):
        return decorator(fn(*args, **kwargs))
    return decorated


def getenv(name, default=None):
    return decode(os.getenv(name, default))


def xopen(path, mode='r', encoding=None):
    return open(mkpath(path, encoding=encoding), mode)


def stdout(msg):
    msg = msg + '\n'
    if PY2:
        msg = encode(msg, encoding='utf-8')
    sys.stdout.write(msg)


def stderr(msg):
    msg = msg + '\n'
    if PY2:
        msg = encode(msg, encoding='utf-8')
    sys.stderr.write(msg)


@interruptable
def node():
    return platform.node()


abspath = wrap(mkpath, os.path.abspath, decorator=decode)
chdir = wrap(mkpath, os.chdir)
exists = wrap(mkpath, os.path.exists)
expanduser = wrap(encode, os.path.expanduser, decorator=decode)
try:  # Python 2
    getcwd = os.getcwdu
except AttributeError:
    getcwd = os.getcwd
isdir = wrap(mkpath, os.path.isdir)
isfile = wrap(mkpath, os.path.isfile)
islink = wrap(mkpath, os.path.islink)
makedirs = wrap(mkpath, os.makedirs)
try:
    readlink = wrap(mkpath, os.readlink, decorator=decode)
except AttributeError:
    readlink = lambda p: p
realpath = wrap(mkpath, os.path.realpath, decorator=decode)
relpath = wrap(mkpath, os.path.relpath, decorator=decode)
stat = wrap(mkpath, os.stat)
unlink = wrap(mkpath, os.unlink)
walk = wrap(mkpath, os.walk)
