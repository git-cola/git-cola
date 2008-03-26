#!/usr/bin/env python
import os
import sys
import glob
import Params
import Common

# Release versioning
def get_version():
	"""Runs version.sh and returns the output."""
	cmd = os.path.join(os.getcwd(), 'scripts', 'version.sh')
	pipe = os.popen(cmd)
	version = pipe.read()
	pipe.close()
	return version.strip()

#############################################################################
# Mandatory variables
APPNAME = 'ugit'
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
	env = conf.env
	env['PYMODS'] = pymod(env['PREFIX'])
	env['PYMODS_UGIT'] = os.path.join(env['PYMODS'], 'ugit')
	env['ICONS'] = os.path.join(env['PREFIX'], 'share', 'ugit', 'icons')
	env['BIN'] = os.path.join(env['PREFIX'], 'bin')

	conf.check_tool('misc')
	conf.check_tool('python')
	conf.check_tool('pyuic4', 'build')
	conf.check_tool('po2qm', 'build')

#############################################################################
# Build
def build(bld):
	bld.add_subdirs('scripts ui ugit')

	bin = bld.create_obj('py')
	bin.inst_var = 'BIN'
	bin.chmod = 0755
	bin.find_sources_in_dirs('bin')

	qm = bld.create_obj('po2qm')
	qm.find_sources_in_dirs('po')

	for icon in glob.glob('icons/*.png'):
		Common.install_files('ICONS', '', icon)
	
	Common.symlink_as('BIN', 'git-ugit.py', 'ugit')

#############################################################################
# Other
def pymod(prefix):
	"""Returns a lib/python2.x/site-packages path relative to prefix"""
	api_version = sys.version[:3]
	python_api = 'python' + api_version
	return os.path.join(prefix, 'lib', python_api, 'site-packages')
