#!/usr/bin/env python
# usage: use the Makefile instead of invoking this script directly.
# pylint: disable=import-error,no-name-in-module
from __future__ import absolute_import, division, print_function, unicode_literals
from glob import glob
from distutils.command import build_scripts
from distutils.core import setup
import os
import re
import sys

sys.path.insert(1, os.path.dirname(__file__))
from extras import cmdclass

# Hack: prevent python2's ascii default encoding from breaking inside
# distutils when installing from utf-8 paths.
if sys.version_info[0] < 3:
    # pylint: disable=reload-builtin,undefined-variable
    reload(sys)  # noqa
    # pylint: disable=no-member
    sys.setdefaultencoding('utf-8')

# Prevent distutils from changing "#!/usr/bin/env python" when
# --use-env-python is specified.
try:
    sys.argv.remove('--use-env-python')
    use_env_python = True
except ValueError:
    use_env_python = False
if use_env_python:
    if sys.version_info[0] < 3:
        # Python2 accepts the r'' unicode literal.
        pattern = re.compile(r'^should not match$')
    else:
        # Python3 reads files as bytes and requires that the regex pattern is
        # specified as bytes.
        pattern = re.compile(b'^should not match$')
    build_scripts.first_line_re = pattern

# Disable installation of the private cola package by passing --no-private-libs or
# by setting GIT_COLA_NO_PRIVATE_LIBS=1 in th environment.
try:
    sys.argv.remove('--no-private-libs')
    private_libs = False
except ValueError:
    private_libs = not os.getenv('GIT_COLA_NO_PRIVATE_LIBS', '')

# Disable vendoring of qtpy and friends by passing --no-vendor-libs to setup.py or
# by setting GIT_COLA_NO_VENDOR_LIBS=1 in the environment.
try:
    sys.argv.remove('--no-vendor-libs')
    vendor_libs = False
except ValueError:
    vendor_libs = not os.getenv('GIT_COLA_NO_VENDOR_LIBS', '')

# fmt: off
here = os.path.dirname(__file__)
version = os.path.join(here, 'cola', '_version.py')
scope = {}
# flake8: noqa
exec(open(version).read(), scope)  # pylint: disable=exec-used
version = scope['VERSION']
# fmt: on


def main():
    """Runs distutils.setup()"""
    scripts = [
        'bin/git-cola',
        'bin/git-cola-sequence-editor',
        'bin/git-dag',
    ]

    if sys.platform == 'win32':
        scripts.append('contrib/win32/cola')

    packages = [str('cola'), str('cola.models'), str('cola.widgets')]

    setup(
        name='git-cola',
        version=version,
        description='The highly caffeinated git GUI',
        long_description='A sleek and powerful git GUI',
        license='GPLv2',
        author='David Aguilar',
        author_email='davvid@gmail.com',
        url='https://git-cola.github.io/',
        scripts=scripts,
        cmdclass=cmdclass,
        packages=packages,
        platforms='any',
        data_files=_data_files(),
    )


def _data_files():
    """Return the list of data files"""
    data = [
        _app_path('share/git-cola/bin', '*'),
        _app_path('share/git-cola/icons', '*.png'),
        _app_path('share/git-cola/icons', '*.svg'),
        _app_path('share/git-cola/icons/dark', '*.png'),
        _app_path('share/git-cola/icons/dark', '*.svg'),
        _app_path('share/metainfo', '*.xml'),
        _app_path('share/applications', '*.desktop'),
        _app_path('share/doc/git-cola', '*.rst'),
        _app_path('share/doc/git-cola', '*.html'),
    ]

    if private_libs:
        data.extend(
            [_package('cola'), _package('cola.models'), _package('cola.widgets')]
        )

    if vendor_libs:
        data.extend([_package('qtpy'), _package('qtpy._patch')])

    data.extend(
        [
            _app_path(localedir, 'git-cola.mo')
            for localedir in glob('share/locale/*/LC_MESSAGES')
        ]
    )
    return data


def _package(package, subdirs=None):
    """Collect python files for a given python "package" name"""
    dirs = package.split('.')
    app_dir = _lib_path(*dirs)
    if subdirs:
        dirs = list(subdirs) + dirs
    src_dir = os.path.join(*dirs)
    return (app_dir, glob(os.path.join(src_dir, '*.py')))


def _lib_path(*dirs):
    return os.path.join('share', 'git-cola', 'lib', *dirs)


def _app_path(dirname, entry):
    """Construct (dirname, [glob-expanded-entries relative to dirname])"""
    return (dirname, glob(os.path.join(dirname, entry)))


if __name__ == '__main__':
    main()
