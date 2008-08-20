#!/usr/bin/env python
import os
import imp
import unittest

from testutils import *
from testmodel import *

class ImportTest(TestCase):
    pass

def gen_import_test(module):
    def import_test(self):
        modinfo = None
        for idx, path in enumerate(module.split('.')):
            if idx == 0:
                modinfo = imp.find_module(path)
                mod = imp.load_module(module, *modinfo)
            else:
                modinfo = imp.find_module('cola/'+path, modinfo[0])
                mod = imp.load_module(path, *modinfo)
            self.failUnless(mod)
    return import_test

def setup_tests():
    for module in """
        cola.model
        cola.models
        cola.qobserver
        cola.controllers
        cola.utils
        cola.qtutils
    """.split():
        setattr(ImportTest,
                "test" + module.title().replace('.', ''),
                gen_import_test(module))

setup_tests()
unittest.main()
