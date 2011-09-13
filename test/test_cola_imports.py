#!/usr/bin/env python
"""Tests the import-safety of leaf cola modules"""
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
                     cola.basemodel
                     cola.classic.controller
                     cola.classic.model
                     cola.classic.view
                     cola.observer
                     cola.obsmodel
                     cola.settings
                     cola.controllers.bookmark
                     cola.controllers.compare
                     cola.controllers.createbranch
                     cola.main.controller
                     cola.main.model
                     cola.main.view
                     cola.controllers.merge
                     cola.controllers.remote
                     cola.controllers.repobrowser
                     cola.controllers.search
                     cola.controllers.selectcommits
                     cola.controllers.stash
                     cola.models.compare
                     cola.models.search
                     cola.prefs.view
                     cola.prefs.model
                     cola.prefs.controller
                     """.strip().split():
        method = _gen_test_method(module)
        method.__doc__ = 'Test that we can import %s' % module
        methodname = "test_" + module.replace('.', '_')
        setattr(ColaImportTest, methodname, method)
__create_tests()

if __name__ == '__main__':
    unittest.main()
