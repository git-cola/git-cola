#!/usr/bin/env python
from os.path import join
from glob import glob

import Params
from Common import install_files
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

	env['PYMODS']           = pymod(env['PREFIX'])
	env['PYMODS_UGIT']      = join(env['PYMODS'],      'ugitlibs')
	env['ICONS']            = join(env['PYMODS_UGIT'], 'icons')
	env['BIN']              = join(env['PREFIX'],      'bin')

	configure_python(conf)
	configure_pyqt(conf)


def build(bld):
	bld.add_subdirs('py ui')

	bin = bld.create_obj('py')
	bin.inst_var = 'BIN'
	bin.chmod = 0755
	bin.find_sources_in_dirs('bin')

	for icon in glob('icons/*.png'):
		install_files ('ICONS', '', icon)
