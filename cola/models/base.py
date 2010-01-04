# Copyright (c) 2009 David Aguilar
"""Provides a serializable data container"""
import types
import copy

from cola import serializer
from cola.compat import set

class BaseModel(object):
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
            if is_atom(v) or is_dict(v) or is_seq(v):
                if k.strip('_') != k:
                    if not export:
                        continue
                names.append(k)
        names.sort()
        return names

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
            self.__dict__[k] = copy.copy(model.__dict__[k])


def is_dict(item):
    return type(item) is types.DictType


def is_seq(item):
    return (type(item) is types.ListType or
            type(item) is types.TupleType or
            type(item) is set)

def is_atom(item):
    return(item is None or
        type(item) in types.StringTypes or
        type(item) is types.BooleanType or
        type(item) is types.IntType or
        type(item) is types.LongType or
        type(item) is types.FloatType or
        type(item) is types.ComplexType)
