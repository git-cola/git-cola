#!/usr/bin/env python
import unittest
import helper

from cola import model

class ExampleModel(model.Model):
    """An example model for use by these tests"""
    def pass_through(self, value):
        """Passes values through unmodified"""
        return value

class ModelTest(unittest.TestCase):
    """Tests the cola.model.Model class"""

    def test_create_attribute(self):
        """Test that arbitrary attributes provide set_* methods"""
        model = ExampleModel()
        model.set_foo('bar')
        self.assertEqual(model.foo, 'bar')

    def test_param(self):
        """Test attribute access in case we f*** up __getattr__"""
        model = ExampleModel()
        model.attribute = 'value'
        self.assertEqual(model.param('attribute'), 'value')

    def test_method(self):
        """Test calling a concrete method"""
        model = ExampleModel()
        self.assertEqual(model.pass_through('value'), 'value')

    def test_dict_attribute(self):
        """Test setting dictionaries/dictionary values."""
        model = ExampleModel()
        model.thedict = { 'hello': 'world' }
        self.assertEqual(model.thedict['hello'], 'world' )

    def test_from_dict(self):
        """Test reconstituting a model from a dictionary."""
        model = ExampleModel()
        model.from_dict({
            'test_dict': { 'hello':'world' },
            'test_list': [ 'foo', 'bar' ],
            'test_str': 'foo',
        })
        self.assertEqual(model.test_dict['hello'], 'world')
        self.assertEqual(model.test_list[1], 'bar')


if __name__ == '__main__':
    unittest.main()
