#!/usr/bin/env python
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

	def testMethod(self): return 'test'
