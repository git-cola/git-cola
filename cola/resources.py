"""Provides the prefix() function for finding cola resources"""
from os.path import abspath
from os.path import dirname
from os.path import join

def path(*args):
    if 'site-packages' in __file__:
        # this is the release tree
        # __file__ = '$prefix/lib/python2.x/site-packages/cola/__file__.py'
        prefix = dirname(dirname(dirname(dirname(dirname(abspath(__file__))))))
    else:
        # this is the source tree
        # __file__ = '$prefix/cola/__file__.py'
        prefix = dirname(dirname(abspath(__file__)))
    return join(prefix, *args)
