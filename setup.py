#!/usr/bin/env python
import re
import os
import sys
import stat
from glob import glob

from distutils.core import setup
from distutils.command import build_scripts

# Prevent distuils from changing "#!/usr/bin/env python"
build_scripts.first_line_re = re.compile('^should not match$')

# Look for modules in the root and thirdparty directories
srcdir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(srcdir, 'thirdparty'))
sys.path.insert(0, srcdir)

from cola import version
from cola import utils
from cola import resources
from cola import core

# --standalone prevents installing thirdparty libraries
if '--standalone' in sys.argv:
    sys.argv.remove('--standalone')
    _standalone = True
else:
    _standalone = False


def main():
    # ensure readable files
    old_mask = os.umask(0022)
    if sys.argv[1] in ('install', 'build'):
        _setup_environment()
        _check_python_version()
        _check_git_version()
        _check_pyqt_version()
        _build_translations()      # msgfmt: .po -> .qm

    # First see if there is a version file (included in release tarballs),
    # then try git-describe, then default.
    builtin_version = os.path.join('cola', 'builtin_version.py')
    if os.path.exists('version') and not os.path.exists(builtin_version):
        shutils.copy('version', builtin_version)

    elif os.path.exists('.git'):
        version.write_builtin_version()

    _run_setup()
    # restore the old mask
    os.umask(old_mask)

def _setup_environment():
    """Adds win32/ to our path for windows only"""
    if sys.platform != 'win32':
        return
    path = os.environ['PATH']
    win32 = os.path.join(srcdir, 'win32')
    os.environ['PATH'] = win32 + os.pathsep + path

def _run_setup():
    """Runs distutils.setup()"""

    scripts = ['bin/git-cola']

    # git-difftool first moved out of git.git's contrib area in git 1.6.3
    if (os.environ.get('INSTALL_GIT_DIFFTOOL', '') or
            not version.check('difftool-builtin', version.git_version())):
        scripts.append('bin/difftool/git-difftool')
        scripts.append('bin/difftool/git-difftool--helper')

    if sys.platform == 'win32':
        scripts.append('win32/cola')
        scripts.append('win32/dirname')
        scripts.append('win32/py2exe-setup.py')
        scripts.append('win32/py2exe-setup.cmd')

    setup(name = 'git-cola',
          version = version.version(),
          license = 'GPLv2',
          author = 'David Aguilar and contributors',
          author_email = 'davvid@gmail.com',
          url = 'http://cola.tuxfamily.org/',
          description = 'git-cola',
          long_description = 'A highly caffeinated git GUI',
          scripts = scripts,
          packages = [],
          data_files = cola_data_files())


def cola_data_files(standalone=_standalone):
    data = [_app_path('share/git-cola/qm', '*.qm'),
            _app_path('share/git-cola/icons', '*.png'),
            _app_path('share/git-cola/icons', '*.svg'),
            _app_path('share/git-cola/styles', '*.qss'),
            _app_path('share/git-cola/styles/images', '*.png'),
            _app_path('share/applications', '*.desktop'),
            _app_path('share/doc/git-cola', '*.txt'),
            _package('cola'),
            _package('cola.models'),
            _package('cola.controllers'),
            _package('cola.views')]

    if not standalone:
        data.extend([_thirdparty_package('jsonpickle'),
                     _thirdparty_package('simplejson')])

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


def _thirdparty_package(package):
    return _package(package, subdir='thirdparty')


def _app_path(dirname, entry):
    return (dirname, glob(os.path.join(dirname, entry)))


def _check_python_version():
    """Check the minimum Python version
    """
    pyver = '.'.join(map(lambda x: str(x), sys.version_info))
    if not version.check('python', pyver):
        print >> sys.stderr, ('Python version %s or newer required.  '
                              'Found %s' % (version.get('python'), pyver))
        sys.exit(1)


def _check_git_version():
    """Check the minimum GIT version
    """
    if not version.check('git', version.git_version()):
        print >> sys.stderr, ('GIT version %s or newer required.  '
                              'Found %s' % (version.get('git'),
                                            version.git_version()))
        sys.exit(1)

def _check_pyqt_version():
    """Check the minimum PyQt version
    """
    has_pyqt = False
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


def _dirty(src, dst):
    if not os.path.exists(dst):
        return True
    srcstat = os.stat(src)
    dststat = os.stat(dst)
    return srcstat[stat.ST_MTIME] > dststat[stat.ST_MTIME]


def _build_translations():
    print 'running build_translations'
    sources = glob(resources.share('po', '*.po'))
    sources = glob('share/git-cola/po/*.po')
    for src in sources:
        dst = resources.qm(os.path.basename(src)[:-3])
        if _dirty(src, dst):
            print '\tmsgfmt --qt %s -o %s' % (src, dst)
            utils.run_cmd(['msgfmt', '--qt', src, '-o', dst])


if __name__ == '__main__':
    main()
