# pylint: disable=unused-import,redefined-builtin
from __future__ import absolute_import, division, unicode_literals
import os
import sys
try:
    import urllib2 as parse  # noqa
except ImportError:
    # Python 3
    from urllib import parse  # noqa

try:
    # Python 2.7+
    from collections import OrderedDict as odict  # noqa
except ImportError:
    from .ordered_dict import OrderedDict as odict  # noqa


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3
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
    unichr = chr
else:
    bchr = chr
    maxsize = 2 ** 31
    # pylint: disable=unicode-builtin
    ustr = unicode  # noqa
    # pylint: disable=unichr-builtin
    unichr = unichr
    # pylint: disable=long-builtin
    int_types = (int, long)  # noqa


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
    try:
        del os.environ[key]
    except KeyError:
        pass
    if hasattr(os, 'unsetenv'):
        os.unsetenv(key)
