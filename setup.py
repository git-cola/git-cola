#!/usr/bin/env python

import os
import sys
import stat
from glob import glob
from distutils.core import setup

from cola import version
from cola import utils

def main():
    # ensure readable files
    old_mask = os.umask(0022)
    if sys.argv[1] in ['install', 'build']:
        __check_python_version()
        __check_git_version()
        __check_pyqt_version()
        __build_views()             # pyuic4: .ui -> .py
        __build_translations()      # msgfmt: .po -> .qm
    try:
        version.write_builtin_version()
        __run_setup()
    finally:
        version.delete_builtin_version()
    # restore the old mask
    os.umask(old_mask)

def __run_setup():
    setup(name = 'cola',
          version = version.version,
          license = 'GPLv2',
          author = 'David Aguilar',
          author_email = 'davvid@gmail.com',
          url = 'http://cola.tuxfamily.org/',
          description = 'GIT Cola',
          long_description = 'A highly caffeinated GIT GUI',
          scripts = ['bin/git-cola'],
          packages = ['cola', 'cola.views', 'cola.controllers'],
          data_files = [
            __app_path('share/cola/qm', '*.qm'),
            __app_path('share/cola/icons', '*.png'),
            __app_path('share/cola/styles', '*.qss'),
            __app_path('share/cola/styles/images', '*.png'),
            __app_path('share/applications', '*.desktop'),
          ])

def __app_path(dirname, entry):
    return (dirname, glob(os.path.join(dirname, entry)))

def __version_to_list(version):
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

def __check_min_version(min_ver, ver):
    """Check whether ver is greater or equal to min_ver
    """
    min_ver_list = __version_to_list(min_ver)
    ver_list = __version_to_list(ver)
    return min_ver_list <= ver_list

def __check_python_version():
    """Check the minimum Python version
    """
    pyver = '.'.join(map(lambda x: str(x), sys.version_info))
    if not __check_min_version(version.python_min_ver, pyver):
        print >> sys.stderr, 'Python version %s or newer required. Found %s' \
              % (version.python_min_ver, pyver)
        sys.exit(1)

def __check_git_version():
    """Check the minimum GIT version
    """
    gitver = utils.run_cmd('git', '--version').split()[2]
    if not __check_min_version(version.git_min_ver, gitver):
        print >> sys.stderr, 'GIT version %s or newer required. Found %s' \
              % (version.git_min_ver, gitver)
        sys.exit(1)

def __check_pyqt_version():
    """Check the minimum PYQT version
    """
    pyqtver = utils.run_cmd('pyuic4', '--version').split()[-1]
    if not __check_min_version(version.pyqt_min_ver, pyqtver):
        print >> sys.stderr, 'PYQT version %s or newer required. Found %s' \
              % (version.pyqt_min_ver, pyqtver)
        sys.exit(1)

def __dirty(src, dst):
    if not os.path.exists(dst):
        return True
    srcstat = os.stat(src)
    dststat = os.stat(dst)
    return srcstat[stat.ST_MTIME] > dststat[stat.ST_MTIME]

def __build_views():
    print 'running build_views'
    views = os.path.join('cola', 'views')
    sources = glob('ui/*.ui')
    for src in sources:
        dst = os.path.join(views, os.path.basename(src)[:-3] + '.py')
        if __dirty(src, dst):
            print '\tpyuic4 -x %s -o %s' % (src, dst)
            utils.run_cmd('pyuic4', '-x', src, '-o', dst)

def __build_translations():
    print 'running build_translations'
    sources = glob('share/cola/po/*.po')
    for src in sources:
        dst = os.path.join('share', 'cola', 'qm',
                           os.path.basename(src)[:-3] + '.qm')
        if __dirty(src, dst):
            print '\tmsgfmt --qt %s -o %s' % (src, dst)
            utils.run_cmd('msgfmt', '--qt', src, '-o', dst)

main()
