#!/usr/bin/env python
from pprint import pformat

class Observer(object):
	'''Observers receive notify(*attributes) messages from their
	subjects whenever new data arrives.  This notify() message signifies
	that an observer should update its internal state/view.'''

	def __init__(self):
		self.__attribute_adapter = {}
		self.__subjects = {}
		self.__debug = False

	def set_debug(self, enabled): self.__debug = enabled

	def notify(self, *attributes):
		'''Called by the model to notify Observers about changes.'''
		# We can be notified about multiple attribute changes at once
		for attr in attributes:

			if attr not in self.__subjects: continue

			# The model corresponding to attribute
			model = self.__subjects[attr]

			# The new value for updating
			value = model.getattr(attr)

			# Allow mapping from model to observer attributes
			if attr in self.__attribute_adapter:
				attr = self.__attribute_adapter[attr]

			# Call the concrete observer's notification method
			notify = model.get_notify()
			model.set_notify(False)

			self.subject_changed(model, attr, value)

			model.set_notify(notify)

			if not self.__debug: continue

			print "Objserver::notify(" + pformat(attributes) + "):"
			print model, "\n"


	def subject_changed(self, model, attr, value):
		'''This method handles updating of the observer/UI.
		This must be implemented in each concrete observer class.'''

		msg = 'Concrete Observers must override subject_changed().'
		raise NotImplementedError, msg

	def add_subject(self, model, model_attr):
		self.__subjects[model_attr] = model
	
	def add_attribute_adapter (self, model_attr, observer_attr):
		self.__attribute_adapter[model_attr] = observer_attr
