#!/usr/bin/env python
import os
from commands import getoutput

KNOWN_FILE_TYPES = {
	'ascii c':   'c',
	'python':    'script',
	'ruby':      'script',
	'shell':     'script',
	'perl':      'script',
	'java':      'script',
	'assembler': 'binary',
	'binary':    'binary',
	'byte':      'binary',
	'image':     'image',
}

def ident_file_type (filename):
	if os.path.exists (filename):
		fileinfo = getoutput('file -b "%s"' % filename)
		for filetype, iconname in KNOWN_FILE_TYPES.iteritems():
			if filetype in fileinfo.lower():
				return iconname
	return 'generic'

def get_icon (filename):
	filetype = ident_file_type (filename)
	ugitdir = os.path.dirname (__file__)
	return os.path.join( ugitdir, 'icons', filetype + '.png' )
