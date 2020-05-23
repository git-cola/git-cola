#!/usr/bin/env python
# git-cola installer
# usage: use the Makefile instead of invoking this script directly.
# pylint: disable=import-error,no-name-in-module
from __future__ import absolute_import, division, unicode_literals
from glob import glob
from distutils.command import build_scripts
from distutils.core import setup
import os
import re
import sys

from extras import cmdclass
from extras import build_helpers

# Hack: prevent python2's ascii default encoding from breaking inside
# distutils when installing from utf-8 paths.
if sys.version_info[0] < 3:
    # pylint: disable=reload-builtin,undefined-variable
    reload(sys)  # noqa
    # pylint: disable=no-member
    sys.setdefaultencoding('utf-8')

# Prevent distuils from changing "#!/usr/bin/env python" when
# --use-env-python is specified.
try:
    sys.argv.remove('--use-env-python')
    use_env_python = True
except ValueError:
    use_env_python = False
if use_env_python:
    build_scripts.first_line_re = re.compile(r'^should not match$')

# Disable vendoring of qtpy and friends by passing --no-vendor-libs
try:
    sys.argv.remove('--no-vendor-libs')
    vendor_libs = False
except ValueError:
    vendor_libs = not os.getenv('GIT_COLA_NO_VENDOR_LIBS', '')

here = os.path.dirname(__file__)
version = os.path.join(here, 'cola', '_version.py')
scope = {}
exec(open(version).read(), scope)  # pylint: disable=exec-used
version = scope['VERSION']


def main():
    """Runs distutils.setup()"""
    scripts = [
        'bin/git-cola',
        'bin/git-dag',
    ]

    if sys.platform == 'win32':
        scripts.append('contrib/win32/cola')

    # Helper scripts are installed to share/git-cola/bin and are visible to
    # git-cola only.  Adding scripts to build_helpers.scripts will make them
    # available for #! updating.
    build_helpers.helpers = [
        'share/git-cola/bin/git-xbase',
    ]

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
        _app_path('share/appdata', '*.xml'),
        _app_path('share/applications', '*.desktop'),
        _app_path('share/doc/git-cola', '*.rst'),
        _app_path('share/doc/git-cola', '*.html'),
        _package('cola'),
        _package('cola.models'),
        _package('cola.widgets'),
    ]

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
