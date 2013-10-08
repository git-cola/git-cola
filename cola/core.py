"""This module provides core functions for handling unicode and UNIX quirks

The @interruptable functions retry when system calls are interrupted,
e.g. when python raises an IOError or OSError with errno == EINTR.

"""
import os
import itertools

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
    if type(enc) is unicode:
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


abspath = wrap(encode, os.path.abspath, decorator=decode)
exists = wrap(encode, os.path.exists)
expanduser = wrap(encode, os.path.expanduser, decorator=decode)
getcwd = decorate(decode, os.getcwd)
isdir = wrap(encode, os.path.isdir)
isfile = wrap(encode, os.path.isfile)
islink = wrap(encode, os.path.islink)
makedirs = wrap(encode, os.makedirs)
readlink = wrap(encode, os.readlink, decorator=decode)
realpath = wrap(encode, os.path.realpath, decorator=decode)
stat = wrap(encode, os.stat)
unlink = wrap(encode, os.unlink)
