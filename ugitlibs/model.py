#!/usr/bin/env python
import os
import imp
from cStringIO import StringIO
from types import DictType
from types import ListType
from types import TupleType
from types import StringTypes
from types import BooleanType
from types import IntType
from types import LongType
from types import FloatType
from types import ComplexType
from types import InstanceType

class Observable(object):
	'''Handles subject/observer notifications.'''
	def __init__(self,*args,**kwargs):
		self.__observers = []
		self.__notify = True
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
	def notify_observers(self, *param):
		if not self.__notify: return
		for observer in self.__observers:
			observer.notify(*param)

class Model(Observable):
	'''Creates a generic model object with params specified
	as a name:value dictionary.

	get_name() and set_name(value) are created automatically
	for any of the parameters specified in the **kwargs'''

	def __init__(self, *args, **kwargs):
		Observable.__init__(self)
		self.__params = []
		self.__list_params = {}
		self.__object_params = {}
		# For meta-programmability
		self.from_dict(kwargs)

	def get_param_names(self):
		return tuple(self.__params)

	def notify_all(self):
		self.notify_observers(*self.get_param_names())

	def create(self,**kwargs):
		return self.from_dict(kwargs)

	def clone(self, *args, **kwargs):
		return self.__class__(*args, **kwargs).from_dict(self.to_dict())

	def set_list_params(self, **list_params):
		self.__list_params.update(list_params)

	def set_object_params(self, **obj_params):
		self.__object_params.update(obj_params)

	def has_param(self,param):
		return param in self.__params

	def get_param(self,param):
		return getattr(self, param)

	def __getattr__(self, param):
		'''Provides automatic get/set/add/append methods.'''

		# Base case: we actually have this param
		if param in self.__dict__:
			return getattr(self, param)

		# Check for the translated variant of the param
		realparam = self.__translate(param, sep='')
		if realparam in self.__dict__:
			return getattr(self, realparam)

		if realparam.startswith('get'):
			param = self.__translate(param, 'get')
			return lambda: getattr(self, param)

		elif realparam.startswith('set'):
			param = self.__translate(param, 'set')
			return lambda v: self.set_param(param, v,
					check_params=True)

		elif realparam.startswith('add'):
			self.__array = self.__translate(param, 'add')
			return self.__append

		elif realparam.startswith('append'):
			self.__array = self.__translate(param, 'append')
			return self.__append

		errmsg  = ("%s object has no parameter '%s'"
				% (self.__class__.__name__, param))

		raise AttributeError(errmsg)

	def set_param(self, param, value, notify=True, check_params=False):
		'''Set param with optional notification and validity checks.'''

		param = param.lower()
		if check_params and param not in self.__params:
			raise Exception("Parameter '%s' not available for %s"
					% (param, self.__class__.__name__))
		elif param not in self.__params:
			self.__params.append(param)

		setattr(self, param, value)
		if notify: self.notify_observers(param)

	def copy_params(self, model, params=None):
		if params is None:
			params = self.get_param_names()
		for param in params:
			self.set_param(param, model.get_param(param))

	def __append(self, *values):
		'''Appends an arbitrary number of values to
		an array atribute.'''
		array = getattr(self, self.__array)
		if array is None:
			errmsg = "%s object has no parameter '%s'" \
				%( self.__class__.__name__, self.__array )
			raise AttributeError(errmsg)
		else:
			array.extend(values)

	def __translate(self, param, prefix='', sep='_'):
		'''Translates an param name from the external name
		used in methods to those used internally.  The default
		settings strip off '_' so that both get_foo() and getFoo()
		are valid incantations.'''
		return param.lstrip(prefix).lstrip(sep).lower()

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
			warning = ('WARNING: %s not found in %s\n'
					%(modname, classname))
			sys.stderr.write(warning)

		modfile[0].close()
		return cls

	def save(self, filename):
		import simplejson
		file = open(filename, 'w')
		simplejson.dump(self.to_dict(), file, indent=4)
		file.close()

	def load(self, filename):
		import simplejson
		file = open(filename, 'r')
		dict = simplejson.load(file)
		file.close()
		self.from_dict(dict)

	def from_dict(self, source_dict):
		'''Import a complex model from a dictionary.  The import/export
		is clued as to nested Model-objects by setting the
		__list_params or __object_params object specifications.'''
		for param,val in source_dict.iteritems():
			self.set_param(param, self.__param_from_dict(param, val),
				notify=False)
		return self
	
	def __param_from_dict(self,param,val):

		# A list of Model-objects
		if is_list(val):
			if param in self.__list_params:
				# A list of Model-derived objects
				listparam = []
				cls = self.__list_params[param]
				for item in val:
					listparam.append(cls().from_dict(item))
				return listparam

		# A param that maps to a Model-object
		elif is_dict(val):
			if param in self.__object_params:
				# "module.submodule:ClassName"
				cls = self.__object_params[param]
				return cls().from_dict(val)

		# Atoms and uninteresting hashes/dictionaries
		return val

	def to_dict(self):
		'''Exports a model to a dictionary.
		This simplifies serialization.'''
		params = {}
		for param in self.__params:
			params[param] = self.__param_to_dict(param)
		return params

	def __param_to_dict(self, param):
		item = getattr(self, param)
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

	__INDENT__ = 0

	@staticmethod
	def INDENT(i=None):
		if i is not None:
			Model.__INDENT__ += i
		return '\t' * Model.__INDENT__

	def __str__(self):
		'''A convenient, recursively-defined stringification method.'''

		io = StringIO()
		io.write(Model.INDENT())
		io.write(self.__class__.__name__ + '(')

		Model.INDENT(1)

		for param in self.__params:
			if param.startswith('_'): continue
			io.write('\n')

			inner = Model.INDENT() + param + " = "
			value = getattr(self, param)

			if type(value) == ListType:
				indent = Model.INDENT(1)
				io.write(inner + "[\n")
				for val in value:
					if is_model(val):
						io.write(val+'\n')
					else:
						io.write(indent)
						io.write(str(val))
						io.write(",\n")

				io.write(Model.INDENT(-1))
				io.write('],')
			else:
				io.write(inner)
				io.write(str(value))
				io.write(',')

		io.write('\n' + Model.INDENT(-1) + ')')
		value = io.getvalue()
		io.close()
		return value

#############################################################################
#
def is_model(item): return issubclass(item.__class__, Model)
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
	return(is_model(item)
		or type(item) is InstanceType)
