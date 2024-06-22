"""Provide git-cola's version number"""
import sys

try:
    if sys.version_info < (3, 8):
        import importlib_metadata as metadata
    else:
        from importlib import metadata
except (ImportError, OSError):
    metadata = None

from .git import STDOUT
from .decorators import memoize
from ._version import VERSION

try:
    from ._scm_version import __version__ as SCM_VERSION
except ImportError:
    SCM_VERSION = None


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
    # git include.path pseudo-variable was introduced in 1.7.10.
    'config-includes': '1.7.10',
    # git config --show-scope was introduced in 2.26.0
    'config-show-scope': '2.26.0',
    # git config --show-origin was introduced in 2.8.0
    'config-show-origin': '2.8.0',
    # git for-each-ref --sort=version:refname
    'version-sort': '2.7.0',
    # Qt support for QT_AUTO_SCREEN_SCALE_FACTOR and QT_SCALE_FACTOR
    'qt-hidpi-scale': '5.6.0',
    # git rebase --rebase-merges was added in 2.18.0
    'rebase-merges': '2.18.0',
    # git rebase --update-refs was added in 2.38.0
    'rebase-update-refs': '2.38.0',
    # git rev-parse --show-superproject-working-tree was added in 2.13.0
    'show-superproject-working-tree': '2.13.0',
}


def get(key):
    """Returns an entry from the known versions table"""
    return _versions.get(key)


def version():
    """Returns the current version"""
    if SCM_VERSION:
        return SCM_VERSION

    pkg_version = VERSION
    if metadata is None:
        return pkg_version

    try:
        metadata_version = metadata.version('git-cola')
    except (ImportError, OSError):
        return pkg_version

    # Building from a tarball can end up reporting "0.0.0" or "0.1.dev*".
    # Use the fallback version in these scenarios.
    if not metadata_version.startswith('0.'):
        return metadata_version
    return pkg_version


def builtin_version():
    """Returns the version recorded in cola/_version.py"""
    return VERSION


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
    for part in value.split('.'):
        try:
            number = int(part)
        except ValueError:
            number = part
        ver_list.append(number)
    return ver_list


@memoize
def git_version_str(context):
    """Returns the current GIT version"""
    git = context.git
    return git.version(_readonly=True)[STDOUT].strip()


@memoize
def git_version(context):
    """Returns the current GIT version"""
    parts = git_version_str(context).split()
    if parts and len(parts) >= 3:
        result = parts[2]
    else:
        # minimum supported version
        result = get('git')
    return result


def cola_version(builtin=False):
    """A version string for consumption by humans"""
    if builtin:
        suffix = builtin_version()
    else:
        suffix = version()
    return 'cola version %s' % suffix


def print_version(builtin=False, brief=False):
    if builtin and brief:
        msg = builtin_version()
    elif brief:
        msg = version()
    else:
        msg = cola_version(builtin=builtin)
    print(msg)
