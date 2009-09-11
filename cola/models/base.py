# Copyright (c) 2009 David Aguilar
"""
This module provides the BaseModel class, a generic, serializable
data container.
"""

import os
import imp
import types
from cStringIO import StringIO

import jsonpickle

from cola import core


class BaseModel(object):
    """
    BaseModel is a base class that implements convenient
    serialization methods.
    """
    def __getitem__(self, item):
        """Adds support for retrieving a parameter via model['param'].

        >>> m = BaseModel()
        >>> m.answer = 42
        >>> m['answer']
        42

        """
        return self.__dict__[item]

    def __setitem__(self, item, value):
        """
        Adds support for setting a parameter via model['param'] = value.

        >>> m = BaseModel()
        >>> m['answer'] = 42
        >>> m.answer
        42

        """
        self.__dict__[item] = value

    def __iter__(self):
        """Provides iterator access to a model class.

        This allows you to iterate over a model's parameters as if it
        were a list.

        >>> m = BaseModel()
        >>> m.answer = 42
        >>> key = 'nada'
        >>> for k, v in m: key = k
        >>> key
        'answer'

        >>> m = BaseModel()
        >>> m.answer = 42
        >>> value = 'nada'
        >>> for k, v in m: value = v
        >>> value
        42

        """
        return BaseModelIterator(self)

    def _filter_dict(self, dct):
        """This method removes all items that begin with an underscore.

        >>> m = BaseModel()
        >>> m._filter_dict({'a': 1, '_b': 2, 'c_': 3})
        {'a': 1}

        """
        # Create a set of (key, value) pairs
        included = set([(k, v) for k, v in dct.iteritems()
                                    if not k.startswith('_') and
                                       not k.endswith('_') and
                                       not k.startswith('py/')])
        # Anything left over passed the filter
        filtered = {}
        for k, v in included:
            filtered[k] = v
        return filtered

    def items(self, raw=False):
        """Provides a dictionary-like items() iterator.

        >>> m = BaseModel().from_dict(dict(a='a', b='b'))
        >>> value = 'nada'
        >>> for k, v in m.items(): value = v;
        >>> value
        'b'

        """
        if raw:
            return self.to_dict().items()
        return self._filter_dict(self.to_dict()).items()

    def iteritems(self, raw=False):
        """Provides a dictionary-like iteritems() iterator.

        >>> m = BaseModel().from_dict(dict(a='a', b='b'))
        >>> value = 'nada'
        >>> for k, v in m.iteritems(): value = v;
        >>> value
        'b'

        """
        if raw:
            return self.to_dict().iteritems()
        return self._filter_dict(self.to_dict()).iteritems()

    def param_names(self, export=False):
        """Returns a list of serializable attribute names.

        >>> m = BaseModel()
        >>> m._question = 'unknown'
        >>> m.answer = 42

        >>> m.param_names()
        ['answer']

        >>> m.param_names(export=True)
        ['_question', 'answer']

        """
        names = []
        for k, v in self.__dict__.iteritems():
            if not export and (k.startswith('_') or k.endswith('_') or
                               k.startswith('py/')):
                continue
            if is_function(v):
                continue
            if is_atom(v) or is_list(v) or is_dict(v) or is_model(v):
                names.append(k)
        names.sort()
        return names

    def clone(self):
        """Creates a clone of the current object.

        >>> m = BaseModel()
        >>> m.answer = 42
        >>> clone = m.clone()
        >>> clone.answer
        42

        >>> type(clone)
        <class 'cola.models.base.BaseModel'>

        """
        # Go in and out of jsonpickle to create a clone
        return jsonpickle.decode(jsonpickle.encode(self))

    def has_param(self,param):
        """Returns true if a parameter exists in a model.

        >>> m = BaseModel()
        >>> m.answer = 42
        >>> m.has_param('answer')
        True

        >>> m.has_param('question')
        False

        """
        return param in self.__dict__

    def param(self, param, default=None):
        """Returns the value of a model parameter.

        >>> m = BaseModel()
        >>> m.answer = 42
        >>> m.param('answer')
        42

        >>> m.param('another answer', 42)
        42
        """
        return self.__dict__.get(param, default)

    def __getattr__(self, param):
        """Provides set_<attribute>(value) append methods.

        This provides automatic convenience methods for handling
        setattrs with notification.

        >>> m = BaseModel()
        >>> m.answer = 42
        >>> m.set_answer(41)
        >>> # Observers are notified
        >>> m.answer
        41

        """
        # Base case: we actually have this param
        if param in self.__dict__:
            return getattr(self, param)

        # Return a closure over param for calling set_param;
        # Concrete classes subclass set_param to provide notification
        if param.startswith('set_'):
            return lambda v: self.set_param(param[4:], v)

        errmsg  = ("'%s' object has no attribute '%s'" %
                    (self.__class__.__name__, param))
        raise AttributeError(errmsg)

    def set_param(self, param, value):
        """Wrapper around setattr()

        >>> m = BaseModel()
        >>> m.answer = 41
        >>> m.set_param('answer', 42)
        >>> m.answer
        42

        """
        setattr(self, param, value)

    def copy_params(self, model, params_to_copy=None):
        """Copies params from one model to another.

        >>> m = BaseModel()
        >>> m.answer = 42
        >>> m._question = 'unknown'
        >>> m2 = BaseModel()
        >>> m2.copy_params(m)
        >>> m2._question
        'unknown'

        >>> m2.answer
        42

        """
        # Loop over all attributes and copy them over
        for k in params_to_copy or model.param_names(export=True):
            self[k] = model.param(k)

    def save(self, filename):
        """Saves a model to a file.
        """
        fh = open(filename, 'w')
        jsonpickle.set_encoder_options('simplejson', indent=4)
        try:
            core.write_nointr(fh, jsonpickle.encode(self))
        except:
            pass
        fh.close()
        jsonpickle.set_encoder_options('simplejson', indent=None)

    def load(self, filename):
        """Loads model state from a file.
        """
        fh = open(filename, 'r')
        contents = core.read_nointr(fh)
        fh.close()
        try:
            ddict = jsonpickle.decode(contents)
            return self.from_dict(ddict)
        except:
            pass
        return self

    @staticmethod
    def instance(filename):
        """Instances a model from a filename.
        """
        fh = open(filename, 'r')
        contents = core.read_nointr(fh)
        fh.close()
        obj = jsonpickle.decode(contents)
        if is_dict(obj):
            return BaseModel().from_dict(obj)
        else:
            return obj

    def from_dict(self, source_dict):
        """Import a complex model from a dictionary.
        If it looks like a duck, it's a duck.

        >>> BaseModel().from_dict({'answer': 42}).answer
        42
        """
        # Load parameters in-place
        unpickler = jsonpickle.unpickler.Unpickler()
        obj = unpickler.restore(source_dict)
        if is_model(obj):
            self.copy_params(obj)
        elif is_dict(obj):
            for k, v in obj.iteritems():
                self[k] = unpickler.restore(v)
        return self

    def to_dict(self):
        """
        Exports a model to a dictionary.
        This simplifies serialization.

        >>> is_dict(BaseModel().to_dict())
        True

        """
        return jsonpickle.pickler.Pickler().flatten(self)

    __indent__ = 0
    __preindent__ = True
    __strstack__ = set()

    @staticmethod
    def _indent(i=0):
        BaseModel.__indent__ += i
        return '    ' * BaseModel.__indent__

    def __str__(self):
        """A convenient, recursively-defined stringification method."""
        # This avoid infinite recursion on cyclical structures
        if self in BaseModel.__strstack__:
            return 'self' # TODO: implement references?  This ain't lisp.
        else:
            BaseModel.__strstack__.add(self)
        # IO object for output
        io = StringIO()
        # Handle indentation
        if BaseModel.__preindent__:
            io.write(BaseModel._indent())

        # Class name and opening parenthesis
        io.write(self.__class__.__name__ + '(')

        # Go one level deeper
        BaseModel._indent(1)

        # Output each attribute
        for param in self.param_names():
            if param.startswith('_') or param.endswith('_'):
                continue
            # Go to the next line
            io.write('\n')

            # e.g. foo = bar
            inner = BaseModel._indent() + param + " = "
            value = self[param]

            # Lists use a new line for each item
            if type(value) == types.ListType:
                indent = BaseModel._indent(1)
                io.write(inner + "[\n")
                for val in value:
                    # Nested models need special treatment
                    if is_model(val):
                        io.write(str(val)+'\n')
                    else:
                        io.write(indent)
                        io.write(str(val))
                        io.write(",\n")
                # Unindent, closing bracket
                io.write(BaseModel._indent(-1))
                io.write("],")
            else:
                # It's not a list, so just output its str() representation
                BaseModel.__preindent__ = False
                io.write(inner)
                io.write(str(value))
                io.write(',')
                BaseModel.__preindent__ = True

        # Finish this item, closing parenthesis
        io.write('\n' + BaseModel._indent(-1) + ')')
        value = io.getvalue()
        io.close()

        # Remove ourselves from the recursion-avoidance stack
        BaseModel.__strstack__.remove(self)
        return value


#############################################################################
class BaseModelIterator(object):
    """Provides an iterator over model (key, value) pairs.
    """
    def __init__(self, model):
        self.model = model
        self.params = model.param_names()
        self.idx = -1
    def next(self):
        try:
            self.idx += 1
            name = self.params[self.idx]
            return (name, self.model[name])
        except IndexError:
            raise StopIteration


#############################################################################
def is_model(item):
    """Is this an instance of a BaseModel-like object?"""
    return isinstance(item, BaseModel)

def is_dict(item):
    """Is this an instance of a dictionary?"""
    return type(item) is types.DictType

def is_list(item):
    """Is this a list?"""
    return type(item) is types.ListType or type(item) is types.TupleType

def is_atom(item):
    """Is this an atom?"""
    return(type(item) in types.StringTypes
        or type(item) is types.BooleanType
        or type(item) is types.IntType
        or type(item) is types.LongType
        or type(item) is types.FloatType
        or type(item) is types.ComplexType)

def is_function(item):
    """Is this a function?"""
    return type(item) is types.FunctionType
