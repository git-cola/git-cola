#!/usr/bin/env python
"""Tests the import-safety of leaf cola modules"""
import os
import imp
import unittest

import helper


class ColaImportTest(helper.TestCase):
    """Stub class used to hold the generated tests"""
    pass

def _gen_test_method(themodule):
    def import_test(self):
        """This is not a docstring"""
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
        method = _gen_test_method(module)
        method.__doc__ = 'Test that we can import %s' % module
        methodname = "test_" + module.replace('.', '_')
        setattr(ColaImportTest, methodname, method)
__create_tests()

if __name__ == '__main__':
    unittest.main()
