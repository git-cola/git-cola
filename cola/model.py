#!/usr/bin/env python
# Copyright (c) 2008 David Aguilar
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
from types import FunctionType

class Observable(object):
    """Handles subject/observer notifications."""
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

class ModelIterator(object):
    """Provides an iterator over model (key, value) pairs.
    """
    def __init__(self, model):
        self.model = model
        self.params = model.get_param_names()
        self.idx = -1
    def next(self):
        try:
            self.idx += 1
            name = self.params[self.idx]
            return (name, self.model[name])
        except IndexError:
            raise StopIteration

class Model(Observable):
    """Creates a generic model object with params specified
    as a name:value dictionary.

    get_name() and set_name(value) are created automatically
    for any of the parameters specified in the **kwargs"""

    def __init__(self, *args, **kwargs):
        Observable.__init__(self)
        self.from_dict(kwargs)
        self.init()

    def init(self):
        """init() is called by the built-in constructor.
        Subclasses should implement this if necessary."""
        pass

    def __getitem__(self, item):
        return self.__dict__[item]

    def __iter__(self):
        return ModelIterator(self)

    def items(self):
        d = self.to_dict()
        d.pop('__class__', None)
        return d.items()

    def iteritems(self):
        d = self.to_dict()
        d.pop('__class__', None)
        return d.iteritems()

    def create(self,**kwargs):
        return self.from_dict(kwargs)

    def get_param_names(self):
        """Returns a list of serializable attribute names."""
        names = []
        for k, v in self.__dict__.iteritems():
            if k[0] == '_' or is_function(v):
                continue
            if is_atom(v) or is_list(v) or is_dict(v) or is_model(v):
                names.append(k)
        names.sort()
        return names

    def notify_all(self):
        self.notify_observers(*self.get_param_names())

    def clone(self, *args, **kwargs):
        return self.__class__(*args, **kwargs).from_dict(self.to_dict())

    def has_param(self,param):
        return param in self.get_param_names()

    def get_param(self,param):
        return getattr(self, param)

    def __getattr__(self, param):
        """Provides automatic get/set/add/append methods."""

        # Base case: we actually have this param
        if param in self.__dict__:
            return getattr(self, param)

        # Check for the translated variant of the param
        realparam = self.__translate(param, sep='')
        if realparam in self.__dict__:
            return getattr(self, realparam)

        if realparam.startswith("get"):
            param = self.__translate(param, "get")
            return lambda: getattr(self, param)

        elif realparam.startswith("set"):
            param = self.__translate(param, "set")
            return lambda v: self.set_param(param, v,
                                            check_params=True)

        elif (realparam.startswith("add") or realparam.startswith("append")):
            if realparam.startswith("add"):
                param = self.__translate(realparam, "add")
            else:
                param = self.__translate(realparam, "append")

            def array_append(*values):
                array = getattr(self, param)
                if array is None:
                    classnm = self.__class__.__name__
                    errmsg = ("%s object has no array named '%s'"
                            %( classnm, param ))
                    raise AttributeError(errmsg)
                else:
                    array.extend(values)
            # Cache the function definition
            setattr(self, realparam, array_append)
            return array_append

        errmsg  = ("%s object has no parameter '%s'"
                   % (self.__class__.__name__, param))

        raise AttributeError(errmsg)

    def set_param(self, param, value, notify=True, check_params=False):
        """Set param with optional notification and validity checks."""

        param = param.lower()
        if check_params and param not in self.get_param_names():
            raise AttributeError("Parameter '%s' not available for %s"
                                 % (param, self.__class__.__name__))
        setattr(self, param, value)
        if notify:
            self.notify_observers(param)

    def copy_params(self, model, params=None):
        if params is None:
            params = self.get_param_names()
        for param in params:
            self.set_param(param, model.get_param(param))

    def __translate(self, param, prefix='', sep='_'):
        """Translates an param name from the external name
        used in methods to those used internally.  The default
        settings strip off '_' so that both get_foo() and getFoo()
        are valid incantations."""
        return param[len(prefix):].lstrip(sep).lower()

    def save(self, filename):
        if not has_json():
            return
        import simplejson
        file = open(filename, 'w')
        simplejson.dump(self.to_dict(), file, indent=4)
        file.close()

    def load(self, filename):
        if not has_json():
            return
        import simplejson
        file = open(filename, 'r')
        ddict = simplejson.load(file)
        file.close()
        if "__class__" in ddict:
            # load params in-place.
            del ddict["__class__"]
        return self.from_dict(ddict)

    @staticmethod
    def instance(filename):
        if not has_json():
            return
        import simplejson
        file = open(filename, 'r')
        ddict = simplejson.load(file)
        file.close()
        if "__class__" in ddict:
            cls = Model.str_to_class(ddict["__class__"])
            del ddict["__class__"]
            return cls().from_dict(ddict)
        else:
            return Model().from_dict(ddict)

    def from_dict(self, source_dict):
        """Import a complex model from a dictionary.
        We store class information in the __class__ variable.
        If it looks like a duck, it's a duck."""

        if "__class__" in source_dict:
            clsstr = source_dict["__class__"]
            del source_dict["__class__"]
            cls = Model.str_to_class(clsstr)
            return cls().from_dict(source_dict)

        # Not initiating a clone: load parameters in-place
        for param, val in source_dict.iteritems():
            self.set_param(param,
                           self.__obj_from_value(val),
                           notify=False)
        return self

    def __obj_from_value(self, val):
        # Atoms
        if is_atom(val):
            return val

        # Possibly nested lists
        elif is_list(val):
            return [ self.__obj_from_value(v) for v in val ]

        elif is_dict(val):
            # A param that maps to a Model-object
            if "__class__" in val:
                clsstr = val["__class__"]
                cls = Model.str_to_class(clsstr)
                del val["__class__"]
                return cls().from_dict(val)
            newdict = {}
            for k, v in val.iteritems():
                newdict[k] = self.__obj_from_value(v)
            return newdict

        # All others
        return val

    def to_dict(self):
        """
        Exports a model to a dictionary.
        This simplifies serialization.
        """
        params = {"__class__": Model.class_to_str(self)}
        for param in self.get_param_names():
            params[param] = self.__obj_to_value(getattr(self, param))
        return params

    def __obj_to_value(self, item):
        if is_atom(item):
            return item

        elif is_list(item):
            newlist = [ self.__obj_to_value(i) for i in item ]
            return newlist

        elif is_dict(item):
            newdict = {}
            for k,v in item.iteritems():
                newdict[k] = self.__obj_to_value(v)
            return newdict

        elif is_model(item):
            return item.to_dict()

        else:
            raise NotImplementedError("Unknown type:" + str(type(item)))

    __INDENT__ = 0
    __PREINDENT__ = True
    __STRSTACK__ = []

    @staticmethod
    def INDENT(i=0):
        Model.__INDENT__ += i
        return '    ' * Model.__INDENT__

    def __str__(self):
        """A convenient, recursively-defined stringification method."""

        # This avoid infinite recursion on cyclical structures
        if self in Model.__STRSTACK__:
            return 'REFERENCE' # TODO: implement references?  This ain't lisp.
        else:
            Model.__STRSTACK__.append(self)

        io = StringIO()

        if Model.__PREINDENT__:
            io.write(Model.INDENT())

        io.write(self.__class__.__name__ + '(')

        Model.INDENT(1)

        for param in self.get_param_names():
            if param.startswith('_'):
                continue
            io.write('\n')

            inner = Model.INDENT() + param + " = "
            value = getattr(self, param)

            if type(value) == ListType:
                indent = Model.INDENT(1)
                io.write(inner + "[\n")
                for val in value:
                    if is_model(val):
                        io.write(str(val)+'\n')
                    else:
                        io.write(indent)
                        io.write(str(val))
                        io.write(",\n")

                io.write(Model.INDENT(-1))
                io.write("],")
            else:
                Model.__PREINDENT__ = False
                io.write(inner)
                io.write(str(value))
                io.write(',')
                Model.__PREINDENT__ = True

        io.write('\n' + Model.INDENT(-1) + ')')
        value = io.getvalue()
        io.close()

        Model.__STRSTACK__.remove(self)
        return value

    @staticmethod
    def str_to_class(clstr):
        items = clstr.split('.')
        modules = items[:-1]
        classname = items[-1]
        path = None
        module = None
        for mod in modules:
            search = imp.find_module(mod, path)
            try:
                module = imp.load_module(mod, *search)
                if hasattr(module, "__path__"):
                    path = module.__path__
            finally:
                if search and search[0]:
                    search[0].close()
        if module:
            return getattr(module, classname)
        else:
            raise Exception("No class found for: %s" % clstr)

    @staticmethod
    def class_to_str(instance):
        modname = instance.__module__
        classname = instance.__class__.__name__
        return "%s.%s" % (modname, classname)


#############################################################################
def has_json():
    try:
        import simplejson
        return True
    except ImportError:
        print "Unable to import simplejson." % action
        print "You do not have simplejson installed."
        print "try: sudo apt-get install simplejson"
        return False

#############################################################################
def is_model(item):
    return issubclass(item.__class__, Model)
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
def is_function(item):
    return type(item) is FunctionType
