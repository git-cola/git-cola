"""This module provides core functions for handling unicode and UNIX quirks

The @interruptable functions retry when system calls are interrupted,
e.g. when python raises an IOError or OSError with errno == EINTR.

"""
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

def decode(enc):
    """decode(encoded_string) returns an unencoded unicode string
    """
    for encoding in _encoding_tests:
        try:
            return unicode(enc.decode(encoding))
        except:
            pass
    # this shouldn't ever happen... FIXME
    return unicode(enc)


def encode(unenc):
    """encode(unencoded_string) returns a string encoded in utf-8
    """
    return unenc.encode('utf-8', 'replace')


@interruptable
def read(fh):
    """Read from a filehandle and retry when interrupted"""
    return fh.read()


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
