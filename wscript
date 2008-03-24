#!/usr/bin/env python
import os
import sys
import glob
import Params
import Common

# Release versioning
def get_version():
	"""Searches defaults.py for the VERSION field and returns it."""
	defaults = os.path.join(os.getcwd(), 'ugitlibs', 'defaults.py')
	file = open(defaults, 'r')
	contents = file.read()
	file.close()
	for line in contents.splitlines():
		if line.startswith('VERSION = '):
			version = line.replace('VERSION = ', '')
			return version.strip("'")
	raise Exception("Could not find VERSION field in %s" % defaults)

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
	env['PYMODS_UGIT'] = os.path.join(env['PYMODS'], 'ugitlibs')
	env['ICONS'] = os.path.join(env['PREFIX'], 'share', 'ugit', 'icons')
	env['BIN'] = os.path.join(env['PREFIX'], 'bin')

	conf.check_tool('python')
	conf.check_tool('pyuic4', 'build')
	conf.check_tool('po2qm', 'build')

#############################################################################
# Build
def build(bld):
	bld.add_subdirs('ui ugitlibs')

	bin = bld.create_obj('py')
	bin.inst_var = 'BIN'
	bin.chmod = 0755
	bin.find_sources_in_dirs('bin')

	qm = bld.create_obj('po2qm')
	qm.find_sources_in_dirs('po')

	for icon in glob.glob('icons/*.png'):
		Common.install_files('ICONS', '', icon)
	
	Common.symlink_as('BIN', 'ugit.py', 'ugit')

#############################################################################
# Other
def pymod(prefix):
	"""Returns a lib/python2.x/site-packages path relative to prefix"""
	api_version = sys.version[:3]
	python_api = 'python' + api_version
	return os.path.join(prefix, 'lib', python_api, 'site-packages')
