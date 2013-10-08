import os
from cola import core
try:
    set = set
except NameError:
    from sets import Set as set
    set = set

try:
    import hashlib
except ImportError:
    import md5
    class hashlib(object):
        @staticmethod
        def new(*args):
            return md5.new()

        @classmethod
        def md5(cls, value=''):
            obj = md5.new()
            obj.update(value)
            return obj




def setenv(key, value):
    """Compatibility wrapper for setting environment variables

    Why?  win32 requires putenv().  UNIX only requires os.environ.

    """
    os.environ[key] = core.encode(value)
    os.putenv(key, core.encode(value))


def unsetenv(key):
    """Compatibility wrapper for unsetting environment variables"""
    try:
        del os.environment[key]
    except:
        pass
    if hasattr(os, 'unsetenv'):
        os.unsetenv(key)
