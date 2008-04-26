#!/usr/bin/env python
import os
from ugit.model import Model

class TestModel(Model):
	def init(self):
		duck = Model().create(sound='quack',name='ducky')
		goose = Model().create(sound='cluck',name='goose')

		self.create(
			attribute = 'value',
			mylist=[duck,duck,goose]
			)
		self.hello = 'world'
		self.set_mylist([duck,duck,goose, 'meow', 'caboose',42])

	def testMethod(self):
		return 'test'


class InnerModel(Model):
	def init(self):
		self.create(foo = 'bar')

class NestedModel(Model):
	def init(self):
		self.create(
			inner = InnerModel(),
			innerList = [],
			normaList = [ 1,2,3, [4,5, [6,7,8], 9]],
			)
		self.innerList.append(InnerModel())
		self.innerList.append([InnerModel()])
		self.innerList.append([[InnerModel()]])
		self.innerList.append([[[InnerModel(),InnerModel()]]])
		self.innerList.append({"foo": InnerModel()})
