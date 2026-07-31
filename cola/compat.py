import os
import sys
from typing import Any

try:
    import urllib2 as parse  # noqa
except ImportError:
    # Python 3
    from urllib import parse  # noqa


PY_VERSION = sys.version_info[:2]  # (2, 7)
PY_VERSION_MAJOR = PY_VERSION[0]
PY2: bool = PY_VERSION_MAJOR == 2
PY3 = PY_VERSION_MAJOR >= 3
PY26_PLUS = PY2 and sys.version_info[1] >= 6
WIN32 = sys.platform in {'win32', 'cygwin'}
ENCODING = 'utf-8'


if PY3:

    def bstr(value, encoding=ENCODING):
        return bytes(value, encoding=encoding)

elif PY26_PLUS:
    bstr = bytes
else:
    # Python <= 2.5
    bstr = str


if PY3:

    def bchr(i: int) -> bytes:
        return bytes([i])

    int_types = (int,)
    maxsize = sys.maxsize
    ustr = str
else:
    bchr = chr
    maxsize = 2**31
    ustr = unicode  # noqa
    int_types = (int, long)  # noqa

# The max 32-bit signed integer range for Qt is (-2147483648 to 2147483647)
maxint = (2**31) - 1


def setenv(key: str, value: str) -> None:
    """Compatibility wrapper for setting environment variables

    Windows requires putenv(). Unix only requires os.environ.
    """
    if not PY3 and isinstance(value, ustr):
        value = value.encode(ENCODING, 'replace')
    os.environ[key] = value
    os.putenv(key, value)


def unsetenv(key: str) -> None:
    """Compatibility wrapper for clearing environment variables"""
    os.environ.pop(key, None)
    if hasattr(os, 'unsetenv'):
        os.unsetenv(key)


def no_op(value: Any) -> Any:
    """Return the value as-is"""
    return value


def byte_offset_to_int_converter():
    """Return a function to convert byte string offsets into integers

    Indexing into python3 bytes returns integers. Python2 returns str.
    Thus, on Python2 we need to use `ord()` to convert the byte into
    an integer.  It's already an int on Python3, so we use no_op there.
    """
    if PY2:
        result = ord
    else:
        result = no_op
    return result


# git-fanta was renamed from git-cola. Umgebungsvariablen heissen jetzt GIT_FANTA_*,
# die alten GIT_FANTA_*-Namen bleiben als Fallback wirksam.
_LEGACY_ENV_PREFIX = 'GIT_COLA_'
_ENV_PREFIX = 'GIT_FANTA_'


def legacy_env_name(name):
    """Return the pre-rename name of a GIT_FANTA_* variable, or None"""
    if name.startswith(_ENV_PREFIX):
        return _LEGACY_ENV_PREFIX + name[len(_ENV_PREFIX) :]
    return None


def getenv_with_legacy(name, default=None):
    """Read an environment variable, falling back to its pre-rename name"""
    value = os.getenv(name)
    if value is not None:
        return value
    legacy = legacy_env_name(name)
    if legacy is not None:
        value = os.getenv(legacy)
        if value is not None:
            return value
    return default
