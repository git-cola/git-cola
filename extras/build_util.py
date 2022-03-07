from __future__ import absolute_import, division, print_function, unicode_literals
import os
try:
    from shutil import which
except ImportError:
    from distutils.spawn import find_executable as which


def encode(string):
    try:
        result = string.encode('utf-8')
    except (ValueError, UnicodeEncodeError):
        result = string
    return result


def make_string(x):
    if x:
        x = str(x)
    return x


def stringify_options(items):
    return [[make_string(x) for x in i] for i in items]


def stringify_list(items):
    return [make_string(i) for i in items]


def newer(a, b):
    """Return True if a is newer than b"""
    try:
        stat_a = os.stat(a)
        stat_b = os.stat(b)
    except OSError:
        return True
    return stat_a.st_mtime >= stat_b.st_mtime
