#!/usr/bin/env python
import re
import os
import sys
import stat
from glob import glob

from distutils.core import setup
from distutils.command import build_scripts
build_scripts.first_line_re = re.compile('^should not match$')

from cola import version
from cola import utils
from cola import core

def main():
    # ensure readable files
    old_mask = os.umask(0022)
    if sys.argv[1] in ['install', 'build']:
        _setup_environment()
        _check_python_version()
        _check_git_version()
        _check_pyqt_version()
        _build_views()             # pyuic4: .ui -> .py
        _build_translations()      # msgfmt: .po -> .qm
    try:
        version.write_builtin_version()
        _run_setup()
    finally:
        version.delete_builtin_version()
    # restore the old mask
    os.umask(old_mask)

def _setup_environment():
    if sys.platform != 'win32':
        return
    path = os.environ['PATH']
    win32 = os.path.join(os.path.dirname(__file__), 'win32')
    os.environ['PATH'] = win32 + os.pathsep + path

def _run_setup():

    scripts = ['bin/git-cola', 'bin/git-difftool', 'bin/git-difftool-helper']
    if sys.platform == 'win32':
        scripts.append('win32/cola')
        scripts.append('win32/dirname')
        scripts.append('win32/py2exe-setup.py')
        scripts.append('win32/py2exe-setup.cmd')

    setup(name = 'git-cola',
          version = version.get_version(),
          license = 'GPLv2',
          author = 'David Aguilar',
          author_email = 'davvid@gmail.com',
          url = 'http://cola.tuxfamily.org/',
          description = 'git-cola',
          long_description = 'A highly caffeinated git gui',
          scripts = scripts,
          packages = ['cola', 'cola.gui', 'cola.views', 'cola.controllers',
                      'cola.json', 'cola.jsonpickle'],
          data_files = [
            _app_path('share/cola/qm', '*.qm'),
            _app_path('share/cola/icons', '*.png'),
            _app_path('share/cola/styles', '*.qss'),
            _app_path('share/cola/styles/images', '*.png'),
            _app_path('share/applications', '*.desktop'),
            _app_path('share/doc/cola', '*.txt'),
          ])

def _app_path(dirname, entry):
    if '/' in entry:
        return (dirname, glob(entry))
    else:
        return (dirname, glob(os.path.join(dirname, entry)))

def _version_to_list(version):
    """Convert a version string to a list of numbers or strings
    """
    ver_list = []
    for p in version.split('.'):
        try:
            n = int(p)
        except ValueError:
            n = p
        ver_list.append(n)
    return ver_list

def _check_min_version(min_ver, ver):
    """Check whether ver is greater or equal to min_ver
    """
    min_ver_list = _version_to_list(min_ver)
    ver_list = _version_to_list(ver)
    return min_ver_list <= ver_list

def _check_python_version():
    """Check the minimum Python version
    """
    pyver = '.'.join(map(lambda x: str(x), sys.version_info))
    if not _check_min_version(version.python_min_ver, pyver):
        print >> sys.stderr, 'Python version %s or newer required. Found %s' \
              % (version.python_min_ver, pyver)
        sys.exit(1)

def _check_git_version():
    """Check the minimum GIT version
    """
    gitver = utils.run_cmd('git', '--version').split()[2]
    if not _check_min_version(version.git_min_ver, gitver):
        print >> sys.stderr, 'GIT version %s or newer required. Found %s' \
              % (version.git_min_ver, gitver)
        sys.exit(1)

def _check_pyqt_version():
    """Check the minimum PyQt version
    """
    failed = False
    try:
        pyqtver = _run_cmd('pyuic4', '--version').split()[-1]
    except IndexError:
        pyqtver = 'nothing'
        failed = True
    if failed or not _check_min_version(version.pyqt_min_ver, pyqtver):
        print >> sys.stderr, 'PYQT version %s or newer required. Found %s' \
              % (version.pyqt_min_ver, pyqtver)
        sys.exit(1)

def _dirty(src, dst):
    if not os.path.exists(dst):
        return True
    srcstat = os.stat(src)
    dststat = os.stat(dst)
    return srcstat[stat.ST_MTIME] > dststat[stat.ST_MTIME]

def _workaround_pyuic4(src, dst):
    fh = open(src, 'r')
    contents = core.read_nointr(fh)
    fh.close()
    fh = open(dst, 'w')
    for line in contents.splitlines():
        if 'sortingenabled' in line.lower():
            continue
        core.write_nointr(fh, line+os.linesep)
    fh.close()
    os.unlink(src)

def _build_views():
    print 'running build_views'
    views = os.path.join('cola', 'gui')
    sources = glob('ui/*.ui')
    for src in sources:
        dst = os.path.join(views, os.path.basename(src)[:-3] + '.py')
        dsttmp = dst + '.tmp'
        if _dirty(src, dst):
            print '\tpyuic4 -x %s -o %s' % (src, dsttmp)
            utils.run_cmd('pyuic4', '-x', src, '-o', dsttmp)
            _workaround_pyuic4(dsttmp, dst)

def _build_translations():
    print 'running build_translations'
    sources = glob('share/cola/po/*.po')
    for src in sources:
        dst = os.path.join('share', 'cola', 'qm',
                           os.path.basename(src)[:-3] + '.qm')
        if _dirty(src, dst):
            print '\tmsgfmt --qt %s -o %s' % (src, dst)
            utils.run_cmd('msgfmt', '--qt', src, '-o', dst)

def _run_cmd(*args):
    """Runs a command and returns its output"""
    argstr = utils.shell_quote(*args)
    pipe = os.popen(argstr)
    contents = core.read_nointr(pipe).strip()
    pipe.close()
    return contents


main()
