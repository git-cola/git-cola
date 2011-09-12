#!/usr/bin/env python
"""Tests model serialization methods"""
import unittest

from cola import observer
from cola import serializer
from cola.obsmodel import ObservableModel
from cola.basemodel import BaseModel

import helper


class InnerModel(BaseModel):
    def __init__(self):
        BaseModel.__init__(self)
        self.foo = 'bar'


class NestedModel(ObservableModel):
    def __init__(self):
        ObservableModel.__init__(self)
        self.inner = InnerModel()
        self.innerlist = []
        self.innerlist.append(InnerModel())
        self.innerlist.append([InnerModel()])
        self.innerlist.append([[InnerModel()]])
        self.innerlist.append([[[InnerModel(),InnerModel()]]])
        self.innerlist.append({'foo': InnerModel()})


class ModelObserver(observer.Observer):
    def __init__(self, model):
        observer.Observer.__init__(self, model)


class TestSaveRestore(helper.TmpPathTestCase):
    def setUp(self):
        """Create a nested model for testing"""
        helper.TmpPathTestCase.setUp(self)
        self.nested = NestedModel()
        self.nested_observer = ModelObserver(self.nested)
        path = self.test_path('test.data')
        # save & reconstitute
        serializer.save(self.nested, path)
        self.clone = serializer.load(path)

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
        clone = serializer.clone(self.clone)
        self.assertTrue(len(clone.observers) == 0)
        self.assertTrue(clone.notification_enabled)
        self.assertEqual(clone.__class__, self.clone.__class__)

if __name__ == '__main__':
    unittest.main()
