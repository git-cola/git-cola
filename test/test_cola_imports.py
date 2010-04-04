#!/usr/bin/env python
"""Tests the import-safety of leaf cola modules"""
import os
import imp
import unittest


class ColaImportTest(unittest.TestCase):
    """Stub class used to hold the generated tests"""
    pass

def _gen_test_method(themodule):
    def import_test(self):
        """This is not a docstring"""
        mod = __import__(themodule)
        self.failUnless(mod)
    return import_test

def __create_tests():
    for module in """cola.git
                     cola.observer
                     cola.settings
                     cola.controllers.bookmark
                     cola.controllers.classic
                     cola.controllers.compare
                     cola.controllers.createbranch
                     cola.controllers.main
                     cola.controllers.merge
                     cola.controllers.options
                     cola.controllers.remote
                     cola.controllers.repobrowser
                     cola.controllers.search
                     cola.controllers.selectcommits
                     cola.controllers.stash
                     cola.models.base
                     cola.models.compare
                     cola.models.gitrepo
                     cola.models.main
                     cola.models.observable
                     cola.models.search""".split():
        method = _gen_test_method(module)
        method.__doc__ = 'Test that we can import %s' % module
        methodname = "test_" + module.replace('.', '_')
        setattr(ColaImportTest, methodname, method)
__create_tests()

if __name__ == '__main__':
    unittest.main()
