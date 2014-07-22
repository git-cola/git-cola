#!/usr/bin/env python
import unittest

from PyQt4 import QtGui


# This would normally be done in the unit test setup BUT
# The import triggers the problem :-(
def setapi(self, *args):
    pass
import sip
Store_setapi = sip.setapi
sip.setapi = setapi

from cola import app
from test.support import run_unittest


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
        sip.setapi = Store_setapi

    def test_setup_environment(self):
        #If the function doesn't throw an exception we are happy.
        app.setup_environment()

    def test_ColaApplication(self):
        test_app = app.ColaQApplication('')
        test_app.view = self.MockView()  # just not None
        session = self.Mock_Session_Mgr()
        test_app.commitData(session)


def test_suite():
    return unittest.makeSuite(AppTestCase)

if __name__ == "__main__":
    run_unittest(test_suite())
