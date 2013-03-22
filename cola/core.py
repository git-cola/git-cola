"""This module provides core functions for handling unicode and UNIX quirks

The @interruptable functions retry when system calls are interrupted,
e.g. when python raises an IOError or OSError with errno == EINTR.

"""
import itertools

from cola.decorators import interruptable

from sys import getfilesystemencoding

# Some files are not in UTF-8; some other aren't in any codification.
# Remember that GIT doesn't care about encodings (saves binary data)
_encoding_tests = [
    getfilesystemencoding (),
    'utf-8',
    'iso-8859-15',
    'windows1252',
    'ascii',
    # <-- add encodings here
]


def decode(enc, encoding=None):
    """decode(encoded_string) returns an unencoded unicode string
    """
    if encoding is None:
        encoding_tests = _encoding_tests
    else:
        encoding_tests = itertools.chain([encoding], _encoding_tests)

    for encoding in encoding_tests:
        try:
            return unicode(enc.decode(encoding))
        except:
            pass
    # this shouldn't ever happen... FIXME
    return unicode(enc)


def encode(unenc, encoding=None):
    """encode(unencoded_string) returns a string encoded in utf-8
    """
    if encoding is None:
        encoding = 'utf-8'
    return unenc.encode(encoding, 'replace')


@interruptable
def read(fh, size=-1):
    """Read from a filehandle and retry when interrupted"""
    return fh.read(size)


@interruptable
def write(fh, content):
    """Write to a filehandle and retry when interrupted"""
    return fh.write(content)


@interruptable
def wait(proc):
    """Wait on a subprocess and retry when interrupted"""
    return proc.wait()


@interruptable
def readline(fh):
    return fh.readline()
