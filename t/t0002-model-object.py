#!/usr/bin/env python
import unittest
from testmodel import TestModel

class ModelTest(unittest.TestCase):
	def setUp(self):
		self.model = TestModel()
	def tearDown(self):
		del self.model

	def testCreate(self):
		self.model.create(foo='bar')
		self.failUnless(self.model.get_foo()=='bar')
	
	def testRegularAttributes(self):
		'''Test accessing attribute via model.attribute.'''
		self.failUnless( self.model.attribute == 'value' )

	def testMixedcaseAttributes(self):
		'''Test accessing attribute via model.Attribute.'''
		self.failUnless( self.model.AtTrIbUte == 'value' )
	
	def testExplicitAttr(self):
		'''Test accessing an explicit attribute. Just in case we f** up getattr'''
		self.failUnless( self.model.hello == 'world' )
	
	def testRealMethod(self):
		'''Test calling a concrete model method.'''
		self.failUnless( self.model.testMethod() == 'test' )
	
	def testGetter(self):
		'''Test calling using the get* method.'''
		self.failUnless( self.model.getAttribute() == 'value' )
	
	def testSetter(self):
		'''Test using the set* method.'''
		self.model.set_param('newAttribute','baz')
		self.failUnless( self.model.newattribute == 'baz' )
		self.failUnless( self.model.getNewAttribute() == 'baz' )

	def testAddArray(self):
		'''Test using the add* array method.'''
		self.model.array = []
		self.model.addArray('bar')
		self.failUnless( self.model.array[0] == 'bar' )

		self.model.addArray('baz','quux')
		self.failUnless( self.model.array[1] == 'baz' )
		self.failUnless( self.model.array[2] == 'quux' )

	def testAppendArray(self):
		'''Test using the append* array method.'''
		self.model.array = []
		self.model.appendArray('bar')
		self.failUnless( self.model.array[0] == 'bar' )

		self.model.appendArray('baz','quux')
		self.failUnless( self.model.array[1] == 'baz' )
		self.failUnless( self.model.array[2] == 'quux' )
	
	def testDict(self):
		'''Test setting dictionary/dictionary values.'''
		self.model.dict = { 'hello': 'world' }
		self.failUnless( self.model.dict['hello'] == 'world' )
		self.failUnless( self.model.getDict()['hello'] == 'world' )

	def testFromDict(self):
		'''Test reconstituting a model from a dictionary.'''
		self.model.from_dict({
			'test_dict': { 'hello':'world' },
			'test_list': [ 'foo', 'bar' ],
			'test_str': 'foo',
		})
		self.failUnless( self.model.get_test_dict()['hello'] == 'world' )
		self.failUnless( self.model.get_test_list()[1] == 'bar' )

if __name__ == '__main__':
	unittest.main()
