import os
from cola import core

def setenv(key, value):
    """Compatibility wrapper for setting environment variables

    Why?  win32 requires putenv().  UNIX only requires os.environ.

    """
    os.environ[key] = core.encode(value)
    os.putenv(key, core.encode(value))


def unsetenv(key):
    """Compatibility wrapper for unsetting environment variables"""
    try:
        del os.environ[key]
    except:
        pass
    if hasattr(os, 'unsetenv'):
        os.unsetenv(key)
