#!/usr/bin/env python
from os.path import join

import Params
from Params import fatal
from wafutils import pymod
from wafutils import configure_python
from wafutils import configure_pyqt
from wafutils import wafutils_dir

# ===========================================================================
# Mandatory variables
# ===========================================================================

APPNAME = 'ugit'
VERSION = 'current'

srcdir = '.'
blddir = 'build'

# ===========================================================================
# Configure/Build
# ===========================================================================

def set_options(opt):
	opt.tool_options('python')
	opt.tool_options('pyuic4', wafutils_dir())

	opt.parser.remove_option('--prefix')
	opt.add_option('--prefix', type='string', default=None,
		help='Set installation prefix', dest='prefix')
	pass

def configure(conf):
	env = conf.env
	if Params.g_options.prefix is None:
		env['PREFIX']         = '/shared/packages/%s-%s' % ( APPNAME, VERSION )

	env['BIN']            = join(env['PREFIX'],'bin')
	env['PYMODS_LIB']     = pymod(env['PREFIX'])

	configure_python(conf)
	configure_pyqt(conf)


def build(bld):
	pyqt = bld.create_obj('py')
	pyqt.inst_var = 'PYMODS_LIB'
	pyqt.find_sources_in_dirs('py ui')

	bin = bld.create_obj('py')
	bin.inst_var = 'BIN'
	bin.find_sources_in_dirs('bin')
