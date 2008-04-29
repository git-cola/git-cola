#!/usr/bin/env python
import unittest
import os
import imp

from testutils import *
from testmodel import *

from ugit import git

class ImportTest(TestCase):
	pass

def setup_tests():
	for module in """
		ugit.git
		ugit.model
		ugit.models
		ugit.qobserver
		ugit.controllers
		ugit.utils
		ugit.qtutils
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
