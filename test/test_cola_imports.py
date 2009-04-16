#!/usr/bin/env python
import os
import imp
import unittest

import helper


class ImportTest(helper.TestCase):
    pass

def gen_class(themodule):
    def import_test(self):
        mod = __import__(themodule)
        self.failUnless(mod)
    return import_test

def __create_tests():
    for module in """
        cola.git
        cola.model
        cola.observer
        cola.settings
    """.split():
        setattr(ImportTest,
                "test" + module.title().replace('.', ''),
                gen_class(module))
__create_tests()

if __name__ == '__main__':
    unittest.main()
