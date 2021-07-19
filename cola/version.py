"""Provide git-cola's version number"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys

if __name__ == '__main__':
    srcdir = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(1, srcdir)

from .git import STDOUT  # noqa
from .decorators import memoize  # noqa
from ._version import VERSION  # noqa

try:
    from ._build_version import BUILD_VERSION
except ImportError:
    BUILD_VERSION = ''

# minimum version requirements
_versions = {
    # git diff learned --patience in 1.6.2
    # git mergetool learned --no-prompt in 1.6.2
    # git difftool moved out of contrib in git 1.6.3
    'git': '1.6.3',
    'python': '2.6',
    # new: git cat-file --filters --path=<path> SHA1
    # old: git cat-file --filters blob SHA1:<path>
    'cat-file-filters-path': '2.11.0',
    # git diff --submodule was introduced in 1.6.6
    'diff-submodule': '1.6.6',
    # git check-ignore was introduced in 1.8.2, but did not follow the same
    # rules as git add and git status until 1.8.5
    'check-ignore': '1.8.5',
    # git push --force-with-lease
    'force-with-lease': '1.8.5',
    # git submodule update --recursive was introduced in 1.6.5
    'submodule-update-recursive': '1.6.5',
    # git include.path pseudo-variable was introduced in 1.7.10
    'config-includes': '1.7.10',
    # git for-each-ref --sort=version:refname
    'version-sort': '2.7.0',
    # Qt support for QT_AUTO_SCREEN_SCALE_FACTOR and QT_SCALE_FACTOR
    'qt-hidpi-scale': '5.6.0',
    # git rev-parse --show-superproject-working-tree was added in 2.13.0
    'show-superproject-working-tree': '2.13.0',
}


def get(key):
    """Returns an entry from the known versions table"""
    return _versions.get(key)


def version():
    """Returns the current version"""
    return VERSION


def build_version():
    """Return the build version, which includes the Git ID"""
    return BUILD_VERSION


@memoize
def check_version(min_ver, ver):
    """Check whether ver is greater or equal to min_ver"""
    min_ver_list = version_to_list(min_ver)
    ver_list = version_to_list(ver)
    return min_ver_list <= ver_list


@memoize
def check(key, ver):
    """Checks if a version is greater than the known version for <what>"""
    return check_version(get(key), ver)


def check_git(context, key):
    """Checks if Git has a specific feature"""
    return check(key, git_version(context))


def version_to_list(value):
    """Convert a version string to a list of numbers or strings"""
    ver_list = []
    for p in value.split('.'):
        try:
            n = int(p)
        except ValueError:
            n = p
        ver_list.append(n)
    return ver_list


@memoize
def git_version_str(context):
    """Returns the current GIT version"""
    git = context.git
    return git.version()[STDOUT].strip()


@memoize
def git_version(context):
    """Returns the current GIT version"""
    parts = git_version_str(context).split()
    if parts and len(parts) >= 3:
        result = parts[2]
    else:
        # minimum supported version
        result = '1.6.3'
    return result


def cola_version(build=False):
    if build:
        suffix = build_version() or version()
    else:
        suffix = version()
    return 'cola version %s' % suffix


def print_version(brief=False, build=False):
    if brief:
        if build:
            msg = build_version()
        else:
            msg = version()
    else:
        msg = cola_version(build=build)
    sys.stdout.write('%s\n' % msg)
