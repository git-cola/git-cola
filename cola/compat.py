from __future__ import absolute_import, division, unicode_literals
import os
import sys
try:
    import urllib2 as parse
except ImportError:
    # Python 3
    from urllib import parse


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3
PY26_PLUS = PY2 and sys.version_info[1] >= 6
WIN32 = sys.platform == 'win32' or sys.platform == 'cygwin'

if PY3:
    def bstr(x):
        # pylint: disable=bytes-builtin
        return bytes(x, encoding='utf8')
elif PY26_PLUS:
    # pylint: disable=bytes-builtin
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
    unichr = chr
else:
    bchr = chr
    maxsize = sys.maxint
    # pylint: disable=unicode-builtin
    ustr = unicode
    # pylint: disable=unichr-builtin
    unichr = unichr
    int_types = (int, long)  # pylint: disable=long-builtin


def setenv(key, value):
    """Compatibility wrapper for setting environment variables

    Why?  win32 requires putenv().  UNIX only requires os.environ.

    """
    if not PY3 and type(value) is ustr:
        value = value.encode('utf-8', 'replace')
    os.environ[key] = value
    os.putenv(key, value)


def unsetenv(key):
    """Compatibility wrapper for unsetting environment variables"""
    try:
        del os.environ[key]
    except:
        pass
    if hasattr(os, 'unsetenv'):
        os.unsetenv(key)
