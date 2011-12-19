#!/usr/bin/env python

import os
import sys
import platform
from glob import glob
from distutils.core import setup

# Look for modules in the root
srcdir = os.path.dirname(os.path.abspath(__file__))

from extras import cmdclass
from cola import version


def main():
    _check_python_version()
    _setup_environment()
    _check_git_version()
    _check_pyqt_version()
    _run_setup()


def _check_python_version():
    """Check the minimum Python version
    """
    pyver = platform.python_version()
    if not version.check('python', pyver):
        print >> sys.stderr, ('Python version %s or newer required.  '
                              'Found %s' % (version.get('python'), pyver))
        sys.exit(1)


def _setup_environment():
    """Adds win32/ to our path for windows only"""
    if sys.platform != 'win32':
        return
    path = os.environ['PATH']
    win32 = os.path.join(srcdir, 'win32')
    os.environ['PATH'] = win32 + os.pathsep + path


def _check_git_version():
    """Check the minimum GIT version
    """
    git_version = version.git_version()
    if not version.check('git', git_version):
        print >> sys.stderr, ('GIT version %s or newer required.  '
                              'Found %s' % (version.get('git'), git_version))
        sys.exit(1)


def _check_pyqt_version():
    """Check the minimum PyQt version
    """
    pyqtver = 'None'
    try:
        from PyQt4 import QtCore
        pyqtver = QtCore.PYQT_VERSION_STR
        if version.check('pyqt', pyqtver):
            return
    except ImportError:
        pass
    print >> sys.stderr, ('PyQt4 version %s or newer required.  '
                          'Found %s' % (version.get('pyqt'), pyqtver))
    sys.exit(1)


def _run_setup():
    """Runs distutils.setup()"""

    scripts = [
        'bin/git-cola',
        'bin/git-dag',
    ]

    if sys.platform == 'win32':
        scripts.extend([
                'win32/cola',
                'win32/dirname',
                'win32/py2exe-setup.py',
                'win32/py2exe-setup.cmd',
        ])

    setup(name = 'git-cola',
          version = version.version(),
          description = 'The highly caffeinated git GUI',
          license = 'GPLv2',
          author = 'The git-cola community',
          author_email = 'git-cola@googlegroups.com',
          url = 'http://git-cola.github.com/',
          long_description = 'A sleek and powerful git GUI',
          scripts = scripts,
          cmdclass = cmdclass,
          data_files = cola_data_files())


def cola_data_files():
    data = [
        _app_path('share/git-cola/icons', '*.png'),
        _app_path('share/git-cola/icons', '*.svg'),
        _app_path('share/applications', '*.desktop'),
        _app_path('share/doc/git-cola', '*.txt'),
        _app_path('share/doc/git-cola', '*.html'),
        _package('cola'),
        _package('cola.classic'),
        _package('cola.dag'),
        _package('cola.main'),
        _package('cola.merge'),
        _package('cola.models'),
        _package('cola.prefs'),
        _package('cola.stash'),
        _package('cola.widgets'),
    ]

    data.extend([_app_path(localedir, 'git-cola.mo')
                 for localedir in glob('share/locale/*/LC_MESSAGES')])

    if sys.platform == 'darwin':
        data.append(_app_path('share/git-cola/bin', 'ssh-askpass-darwin'))
    else:
        data.append(_app_path('share/git-cola/bin', 'ssh-askpass'))
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
