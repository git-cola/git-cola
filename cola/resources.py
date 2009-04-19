"""Provides the prefix() function for finding cola resources"""
import os

_modpath = os.path.abspath(__file__)
if 'share' in __file__ and 'lib' in __file__:
    # this is the release tree
    # __file__ = '$prefix/share/cola/lib/cola/__file__.py'
    _lib_dir = os.path.dirname(os.path.dirname(_modpath))
    _prefix = os.path.dirname(os.path.dirname(os.path.dirname(_lib_dir)))
else:
    # this is the source tree
    # __file__ = '$prefix/cola/__file__.py'
    _prefix = os.path.dirname(os.path.dirname(_modpath))

def path(*args):
    return os.path.join(_prefix, *args)
