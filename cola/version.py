# Copyright (c) David Aguilar
"""Provide git-cola's version number"""

# The current git-cola version
_default_version = '1.8.3.rc1'


import os
import sys

if __name__ == '__main__':
    srcdir = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(1, srcdir)

from cola.git import git
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


def version():
    """Returns the current version"""
    return _default_version


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
def git_version_str():
    """Returns the current GIT version"""
    return git.version().strip()

@memoize
def git_version():
    """Returns the current GIT version"""
    parts = git_version_str().split()
    if parts and len(parts) > 2:
        return parts[2]
    else:
        return 'v1.6.3' # minimum supported version


if __name__ == '__main__':
    print(version())
