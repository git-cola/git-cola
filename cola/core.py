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

# Some files are not in UTF-8; some other aren't in any codification.
# Remember that GIT doesn't care about encodings (saves binary data)
_encoding_tests = [
    'utf-8',
    'iso-8859-15',
    'windows1252',
    'ascii',
    # <-- add encodings here
]

def decode(enc, encoding=None):
    """decode(encoded_string) returns an unencoded unicode string
    """
    if enc is None or type(enc) is unicode:
        return enc

    if encoding is None:
        encoding_tests = _encoding_tests
    else:
        encoding_tests = itertools.chain([encoding], _encoding_tests)

    for encoding in encoding_tests:
        try:
            return enc.decode(encoding)
        except:
            pass
    # this shouldn't ever happen... FIXME
    return unicode(enc)


def encode(string, encoding=None):
    """encode(unencoded_string) returns a string encoded in utf-8
    """
    if type(string) is not unicode:
        return string
    return string.encode(encoding or 'utf-8', 'replace')


def read(filename, size=-1, encoding=None):
    """Read filename and return contents"""
    with xopen(filename, 'r') as fh:
        return fread(fh, size=size, encoding=encoding)


def write(path, contents, encoding=None):
    """Writes a unicode string to a file"""
    with xopen(path, 'wb') as fh:
        return fwrite(fh, contents, encoding=encoding)


@interruptable
def fread(fh, size=-1, encoding=None):
    """Read from a filehandle and retry when interrupted"""
    return decode(fh.read(size), encoding=encoding)


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
def start_command(cmd, cwd=None, shell=False, add_env=None,
                  universal_newlines=False,
                  stdin=subprocess.PIPE,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE):
    """Start the given command, and return a subprocess object.

    This provides a simpler interface to the subprocess module.

    """
    env = None
    if add_env is not None:
        env = os.environ.copy()
        env.update(add_env)
    cmd = [encode(c) for c in cmd]
    return subprocess.Popen(cmd, bufsize=1, stdin=stdin, stdout=stdout,
                            stderr=stderr, cwd=cwd, shell=shell, env=env,
                            universal_newlines=universal_newlines)


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
    return (exit_code, output, errors)


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

    argv = [encode(arg) for arg in args]
    abspath = _win32_abspath(argv[0])
    if abspath:
        # e.g. fork(['git', 'difftool', '--no-prompt', '--', 'path'])
        argv[0] = abspath
    else:
        # e.g. fork(['gitk', '--all'])
        cmdstr = subprocess.list2cmdline(argv)
        sh_exe = _win32_abspath('sh')
        argv = [sh_exe, '-c', cmdstr]

    DETACHED_PROCESS = 0x00000008 # Amazing!
    return subprocess.Popen(argv, cwd=cwd, creationflags=DETACHED_PROCESS).pid


def _win32_abspath(exe):
    """Return the absolute path to an .exe if it exists"""
    if exists(exe):
        return exe
    if not exe.endswith('.exe'):
        exe += '.exe'
    if exists(exe):
        return exe
    for path in getenv('PATH', '').split(os.pathsep):
        abspath = os.path.join(path, exe)
        if exists(abspath):
            return abspath
    return None


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
    return decode(os.getenv(encode(name), default))


def xopen(path, mode='r', encoding=None):
    return open(encode(path, encoding=encoding), mode)


def stdout(msg):
    sys.stdout.write(encode(msg) + '\n')


def stderr(msg):
    sys.stderr.write(encode(msg) + '\n')


@interruptable
def node():
    return platform.node()


abspath = wrap(encode, os.path.abspath, decorator=decode)
chdir = wrap(encode, os.chdir)
exists = wrap(encode, os.path.exists)
expanduser = wrap(encode, os.path.expanduser, decorator=decode)
getcwd = decorate(decode, os.getcwd)
isdir = wrap(encode, os.path.isdir)
isfile = wrap(encode, os.path.isfile)
islink = wrap(encode, os.path.islink)
makedirs = wrap(encode, os.makedirs)
try:
    readlink = wrap(encode, os.readlink, decorator=decode)
except AttributeError:
    readlink = lambda p: p
realpath = wrap(encode, os.path.realpath, decorator=decode)
stat = wrap(encode, os.stat)
unlink = wrap(encode, os.unlink)
walk = wrap(encode, os.walk)
