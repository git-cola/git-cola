#!/usr/bin/env python
import os
from os.path import join
from glob import glob
from Common import install_files
from buildutils import pymod
from buildutils import configure_python
from buildutils import configure_pyqt

APPNAME = 'ugit'
VERSION = '0.5.0'

# Mandatory variables
srcdir = '.'
blddir = 'build'

# Options
def set_options(opt):
	opt.tool_options('python')
	opt.tool_options('pyuic4', 'buildutils')
	pass

# Configure
def configure(conf):
	env = conf.env
	env['PYMODS']           = pymod(env['PREFIX'])
	env['PYMODS_UGIT']      = join(env['PYMODS'],      'ugitlibs')
	env['ICONS']            = join(env['PYMODS_UGIT'], 'icons')
	env['BIN']              = join(env['PREFIX'],      'bin')

	configure_python(conf)
	configure_pyqt(conf)

# Build
def build(bld):
	bld.add_subdirs('py ui')

	bin = bld.create_obj('py')
	bin.inst_var = 'BIN'
	bin.chmod = 0755
	bin.find_sources_in_dirs('bin')

	for icon in glob('icons/*.png'):
		install_files ('ICONS', '', icon)
