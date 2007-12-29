#!/usr/bin/env python
import imp
from types import *

class Observable(object):
	'''Handles subject/observer notifications.'''
	def __init__(self, notify=True):
		self.__observers = []
		self.__notify = notify
	def get_notify(self):
		return self.__notify
	def set_notify(self, notify=True):
		self.__notify = notify
	def add_observer(self, observer):
		if observer not in self.__observers:
			self.__observers.append(observer)
	def remove_observer(self, observer):
		if observer in self.__observers:
			self.__observers.remove(observer)
	def notify_observers(self, *attr):
		if not self.__notify: return
		for observer in self.__observers:
			observer.notify(*attr)

class Model(Observable):
	'''Creates a generic model object with attributes specified
	as a name:value dictionary.

	get_name() and set_name(value) are created automatically
	for any of the specified attributes.'''

	def __init__(self, attributes = {}, defaults = {}, notify=True):
		'''Initializes all attributes and default attribute
		values.  By default we do not call notify unless explicitly
		told to do so.'''

		Observable.__init__(self, notify)

		for attr, value in attributes.iteritems():
			setattr(self, attr, value)

		for attr, value in defaults.iteritems():
			if not hasattr(self, attr):
				setattr(self, attr, value)

		# For meta-programmability
		self.__attributes = list(attributes.keys() + defaults.keys())
		self.__list_attrs = {}
		self.__object_attrs = {}
	
	def create(self,**kwargs):
		self.from_dict(kwargs)

	def clone(self):
		return self.__class__().from_dict(self.to_dict())

	def set_list_attrs(self, list_attrs):
		self.__list_attrs.update(list_attrs)
	
	def set_object_attrs(self, obj_attrs):
		self.__object_attrs.update(obj_attrs)

	def getattr(self, attr):
		return getattr(self, attr)
	
	def get_attributes(self):
		return self.__attributes


	def __getattr__(self, attr):
		'''Provides automatic get/set/add/append methods.'''

		# Base case: we actually have this attribute
		if attr in self.__dict__:
			return getattr(self, attr)

		# Check for the translated variant of the attr
		realattr = self.__translate(attr, sep='')
		if realattr in self.__dict__:
			return getattr(self, realattr)

		if realattr.startswith('get'):
			realattr = self.__translate(attr, 'get')
			return lambda: getattr(self, realattr)

		elif realattr.startswith('set'):
			realattr = self.__translate(attr, 'set')
			return lambda(value): self.set(realattr, value)

		elif realattr.startswith('add'):
			self.__array = self.__translate(attr, 'add')
			return self.__append

		elif realattr.startswith('append'):
			self.__array = self.__translate(attr, 'append')
			return self.__append

		errmsg  = "%s object has no attribute '%s'" \
			%( self.__class__, attr )

		raise AttributeError, errmsg

	def set(self, attr, value, notify=True):
		'''Sets a model attribute.'''
		setattr(self, attr, value)
		if attr not in self.__attributes:
		    self.__attributes.append(attr)
		if notify: self.notify_observers(attr)

	def __append(self, *values):
		'''Appends an arbitrary number of values to
		an array atribute.'''

		attr = self.__array
		array = getattr(self, attr)

		if array is None:
			errmsg = "%s object has no attribute '%s'" \
				%( self.__class__, attr )
			raise AttributeError, errmsg

		for value in values:
			array.append(value)


	def __translate(self, attr, prefix='', sep='_'):
		'''Translates an attribute name from the external name
		used in methods to those used internally.  The default
		settings strip off '_' so that both get_foo() and getFoo()
		are valid incantations.'''

		return attr.lstrip(prefix).lstrip(sep).lower()

	def __get_class(self, objspec):
		'''Loads a class from a module and returns the class.'''

		# str("module.submodule:ClassName")
		( modname, classname ) = objspec.split(':')
		modfile = imp.find_module(modname)
		module = imp.load_module(modname,
				modfile[0], modfile[1], modfile[2])

		if classname in module.__dict__:
		    cls = module.__dict__[classname]
		else:
		    cls = Model
		    warning = 'WARNING: %s not found in %s\n' %(
					modname, classname )
		    sys.stderr.write(warning)

                modfile[0].close()
		return cls

	def save(self, filename):
		import simplejson
		file = open(filename, 'w')
		simplejson.dump( self.to_dict(), file, indent=4 )
		file.close()

	def load(self, filename):
		import simplejson
		file = open(filename, 'r')
		dict = simplejson.load(file)
		file.close()
		self.from_dict(dict)

	def from_dict(self, model):
		'''Import a complex model from a dictionary.  The import/export
		is clued as to nested Model-objects by setting the
		__list_attrs or __object_attrs object specifications.'''

		for attr,val in model.iteritems():
			setattr(self, attr, self.__attr_from_dict(attr,val))
			if attr not in self.__attributes:
				    self.__attributes.append(attr)
		return self
	
	def __attr_from_dict(self,attr,val):

		# A list of Model-objects
		if is_list(val):
			if attr in self.__list_attrs:
				# A list of Model-derived objects
				listattr = []
				objspec = self.__list_attrs[attr]
				cls = self.__get_class(objspec)
				for item in val:
					listattr.append(cls().from_dict(item))
				return listattr

		# An attribute that maps to a Model-object
		elif is_dict(val):
			if attr in self.__object_attrs:
				# "module.submodule:ClassName"
				objectspec = self.__object_attrs[attr]
				cls = self.__get_class(objectspec)
				return cls().from_dict(val)

		# Atoms and uninteresting hashes/dictionaries
		return val


	def to_dict(self):
		'''Exports a model to a dictionary.
		This simplifies serialization.'''

		attrs = {}
		for attr in self.__attributes:
			attrs[attr] = self.__attr_to_dict(attr)
		return attrs

	def __attr_to_dict(self, attr):
		item = getattr(self, attr)
		return self.__item_to_dict(item)
	
	def __item_to_dict(self, item):

		if is_atom(item): return item

		elif is_list(item):
			newlist = []
			for i in item:
				newlist.append(self.__item_to_dict(i))
			return newlist

		elif is_dict(item):
			newdict = {}
			for k,v in item.iteritems():
				newdict[k] = self.__item_to_dict(v)
			return newdict

		elif is_instance(item):
			return item.to_dict()

		else:
			raise NotImplementedError, 'Unknown type:' + str(type(item))


	__INDENT__ = -4 # Used by __str__

	def __str__(self):
		'''A convenient, recursively-defined stringification method.'''

		Model.__INDENT__ += 4

		strings = ['']
		for attr in self.__dict__:
			if attr.startswith('_'): continue
			inner = " " * Model.__INDENT__ + attr + ":  "

			value = getattr(self, attr)

			if type(value) == ListType:

				indent = " " *(Model.__INDENT__ + 4)
				strings.append(inner + "[")
				for val in value:
					stringval = indent + str(val)
					strings.append(stringval)

				indent = " " * Model.__INDENT__
				strings.append(indent + "]")

			else:
				strings.append(inner + str(value))

		Model.__INDENT__ -= 4

		return "\n".join(strings)


def is_dict(item):
	return type(item) is DictType
def is_list(item):
	return type(item) is ListType or type(item) is TupleType
def is_atom(item):
	return(type(item) in StringTypes
		or type(item) is BooleanType
		or type(item) is IntType
		or type(item) is LongType
		or type(item) is FloatType
		or type(item) is ComplexType)

def is_instance(item):
	return( issubclass(item.__class__, Model)
		or type(item) is InstanceType )
