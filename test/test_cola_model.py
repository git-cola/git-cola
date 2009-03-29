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
        """Test that arbitrary attributes provide get_* methods"""
        model = ExampleModel()
        model.foo = 'bar'
        self.failUnless(model.get_foo()=='bar')

    def test_regular_attribute(self):
        """Test attribute access in case we f*** up __getattr__"""
        model = ExampleModel()
        model.attribute = 'value'
        self.assertEqual(model.attribute, 'value')

    def test_mixed_case_attributes(self):
        """Test accessing an attribute via model.AtTrIbUte"""
        model = ExampleModel()
        model.attribute = 'value'
        self.assertEqual(model.AtTrIbUte, 'value')

    def test_method(self):
        """Test calling a concrete method"""
        model = ExampleModel()
        self.assertEqual(model.pass_through('value'), 'value')

    def test_auto_getter(self):
        """Test using the auto get* method"""
        model = ExampleModel()
        model.attribute = 'value'
        self.assertEqual(model.get_attribute(), 'value' )
        self.assertEqual(model.getAttribute(), 'value' )

    def test_auto_setter(self):
        """Test using the auto set* method"""
        model = ExampleModel()
        model.set_param('newAttribute', 'baz')
        self.assertEqual(model.newattribute, 'baz' )
        self.assertEqual(model.getNewAttribute(), 'baz' )

    def test_add_array(self):
        """Test using the auto add* method"""
        model = ExampleModel()
        model.array = []
        model.addArray('bar')
        self.assertEqual(model.array[0], 'bar')

        model.add_array('baz', 'quux')
        self.assertEqual(model.array[0], 'bar')
        self.assertEqual(model.array[1], 'baz')
        self.assertEqual(model.array[2], 'quux')

    def test_append_array(self):
        """Test using the auto append* array methods"""
        model = ExampleModel()
        model.array = []
        model.appendArray('bar')
        self.assertEqual(model.array[0], 'bar')

        model.append_array('baz', 'quux')
        self.assertEqual(model.array[0], 'bar')
        self.assertEqual(model.array[1], 'baz')
        self.assertEqual(model.array[2], 'quux')

    def test_dict_attribute(self):
        """Test setting dictionaries/dictionary values."""
        model = ExampleModel()
        model.thedict = { 'hello': 'world' }
        self.assertEqual(model.thedict['hello'], 'world' )
        self.assertEqual(model.get_thedict()['hello'], 'world' )
        self.assertEqual(model.getTheDict()['hello'], 'world' )

    def test_from_dict(self):
        """Test reconstituting a model from a dictionary."""
        model = ExampleModel()
        model.from_dict({
            'test_dict': { 'hello':'world' },
            'test_list': [ 'foo', 'bar' ],
            'test_str': 'foo',
        })
        self.assertEqual(model.get_test_dict()['hello'], 'world')
        self.assertEqual(model.get_test_list()[1], 'bar' )


if __name__ == '__main__':
    unittest.main()
