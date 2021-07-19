"""This module provides core functions for handling unicode and UNIX quirks

The @interruptable functions retry when system calls are interrupted,
e.g. when python raises an IOError or OSError with errno == EINTR.

"""
from __future__ import absolute_import, division, print_function, unicode_literals
import functools
import itertools
import mimetypes
import os
import platform
import subprocess
import sys

from .decorators import interruptable
from .compat import ustr
from .compat import PY2
from .compat import PY3
from .compat import WIN32

# /usr/include/stdlib.h
# #define EXIT_SUCCESS    0   /* Successful exit status.  */
# #define EXIT_FAILURE    1   /* Failing exit status.  */
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

# /usr/include/sysexits.h
# #define EX_USAGE        64  /* command line usage error */
# #define EX_NOINPUT      66  /* cannot open input */
# #define EX_UNAVAILABLE  69  /* service unavailable */
EXIT_USAGE = 64
EXIT_NOINPUT = 66
EXIT_UNAVAILABLE = 69

# Default encoding
ENCODING = 'utf-8'

# Some files are not in UTF-8; some other aren't in any codification.
# Remember that GIT doesn't care about encodings (saves binary data)
_encoding_tests = [
    ENCODING,
    'iso-8859-15',
    'windows1252',
    'ascii',
    # <-- add encodings here
]


class UStr(ustr):
    """Unicode string wrapper that remembers its encoding

    UStr wraps unicode strings to provide the `encoding` attribute.
    UStr is used when decoding strings of an unknown encoding.
    In order to generate patches that contain the original byte sequences,
    we must preserve the original encoding when calling decode()
    so that it can later be used when reconstructing the original
    byte sequences.

    """

    def __new__(cls, string, encoding):

        if isinstance(string, UStr):
            if encoding != string.encoding:
                raise ValueError(
                    'Encoding conflict: %s vs. %s' % (string.encoding, encoding)
                )
            string = ustr(string)

        obj = ustr.__new__(cls, string)
        obj.encoding = encoding
        return obj


def decode_maybe(value, encoding, errors='strict'):
    """Decode a value when the "decode" method exists"""
    if hasattr(value, 'decode'):
        result = value.decode(encoding, errors=errors)
    else:
        result = value
    return result


def decode(value, encoding=None, errors='strict'):
    """decode(encoded_string) returns an unencoded unicode string"""
    if value is None:
        result = None
    elif isinstance(value, ustr):
        result = UStr(value, ENCODING)
    elif encoding == 'bytes':
        result = value
    else:
        result = None
        if encoding is None:
            encoding_tests = _encoding_tests
        else:
            encoding_tests = itertools.chain([encoding], _encoding_tests)

        for enc in encoding_tests:
            try:
                decoded = value.decode(enc, errors)
                result = UStr(decoded, enc)
                break
            except ValueError:
                pass

        if result is None:
            decoded = value.decode(ENCODING, errors='ignore')
            result = UStr(decoded, ENCODING)

    return result


def encode(string, encoding=None):
    """encode(unencoded_string) returns a string encoded in utf-8"""
    if not isinstance(string, ustr):
        return string
    return string.encode(encoding or ENCODING, 'replace')


def mkpath(path, encoding=None):
    # The Windows API requires unicode strings regardless of python version
    if WIN32:
        return decode(path, encoding=encoding)
    # UNIX prefers bytes
    return encode(path, encoding=encoding)


def list2cmdline(cmd):
    return subprocess.list2cmdline([decode(c) for c in cmd])


def read(filename, size=-1, encoding=None, errors='strict'):
    """Read filename and return contents"""
    with xopen(filename, 'rb') as fh:
        return xread(fh, size=size, encoding=encoding, errors=errors)


def write(path, contents, encoding=None):
    """Writes a unicode string to a file"""
    with xopen(path, 'wb') as fh:
        return xwrite(fh, contents, encoding=encoding)


@interruptable
def xread(fh, size=-1, encoding=None, errors='strict'):
    """Read from a filehandle and retry when interrupted"""
    return decode(fh.read(size), encoding=encoding, errors=errors)


@interruptable
def xwrite(fh, content, encoding=None):
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
def start_command(
    cmd,
    cwd=None,
    add_env=None,
    universal_newlines=False,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    no_win32_startupinfo=False,
    stderr=subprocess.PIPE,
    **extra
):
    """Start the given command, and return a subprocess object.

    This provides a simpler interface to the subprocess module.

    """
    env = extra.pop('env', None)
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
    shell = extra.get('shell', False)
    cmd = prep_for_subprocess(cmd, shell=shell)

    if WIN32 and cwd == getcwd():
        # Windows cannot deal with passing a cwd that contains unicode
        # but we luckily can pass None when the supplied cwd is the same
        # as our current directory and get the same effect.
        # Not doing this causes unicode encoding errors when launching
        # the subprocess.
        cwd = None

    if PY2 and cwd:
        cwd = encode(cwd)

    if WIN32:
        # If git-cola is invoked on Windows using "start pythonw git-cola",
        # a console window will briefly flash on the screen each time
        # git-cola invokes git, which is very annoying.  The code below
        # prevents this by ensuring that any window will be hidden.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        extra['startupinfo'] = startupinfo

        if WIN32 and not no_win32_startupinfo:
            CREATE_NO_WINDOW = 0x08000000
            extra['creationflags'] = CREATE_NO_WINDOW

    # Use line buffering when in text/universal_newlines mode,
    # otherwise use the system default buffer size.
    bufsize = 1 if universal_newlines else -1
    return subprocess.Popen(
        cmd,
        bufsize=bufsize,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
        env=env,
        universal_newlines=universal_newlines,
        **extra
    )


