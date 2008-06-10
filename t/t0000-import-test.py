#!/usr/bin/env python
import unittest
import os
import imp

from testutils import *
from testmodel import *

class ImportTest(TestCase):
	pass

def setup_tests():
	for module in """
		cola.model
		cola.models
		cola.qobserver
		cola.controllers
		cola.utils
		cola.qtutils
	""".split():
		def import_test(self):
			modinfo = None
			for idx, path in enumerate(module.split('.')):
				if idx == 0:
					modinfo = imp.find_module(path)
					mod = imp.load_module(module, *modinfo)
				else:
					modinfo = imp.find_module(path, modinfo[0])
					mod = imp.load_module(path, *modinfo)
				self.failUnless( mod )
		setattr(ImportTest, "test" + module.title(), import_test)

setup_tests()
unittest.main()
