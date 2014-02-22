"""Provides the prefix() function for finding cola resources"""
from __future__ import division, absolute_import

import os
import webbrowser
from os.path import dirname

from cola import core


_modpath = core.abspath(__file__)
if os.path.join('share', 'git-cola', 'lib') in _modpath:
    # this is the release tree
    # __file__ = '$prefix/share/git-cola/lib/cola/__file__.py'
    _lib_dir = dirname(dirname(_modpath))
    _prefix = dirname(dirname(dirname(_lib_dir)))
else:
    # this is the source tree
    # __file__ = '$prefix/cola/__file__.py'
    _prefix = dirname(dirname(_modpath))


def prefix(*args):
    """Return a path relative to cola's installation prefix"""
    return os.path.join(_prefix, *args)


def doc(*args):
    """Return a path relative to cola's /usr/share/doc/ directory"""
    return os.path.join(_prefix, 'share', 'doc', 'git-cola', *args)


def html_docs():
    """Return the path to the cola html documentation."""
    # index.html only exists after the install-docs target is run,
    # so fallback to git-cola.txt.
    htmldocs = doc('html', 'index.html')
    if core.exists(htmldocs):
        return htmldocs
    return doc('git-cola.txt')


def show_html_docs():
    url = html_docs()
    webbrowser.open_new_tab(url)

def share(*args):
    """Return a path relative to cola's /usr/share/ directory"""
    return prefix('share', 'git-cola', *args)


def icon(basename):
    """Return the full path to an icon file given a basename."""
    return 'icons:'+basename


def icon_dir():
    """Return the path to the style dir within the cola install tree."""
    return share('icons')


def config_home(*args):
    config = core.getenv('XDG_CONFIG_HOME',
                         os.path.join(core.expanduser('~'), '.config'))
    return os.path.join(config, 'git-cola', *args)
