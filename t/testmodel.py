#!/usr/bin/env python
from ugitlibs.model import Model

class TestModel(Model):
	def __init__(self):
		duck = Model().create(sound='quack',name='ducky')
		goose = Model().create(sound='cluck',name='goose')

		Model.__init__(self, attribute = 'value',
				mylist=[duck,duck,goose])
		self.hello = 'world'
		self.set_list_params(mylist=Model)
		self.set_mylist([duck,duck,goose, 'meow', 'caboose',42])

	def testMethod(self): return 'test'
