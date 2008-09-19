#!/usr/bin/env python
import os
import imp
import unittest

import testlib

class ImportTest(testlib.TestCase):
    pass

def gen_class(module):
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

def __create_tests():
    for module in """
        cola.git
        cola.model
        cola.observer
        cola.exception
        cola.defaults
        cola.settings
    """.split():
        setattr(ImportTest,
                "test" + module.title().replace('.', ''),
                gen_class(module))
__create_tests()

if __name__ == '__main__':
    unittest.main()
