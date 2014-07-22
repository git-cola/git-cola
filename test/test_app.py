#!/usr/bin/env python
import unittest

from cola import app

from PyQt4 import QtGui

from test.helper import run_unittest


class AppTestCase(unittest.TestCase):

    class MockQtGuiQApplication(object):
        def __init__(self, *args):
            pass

    class Mock_Session_Mgr(object):
        def sessionId(self):
            return 'junk_string'

        def sessionKey(self):
            return 'junk_string'

    class MockView(object):
        def save_state(self, *args, **kwargs):
            pass

    def setUp(self):
        super(AppTestCase, self).setUp()
        self.Store_QApplication = QtGui.QApplication
        QtGui.QApplication = self.MockQtGuiQApplication

    def tearDown(self):
        super(AppTestCase, self).tearDown()
        QtGui.QApplication = self.Store_QApplication

    def test_setup_environment(self):
        #If the function doesn't throw an exception we are happy.
        app.setup_environment()


def test_suite():
    return unittest.makeSuite(AppTestCase)

if __name__ == "__main__":
    run_unittest(test_suite())
