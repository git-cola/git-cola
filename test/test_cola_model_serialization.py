#!/usr/bin/env python
"""Tests model serialization methods"""
import os
import sys
import unittest

from PyQt4 import QtCore

from cola.models.observable import ObservableModel
from cola.observer import Observer

import helper
from helper import InnerModel
from helper import NestedModel

class ModelObserver(Observer, QtCore.QObject):
    def __init__(self, model):
        Observer.__init__(self, model)
        QtCore.QObject.__init__(self)

class TestSaveRestore(unittest.TestCase):
    def setUp(self):
        """Create a nested model for testing"""
        helper.create_dir()
        self.nested = NestedModel()
        self.nested_observer = ModelObserver(self.nested)
        path = os.path.join(helper.get_dir(), 'test.data')
        # save & reconstitute
        self.nested.save(path)
        self.clone = ObservableModel.instance(path)
        self.clone_observer = ModelObserver(self.clone)

    def tearDown(self):
        """Remove test directories"""
        testdir = helper.get_dir()
        if os.path.exists(testdir):
            helper.remove_dir()

    def test_cloned_class(self):
        """Test equality for __class__"""
        self.failUnless( str(NestedModel) ==
                         str(self.clone.__class__) )

    def test_inner_cloned_class(self):
        """Test an inner clone's __class__"""
        self.failUnless( str(InnerModel) ==
                         str(self.clone.inner.__class__) )

    def test_cloned_list_item(self):
        """Test a list item's __class__"""
        self.failUnless( str(self.clone.inner.__class__) ==
                         str(self.clone.innerlist[0].__class__) )

    def test_list_2deep(self):
        """Test a list-inside-a-list"""
        self.failUnless( str(InnerModel) ==
                         str(self.clone.innerlist[1][0].__class__) )

    def test_list_3deep(self):
        """Test a 3-deep nested list"""
        self.failUnless( str(InnerModel) ==
                         str(self.clone.innerlist[2][0][0].__class__))

    def test_list_4deep(self):
        """Test a 4-deep nested list"""
        self.failUnless( str(InnerModel) ==
                         str(self.clone.innerlist[3][0][0][0].__class__))

    def test_dict_in_list(self):
        """Test a dict inside a list"""
        self.failUnless( str(dict) ==
                         str(self.clone.innerlist[4].__class__))

    def test_obj_in_dict_in_list(self):
        """Test an object instance inside a dict inside a list"""
        self.failUnless( str(InnerModel) ==
                         str(self.clone.innerlist[-1]["foo"].__class__))

    def test_clone_of_clone(self):
        """Test cloning a reconstructed object with an attached observer."""
        clone = self.clone.clone()
        self.assertTrue(len(clone.observers) == 0)
        self.assertTrue(clone.notification_enabled)
        self.assertEqual(clone.__class__, self.clone.__class__)

if __name__ == '__main__':
    unittest.main()
