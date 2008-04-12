#!/usr/bin/env python
import os
import sys
import glob
import Params
import Common
from os.path import join
from distutils.sysconfig import get_python_version

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
	prefix = env['PREFIX']
	bindir = join(prefix, 'bin')
	sitepackages = pymod(prefix)
	modules = join(sitepackages, 'ugit')
	views = join(modules, 'views')
	controllers = join(modules, 'controllers')
	icons = join(prefix, 'share', 'ugit', 'icons')

	env['UGIT_BINDIR'] = bindir
	env['UGIT_MODULES'] = modules
	env['UGIT_VIEWS'] = views
	env['UGIT_CONTROLLERS'] = controllers
	env['UGIT_ICONS'] = icons

	conf.check_tool('misc')
	conf.check_tool('python')
	conf.check_tool('pyuic4', 'build')
	conf.check_tool('po2qm', 'build')

#############################################################################
# Build
def build(bld):
	bld.add_subdirs('scripts ui ugit')

	qm = bld.create_obj('po2qm')
	qm.find_sources_in_dirs('po')

	for icon in glob.glob('icons/*.png'):
		Common.install_files('UGIT_ICONS', '', icon)

#############################################################################
# Other
def pymod(prefix):
	"""Returns a lib/python2.x/site-packages path relative to prefix"""
	python_api = 'python' + get_python_version()
	return join(prefix, 'lib', python_api, 'site-packages')
