#!/usr/bin/env python
import os
import glob
import buildutils
import Common

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
	env['PYMODS']           = buildutils.pymod(env['PREFIX'])
	env['PYMODS_UGIT']      = os.path.join(env['PYMODS'], 'ugitlibs')
	env['ICONS']            = os.path.join(env['PYMODS_UGIT'], 'icons')
	env['BIN']              = os.path.join(env['PREFIX'], 'bin')

	buildutils.configure_python(conf)
	buildutils.configure_pyqt(conf)

# Build
def build(bld):
	bld.add_subdirs('py ui')

	bin = bld.create_obj('py')
	bin.inst_var = 'BIN'
	bin.chmod = 0755
	bin.find_sources_in_dirs('bin')

	for icon in glob.glob('icons/*.png'):
		Common.install_files ('ICONS', '', icon)
	
	Common.symlink_as ('BIN', 'ugit.py', 'ugit')
