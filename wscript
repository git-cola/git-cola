#!/usr/bin/env python
import os
import sys
import glob
import Params
import Common
from os.path import join

# Release versioning
def get_version():
    """Runs version.sh and returns the output."""
    cmd = join(os.getcwd(), 'scripts', 'version.sh')
    pipe = os.popen(cmd)
    version = pipe.read()
    pipe.close()
    return version.strip()

#############################################################################
# Mandatory variables
APPNAME = 'cola'
VERSION = get_version()

srcdir = '.'
blddir = 'obj'

#############################################################################
# Options
def set_options(opt):
    opt.tool_options('python')
    opt.tool_options('pyuic4', 'build')
    pass

#############################################################################
# Configure
def configure(conf):
    conf.check_tool('misc')
    conf.check_tool('python')
    conf.check_tool('pyuic4', 'build')
    conf.check_tool('po2qm', 'build')

    env = conf.env
    prefix = env['PREFIX']
    bindir = join(prefix, 'bin')
    share = join(prefix, 'share')
    modules = join(share, 'cola')
    views = join(modules, 'views')
    controllers = join(modules, 'controllers')
    icons = join(prefix, 'share', 'cola', 'icons')
    apps = join(prefix, 'share', 'applications')

    env['COLA_BINDIR'] = bindir
    env['COLA_MODULES'] = modules
    env['COLA_VIEWS'] = views
    env['COLA_CONTROLLERS'] = controllers
    env['COLA_ICONS'] = icons
    env['COLA_APPS'] = apps

    try:
        import git
    except ImportError:
        print """
ERROR: could not "import git"

Please install the python-git package
or grab GitPython from the cheeseshop:

    http://pypi.python.org/pypi/GitPython


GitPython's git repository can be cloned from gitorious:

    http://gitorious.org/projects/git-python
"""
        return False

#############################################################################
# Build
def build(bld):
    bld.add_subdirs("""
        scripts
        ui
        cola
    """)

    qm = bld.create_obj('po2qm')
    qm.find_sources_in_dirs('po')

    for icon in glob.glob('icons/*.png'):
        Common.install_files('COLA_ICONS', '', icon)

#############################################################################
# Shutdown
def shutdown():
    # always re-create the version.py file
    for variant in Params.g_build.m_allenvs:
        version_file = join(Params.g_build.m_bdir,
                            variant,
                            'scripts',
                            'version.py')
        if os.path.exists(version_file):
            os.unlink(version_file)
