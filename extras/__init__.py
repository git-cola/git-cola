from __future__ import absolute_import, division, print_function, unicode_literals

try:
    from setuptools.command.build import build as build_base
except ImportError:
    try:
        from setuptools._distutils.command.build import build as build_base
    except ImportError:
        from distutils.command.build import build as build_base
