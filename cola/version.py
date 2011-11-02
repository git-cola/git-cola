# Copyright (c) 2012 David Aguilar
"""Provide cola's version number"""

# The current git-cola version
_default_version = '1.7.0'


import os
import sys

if __name__ == '__main__':
    srcdir = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(1, srcdir)
    sys.path.insert(1, os.path.join(srcdir, 'thirdparty'))

from cola import git
from cola import errors
from cola import utils
from cola.decorators import memoize

# minimum version requirements
_versions = {
    # git-diff learned --patience in 1.6.2
    # git-mergetool learned --no-prompt in 1.6.2
    # git-difftool moved out of contrib in git 1.6.3
    'git': '1.6.3',
    'python': '2.4',
    'pyqt': '4.4',
    'pyqt_qrunnable': '4.4',
    'diff-submodule': '1.6.6',
}


def get(key):
    """Returns an entry from the known versions table"""
    return _versions.get(key)


class VersionUnavailable(Exception):
    pass


def git_describe_version():
    """Inspect the cola git repository and return the current version."""
    try:
        v = git.Git.execute(['git', 'describe',
                            '--tags',
                            '--match=v*',
                            '--abbrev=7',
                            'HEAD'],
                            with_stderr=True)
    except errors.GitCommandError, e:
        raise VersionUnavailable(str(e))
    if v[0:1] != 'v' or not v[1:2].isdigit():
        raise VersionUnavailable('%s: bad version' % v)
    try:
        dirty = git.Git.execute(['git', 'diff-index', '--name-only', 'HEAD'])
    except errors.GitCommandError, e:
        raise VersionUnavailable(str(e))
    if dirty:
        v += '-dirty'
    return utils.strip_prefix('v', v.replace('-', '.'))


def builtin_version():
    """Return the builtin version or throw a VersionUnavailable exception"""
    try:
        from cola import builtin_version as bv
    except ImportError, e:
        raise VersionUnavailable()
    else:
        return bv.version


@memoize
def _builtin_version_file(ext='py'):
    """Returns the path to cola's builtin_version.py."""
    dirname = os.path.dirname(__file__)
    return os.path.join(dirname, 'builtin_version.%s' % ext)


def release_version():
    """Return a version number for a release

    First see if there is a version file (included in release tarballs),
    then try git-describe, then default.

    """
    if os.path.isdir('.git'):
        try:
            return git_describe_version()
        except VersionUnavailable:
            pass
    return version()


def write_builtin_version():
    """Writes cola/builtin_version.py

    """
    v = release_version()
    f = file(_builtin_version_file(), 'w')
    f.write('# This file was generated automatically. Do not edit by hand.\n'
            'version = %r\n' % v)
    f.close()


def delete_builtin_version():
    """Deletes cola/builtin_version.py."""
    for ext in ('py', 'pyc', 'pyo'):
        fn = _builtin_version_file(ext=ext)
        if os.path.exists(fn):
            os.remove(fn)


@memoize
def version(vstr=_default_version):
    """Returns the builtin version or calculates the current version."""
    for v in [builtin_version, git_describe_version]:
        try:
            return v()
        except VersionUnavailable:
            pass
    return vstr


@memoize
def check_version(min_ver, ver):
    """Check whether ver is greater or equal to min_ver
    """
    min_ver_list = version_to_list(min_ver)
    ver_list = version_to_list(ver)
    return min_ver_list <= ver_list


@memoize
def check(key, ver):
    """Checks if a version is greater than the known version for <what>"""
    return check_version(get(key), ver)


def version_to_list(version):
    """Convert a version string to a list of numbers or strings
    """
    ver_list = []
    for p in version.split('.'):
        try:
            n = int(p)
        except ValueError:
            n = p
        ver_list.append(n)
    return ver_list


@memoize
def git_version():
    """Returns the current GIT version"""
    return git.instance().version().split()[-1]


if __name__ == '__main__':
    print(release_version())
