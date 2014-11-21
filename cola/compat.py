import os
import sys


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3
WIN32 = sys.platform == 'win32' or sys.platform == 'cygwin'

try:
    ustr = unicode
except NameError:
    # Python 3
    ustr = str

try:
    unichr = unichr
except NameError:
    # Python 3
    unichr = chr

try:
    # Python 3
    from urllib import parse
    urllib = parse
except ImportError:
    import urllib


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
