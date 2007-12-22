#!/usr/bin/env python
import os
import platform
import Params

def pymod(prefix):
	'''Returns a lib/python2.x/site-packages path relative to prefix'''
	python_ver = platform.python_version_tuple()
	python_ver_str = 'python' + '.'.join(python_ver[:2])
	return os.path.join(prefix, 'lib', python_ver_str, 'site-packages')

def configure_python(conf):
	if not conf.check_tool('python'):
		Params.fatal('Error: could not find a Python installation.')

def configure_pyqt(conf):
	# pyuic4 is a custom build object, hence the 2nd parameter
	if not conf.check_tool('pyuic4', os.path.dirname(__file__)):
		Params.fatal('Error: missing PyQt4 development tools.\n'
			+ 'Hint: on Debian systems try:\n'
			+ '\tapt-get install pyqt4-dev-tools python-qt4-dev')
