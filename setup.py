#!/usr/bin/env python

import os
import sys
from glob import glob
from distutils.core import setup

# Look for modules in the root
srcdir = os.path.dirname(os.path.abspath(__file__))

from extras import cmdclass

here = os.path.dirname(__file__)
version = os.path.join(here, 'cola', '_version.py')
scope = {}
exec(open(version).read(), scope)
version = scope['VERSION']


def main():
    """Runs distutils.setup()"""

    scripts = [
        'bin/git-cola',
        'bin/git-dag',
    ]

    if sys.platform == 'win32':
        scripts.append('contrib/win32/cola')

    setup(name='git-cola',
          version=version,
          description='The highly caffeinated git GUI',
          long_description='A sleek and powerful git GUI',
          license='GPLv2',
          author='David Aguilar',
          author_email='davvid@gmail.com',
          url='http://git-cola.github.io/',
          scripts=scripts,
          cmdclass=cmdclass,
          platforms='any',
          data_files = cola_data_files())

def cola_data_files():
    data = [
        _app_path('share/git-cola/bin', '*'),
        _app_path('share/git-cola/icons', '*.png'),
        _app_path('share/git-cola/icons', '*.svg'),
        _app_path('share/applications', '*.desktop'),
        _app_path('share/doc/git-cola', '*.txt'),
        _app_path('share/doc/git-cola', '*.html'),
        _package('cola'),
        _package('cola.models'),
        _package('cola.widgets'),
    ]

    data.extend([_app_path(localedir, 'git-cola.mo')
                 for localedir in glob('share/locale/*/LC_MESSAGES')])
    return data


def _package(package, subdir=None):
    subdirs = package.split('.')
    app_dir = os.path.join('share', 'git-cola', 'lib', *subdirs)
    if subdir:
        subdirs.insert(0, subdir)
    src_dir = os.path.join(*subdirs)
    return (app_dir, glob(os.path.join(src_dir, '*.py')))


def _app_path(dirname, entry):
    return (dirname, glob(os.path.join(dirname, entry)))


if __name__ == '__main__':
    main()
