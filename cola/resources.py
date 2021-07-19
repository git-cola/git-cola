"""Functions for finding cola resources"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os
from os.path import dirname
import webbrowser

from . import core
from . import compat


# Default git-cola icon theme
_default_icon_theme = 'light'

_modpath = core.abspath(core.realpath(__file__))
if (
    os.path.join('share', 'git-cola', 'lib') in _modpath
    or os.path.join('site-packages', 'cola') in _modpath
):
    # this is the release tree
    # __file__ = '$prefix/share/git-cola/lib/cola/__file__.py'
    _lib_dir = dirname(dirname(_modpath))
    _prefix = dirname(dirname(dirname(_lib_dir)))
elif os.path.join('pkgs', 'cola') in _modpath:
    # Windows release tree
    # __file__ = $installdir/pkgs/cola/resources.py
    _prefix = dirname(dirname(dirname(_modpath)))
else:
    # this is the source tree
    # __file__ = '$prefix/cola/__file__.py'
    _prefix = dirname(dirname(_modpath))


def get_prefix():
    """Return the installation prefix"""
    return _prefix


def prefix(*args):
    """Return a path relative to cola's installation prefix"""
    return os.path.join(get_prefix(), *args)


def command(name):
    """Return a command from the bin/ directory"""
    if compat.WIN32:
        # Check for "${name}.exe" on Windows.
        path = prefix('bin', name)
        exe_path = prefix('bin', '%s.exe' % name)
        if core.exists(exe_path):
            result = exe_path
        else:
            result = path
    else:
        result = prefix('bin', name)
    return result


def doc(*args):
    """Return a path relative to cola's /usr/share/doc/ directory"""
    return os.path.join(_prefix, 'share', 'doc', 'git-cola', *args)


def html_docs():
    """Return the path to the cola html documentation."""
    # html/index.html only exists after the install-docs target is run.
    # Fallback to the source tree and lastly git-cola.rst.
    paths_to_try = (('html', 'index.html'), ('_build', 'html', 'index.html'))
    for paths in paths_to_try:
        docdir = doc(*paths)
        if core.exists(docdir):
            return docdir
    return doc('git-cola.rst')


def show_html_docs():
    url = html_docs()
    webbrowser.open_new_tab('file://' + url)


def share(*args):
    """Return a path relative to cola's /usr/share/ directory"""
    return prefix('share', 'git-cola', *args)


def icon_dir(theme):
    """Return the path to the icons directory

    This typically returns share/git-cola/icons within
    the git-cola installation prefix.

    When theme is defined then it will return a subdirectory of the icons/
    directory, e.g. "dark" for the dark icon theme.

    When theme is set to an absolute directory path, that directory will be
    returned, which effectively makes git-cola use those icons.

    """

    if not theme or theme == _default_icon_theme:
        icons = share('icons')
    else:
        theme_dir = share('icons', theme)
        if os.path.isabs(theme) and os.path.isdir(theme):
            icons = theme
        elif os.path.isdir(theme_dir):
            icons = theme_dir
        else:
            icons = share('icons')

    return icons


def config_home(*args):
    config = core.getenv(
        'XDG_CONFIG_HOME', os.path.join(core.expanduser('~'), '.config')
    )
    return os.path.join(config, 'git-cola', *args)
