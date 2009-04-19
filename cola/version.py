# Copyright (c) 2008 David Aguilar
"""Provides the current cola version number"""

import re
import os
import sys

from cola import git
from cola import errors
from cola import utils

class VersionUnavailable(Exception):
    pass

def git_describe_version():
    """Inspect the cola git repository and return the current version."""
    path = sys.path[0]
    try:
        v = git.Git.execute(['git', 'describe', '--tags', '--abbrev=4'],
                            with_stderr=True)
    except errors.GitCommandError, e:
        raise VersionUnavailable(str(e))
    if not re.match(r'^v[0-9]', v):
        raise VersionUnavailable('%s: bad version' % v)
    try:
        dirty = git.Git.execute(['git', 'diff-index', '--name-only', 'HEAD'])
    except errors.GitCommandError, e:
        raise VersionUnavailable(str(e))
    if dirty:
        v += '-dirty'
    return re.sub('-', '.', utils.strip_prefix('v', v))

def builtin_version():
    """Return the builtin version or calculate it as needed."""
    try:
        import builtin_version as bv
    except ImportError:
        raise VersionUnavailable()
    else:
        return bv.version

def _builtin_version_file(ext = 'py'):
    """Returns the path to cola/builtin_version.py."""
    return os.path.join(sys.path[0], 'cola', 'builtin_version.%s' % ext)

def write_builtin_version():
    """Writes cola/builtin_version.py."""
    try:
        v = git_describe_version()
    except VersionUnavailable:
        return
    f = file(_builtin_version_file(), 'w')
    f.write('# This file was generated automatically. Do not edit by hand.\n'
            'version = %r\n' % v)

def delete_builtin_version():
    """Deletes cola/builtin_version.py."""
    for ext in ['py', 'pyc', 'pyo']:
        fn = _builtin_version_file(ext)
        if os.path.exists(fn):
            os.remove(fn)

# cached to avoid recalculation
_version = None

def get_version():
    """Returns the builtin version or calculates the current version."""
    global _version
    if _version:
        return _version
    for v in [builtin_version, git_describe_version]:
        try:
            _version = v()
        except VersionUnavailable:
            pass
    if not _version:
        _version = 'unknown-version'
    return _version


# minimum version requirements
git_min_ver = '1.5.2'
python_min_ver = '2.4'
pyqt_min_ver = '4.3'

# git-difftool moved out of contrib in git 1.6.3
git_difftool_min_ver = '1.6.3'
