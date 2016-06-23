from __future__ import absolute_import, division, unicode_literals

import os
import sys


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3
WIN32 = sys.platform == 'win32' or sys.platform == 'cygwin'

try:
    # pylint: disable=unicode-builtin
    ustr = unicode
except NameError:
    # Python 3
    ustr = str

try:
    # pylint: disable=unichr-builtin
    unichr = unichr
except NameError:
    # Python 3
    unichr = chr


def _bchr_py3(i):
    return bytes([i])


if PY3:
    bchr = _bchr_py3
else:
    bchr = chr

if PY3:
    int_types = (int,)
else:
    int_types = (int, long)  # pylint: disable=long-builtin

try:
    import urllib2 as parse
except ImportError:
    # Python 3
    from urllib import parse


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
