"""Provides the prefix() function for finding cola resources"""
import os
import glob

_modpath = os.path.abspath(__file__)
if 'share' in __file__ and 'lib' in __file__:
    # this is the release tree
    # __file__ = '$prefix/share/git-cola/lib/cola/__file__.py'
    _lib_dir = os.path.dirname(os.path.dirname(_modpath))
    _prefix = os.path.dirname(os.path.dirname(os.path.dirname(_lib_dir)))
else:
    # this is the source tree
    # __file__ = '$prefix/cola/__file__.py'
    _prefix = os.path.dirname(os.path.dirname(_modpath))


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
    if os.path.exists(htmldocs):
        return htmldocs
    return doc('git-cola.txt')


def share(*args):
    """Return a path relative to cola's /usr/share/ directory"""
    return prefix('share', 'git-cola', *args)


def icon(basename):
    """Return the full path to an icon file given a basename."""
    return 'icons:'+basename


def icon_dir():
    """Return the path to the style dir within the cola install tree."""
    return share('icons')
