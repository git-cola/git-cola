# Developer wrapper script helper functions
import configparser
import datetime
import os
import sys


def activate():
    """Activate the cola development environment"""
    initialize_python()
    initialize_version()


def get_prefix():
    """Return the path to the source tree"""
    realpath = os.path.abspath(os.path.realpath(__file__))
    return os.path.dirname(os.path.dirname(realpath))


def initialize_python():
    """Add the source directory to the python sys.path."""
    sys.path.insert(1, get_prefix())


def initialize_version():
    """Replace version.SCM_VERSION when running from the source tree"""
    scm_version = get_version()
    if scm_version:
        # version.SCM_VERSION = version
        update_pkginfo_version(scm_version)


def get_version():
    """Calculate a setuptools-scm compatible version number from the git worktree"""
    from cola import git

    worktree = git.Git(worktree=get_prefix())
    if not worktree.is_valid():
        return None
    status, out, _ = worktree.describe(dirty=True, long=True, match='v[0-9]*.[0-9]*')
    if status != 0 or not out:
        return None
    # We cap the number of splits to 3 (4-parts) but only 2 splits (3-parts) are also
    # accepted. Anything less is not a "git describe" output we support.
    parts = out.lstrip('v').split('-', 3)
    num_parts = len(parts)
    if num_parts < 3:
        return None
    # If we are clean and we are pointing at a tag then setuptools-scm will report
    # just the version number without any extra version details.
    if num_parts == 3 and parts[1] == '0':
        return parts[0]

    # Transform v4.8.2-24-gd7b743a2 into 4.8.3.dev28+gd7b743a2
    # Transform v4.8.2-24-gd7b743a2-dirty into 4.8.3.dev28+gd7b743a2.d20241005
    numbers = parts[0].split('.')
    # Increment the last number.
    if numbers:
        try:
            last_number = f'{int(numbers[-1]) + 1}'
        except ValueError:
            last_number = '1'
        numbers[-1] = last_number
        parts[0] = '.'.join(numbers)

    version = f'{parts[0]}.dev{parts[1]}+{parts[2]}'
    # Worktree is dirty. Append the current date.
    if num_parts == 4:
        now = datetime.datetime.now()
        date_string = now.strftime('.d%Y%m%d')
        version += date_string

    return version


def update_pkginfo_version(scm_version):
    """Update git_cola.egg_info/PKG-INFO with the specified version"""
    from cola import version

    pkginfo = os.path.join(get_prefix(), 'git_cola.egg-info', 'PKG-INFO')
    content, pkginfo_version = get_pkginfo_version(pkginfo)
    # If there's nothing to update then we can set the SCM_VERSION.
    if not content or not pkginfo_version:
        version.SCM_VERSION = scm_version
        return
    # If the versions match then there's nothing to do.
    if scm_version == pkginfo_version:
        return
    # Rewrite the PKG-INFO file to reflect the current version.
    new_lines = []
    replaced = False
    token = 'Version: '
    new_version = f'Version: {scm_version}'
    for line in content.splitlines():
        if not replaced and line.startswith(token):
            new_lines.append(new_version)
            replaced = True
        else:
            new_lines.append(line)
    new_lines.append('')

    try:
        with open(pkginfo, 'w', encoding='utf-8') as pkginfo_file:
            pkginfo_file.write('\n'.join(new_lines))
    except OSError:
        pass


def get_pkginfo_version(pkginfo):
    """Return the version from the PKG-INFO file"""
    version = None
    content = None
    try:
        with open(pkginfo, encoding='utf-8') as pkginfo_file:
            content = pkginfo_file.read()
    except OSError:
        return (content, version)

    token = 'Version: '
    for line in content.splitlines():
        if line.startswith(token):
            version = line[len(token) :]
            break

    return (content, version)


activate()
