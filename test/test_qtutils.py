#!/usr/bin/env python
import unittest

from PyQt4 import QtGui

from cola import qtutils
from test.support import run_unittest


class QtUtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.app = QtGui.QApplication(['dummy_string'])
        super(QtUtilsTestCase, self).setUp()

    def tearDown(self):
        super(QtUtilsTestCase, self).tearDown()

    def test_copy_path(self):
        # This doesn't do much except make sure it doesn't throw and exception
        qtutils.copy_path('dummy_string')


def test_suite():
    return unittest.makeSuite(QtUtilsTestCase)

if __name__ == "__main__":
    run_unittest(test_suite())
