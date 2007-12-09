#!/usr/bin/env python
import os
import platform
from os.path import join
from Params import fatal

def pymod(prefix):
	'''Returns a lib/python2.x/site-packages path relative to prefix'''
	python_ver = 'python' + '.'.join(platform.python_version_tuple()[:2])
	return join( prefix, 'lib', python_ver, 'site-packages' )

def configure_python(conf):
	if not conf.check_tool('python'):
		fatal("Error: could not find a Python installation.")

def configure_pyqt(conf):
	# pyuic4 is a custom build object
	if not conf.check_tool('pyuic4', os.path.dirname (__file__)):
		fatal("Error: missing PyQt4 development environment.\n"
			+ "Hint: on Debian systems try:\n"
			+ "\tapt-get install pyqt4-dev-tools python-qt4-dev")
