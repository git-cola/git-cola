#!/usr/bin/env python
import os
import unittest

import testutils

from testmodel import InnerModel
from testmodel import NestedModel

from ugit.model import Model


class SaveRestoreTest(testutils.TestCase):

	def setUp(self):
		testutils.TestCase.setUp(self)
		self.nested = NestedModel()
		path = os.path.join(self.testDir(), 'test.data')
		self.nested.save(path)
		# reconstitute
		self.clone = Model.load(path)

	def testCloneToClass(self):
		self.failUnless( str(NestedModel) ==
		                 str(self.clone.__class__) )

	def testClonedInnerToClass(self):
		self.failUnless( str(InnerModel) ==
		                 str(self.clone.inner.__class__) )

	def testClonedListAndParam(self):
		self.failUnless( str(self.clone.inner.__class__) ==
		                 str(self.clone.innerList[0].__class__) )

	def testList(self):
		self.failUnless( str(InnerModel) ==
		                 str(self.clone.innerList[1][0].__class__) )

	def testListInList(self):
		self.failUnless( str(InnerModel) ==
		                 str(self.clone.innerList[2][0][0].__class__))

	def testListInListInList(self):
		self.failUnless( str(InnerModel) ==
		                 str(self.clone.innerList[3][0][0][0].__class__))

	def testDictInList(self):
		self.failUnless( str(dict) ==
		                 str(self.clone.innerList[4].__class__))

	def testObjectInDictInList(self):
		self.failUnless( str(InnerModel) ==
		                 str(self.clone.innerList[-1]["foo"].__class__))



if __name__ == '__main__':
	unittest.main()