def prep_for_subprocess(cmd, shell=False):
    """Decode on Python3, encode on Python2"""
    # See the comment in start_command()
    if shell:
        if PY3:
            cmd = decode(cmd)
        else:
            cmd = encode(cmd)
    else:
        if PY3:
            cmd = [decode(c) for c in cmd]
        else:
            cmd = [encode(c) for c in cmd]
    return cmd


@interruptable
def communicate(proc):
    return proc.communicate()


def run_command(cmd, *args, **kwargs):
    """Run the given command to completion, and return its results.

    This provides a simpler interface to the subprocess module.
    The results are formatted as a 3-tuple: (exit_code, output, errors)
    The other arguments are passed on to start_command().

    """
    encoding = kwargs.pop('encoding', None)
    process = start_command(cmd, *args, **kwargs)
    (output, errors) = communicate(process)
    output = decode(output, encoding=encoding)
    errors = decode(errors, encoding=encoding)
    exit_code = process.returncode
    return (exit_code, output or UStr('', ENCODING), errors or UStr('', ENCODING))


@interruptable
def _fork_posix(args, cwd=None, shell=False):
    """Launch a process in the background."""
    encoded_args = [encode(arg) for arg in args]
    return subprocess.Popen(encoded_args, cwd=cwd, shell=shell).pid


def _fork_win32(args, cwd=None, shell=False):
    """Launch a background process using crazy win32 voodoo."""
    # This is probably wrong, but it works.  Windows.. wow.
    if args[0] == 'git-dag':
        # win32 can't exec python scripts
        args = [sys.executable] + args

    if not shell:
        args[0] = _win32_find_exe(args[0])

    if PY3:
        # see comment in start_command()
        argv = [decode(arg) for arg in args]
    else:
        argv = [encode(arg) for arg in args]

    DETACHED_PROCESS = 0x00000008  # Amazing!
    return subprocess.Popen(
        argv, cwd=cwd, creationflags=DETACHED_PROCESS, shell=shell
    ).pid


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
        candidates.extend([(exe + ext) for ext in extensions if ext.startswith('.')])
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


def _decorator_noop(x):
    return x


def wrap(action, fn, decorator=None):
    """Wrap arguments with `action`, optionally decorate the result"""
    if decorator is None:
        decorator = _decorator_noop

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        return decorator(fn(action(*args, **kwargs)))

    return wrapped


def decorate(decorator, fn):
    """Decorate the result of `fn` with `action`"""

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        return decorator(fn(*args, **kwargs))

    return decorated


def getenv(name, default=None):
    return decode(os.getenv(name, default))


def guess_mimetype(filename):
    """Robustly guess a filename's mimetype"""
    mimetype = None
    try:
        mimetype = mimetypes.guess_type(filename)[0]
    except UnicodeEncodeError:
        mimetype = mimetypes.guess_type(encode(filename))[0]
    except (TypeError, ValueError):
        mimetype = mimetypes.guess_type(decode(filename))[0]
    return mimetype


def xopen(path, mode='r', encoding=None):
    return open(mkpath(path, encoding=encoding), mode)


def print_stdout(msg, linesep='\n'):
    msg = msg + linesep
    if PY2:
        msg = encode(msg, encoding=ENCODING)
    sys.stdout.write(msg)


def print_stderr(msg, linesep='\n'):
    msg = msg + linesep
    if PY2:
        msg = encode(msg, encoding=ENCODING)
    sys.stderr.write(msg)


def error(msg, status=EXIT_FAILURE, linesep='\n'):
    print_stderr(msg, linesep=linesep)
    sys.exit(status)


@interruptable
def node():
    return platform.node()


abspath = wrap(mkpath, os.path.abspath, decorator=decode)
chdir = wrap(mkpath, os.chdir)
exists = wrap(mkpath, os.path.exists)
expanduser = wrap(encode, os.path.expanduser, decorator=decode)
if PY2:
    if hasattr(os, 'getcwdu'):
        # pylint: disable=no-member
        getcwd = os.getcwdu
    else:
        getcwd = decorate(decode, os.getcwd)
else:
    getcwd = os.getcwd


# NOTE: find_executable() is originally from the stdlib, but starting with
# python3.7 the stdlib no longer bundles distutils.
def _find_executable(executable, path=None):
    """Tries to find 'executable' in the directories listed in 'path'.

    A string listing directories separated by 'os.pathsep'; defaults to
    os.environ['PATH'].  Returns the complete filename or None if not found.
    """
    if path is None:
        path = os.environ['PATH']

    paths = path.split(os.pathsep)
    _, ext = os.path.splitext(executable)

    if (sys.platform == 'win32') and (ext != '.exe'):
        executable = executable + '.exe'

    if not os.path.isfile(executable):
        for p in paths:
            f = os.path.join(p, executable)
            if os.path.isfile(f):
                # the file exists, we have a shot at spawn working
                return f
        return None

    return executable


if PY2:
    find_executable = wrap(mkpath, _find_executable, decorator=decode)
else:
    find_executable = wrap(decode, _find_executable, decorator=decode)
isdir = wrap(mkpath, os.path.isdir)
isfile = wrap(mkpath, os.path.isfile)
islink = wrap(mkpath, os.path.islink)
makedirs = wrap(mkpath, os.makedirs)
try:
    readlink = wrap(mkpath, os.readlink, decorator=decode)
except AttributeError:

    def _readlink_noop(p):
        return p

    readlink = _readlink_noop

realpath = wrap(mkpath, os.path.realpath, decorator=decode)
relpath = wrap(mkpath, os.path.relpath, decorator=decode)
stat = wrap(mkpath, os.stat)
unlink = wrap(mkpath, os.unlink)
walk = wrap(mkpath, os.walk)
