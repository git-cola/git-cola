"""Provides the prefix() function for finding cola resources"""
from os.path import abspath
from os.path import dirname
from os.path import join

def path(*args):
    if 'site-packages' in __file__:
        # lib/python2.x/site-packages/cola/__file__.py
        prefix = dirname(dirname(dirname(dirname(dirname(abspath(__file__))))))
    else:
        # this is the source tree <src>/cola/__file__.py
        prefix = dirname(dirname(abspath(__file__)))
    return join(prefix, *args)
