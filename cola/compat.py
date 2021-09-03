# pylint: disable=unused-import,redefined-builtin,undefined-variable
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys

try:
    import urllib2 as parse  # noqa
except ImportError:
    # Python 3
    from urllib import parse  # noqa


PY_VERSION = sys.version_info[:2]  # (2, 7)
PY_VERSION_MAJOR = PY_VERSION[0]
PY2 = PY_VERSION_MAJOR == 2
PY3 = PY_VERSION_MAJOR >= 3
PY26_PLUS = PY2 and sys.version_info[1] >= 6
WIN32 = sys.platform == 'win32' or sys.platform == 'cygwin'
ENCODING = 'utf-8'


if PY3:
    def bstr(x, encoding=ENCODING):
        return bytes(x, encoding=encoding)

elif PY26_PLUS:
    bstr = bytes
else:
    # Python <= 2.5
    bstr = str


if PY3:
    def bchr(i):
        return bytes([i])

    int_types = (int,)
    maxsize = sys.maxsize
    ustr = str
    uchr = chr
else:
    bchr = chr
    maxsize = 2 ** 31
    # pylint: disable=unicode-builtin
    ustr = unicode  # noqa
    # pylint: disable=unichr-builtin
    uchr = unichr  # noqa
    # pylint: disable=long-builtin
    int_types = (int, long)  # noqa

# Qt's max 32-bit signed integer range (-2147483648 to 2147483647)
maxint = (2 ** 31) - 1


def setenv(key, value):
    """Compatibility wrapper for setting environment variables

    Why?  win32 requires putenv().  UNIX only requires os.environ.
    """
    if not PY3 and isinstance(value, ustr):
        value = value.encode(ENCODING, 'replace')
    os.environ[key] = value
    os.putenv(key, value)


def unsetenv(key):
    """Compatibility wrapper for unsetting environment variables"""
    os.environ.pop(key, None)
    if hasattr(os, 'unsetenv'):
        os.unsetenv(key)


def no_op(value):
    """Return the value as-is"""
    return value


def byte_offset_to_int_converter():
    """Return a function to convert byte string offsets into ints

    Indexing into python3 bytes returns ints, Python2 returns str.
    Thus, on Python2 we need to use `ord()` to convert the byte into
    an integer.  It's already an int on Python3, so we use no_op there.
    """
    if PY2:
        result = ord
    else:
        result = no_op
    return result
