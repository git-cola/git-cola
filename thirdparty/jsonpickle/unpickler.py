# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 John Paulett (john -at- paulett.org)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import sys
import jsonpickle.util as util
import jsonpickle.tags as tags
import jsonpickle.handlers as handlers
from jsonpickle.compat import set


class Unpickler(object):
    def __init__(self):
        ## The current recursion depth
        self._depth = 0
        ## Maps reference names to object instances
        self._namedict = {}
        ## The namestack grows whenever we recurse into a child object
        self._namestack = []

    def _reset(self):
        """Resets the object's internal state.
        """
        self._namedict = {}
        self._namestack = []

    def _push(self):
        """Steps down one level in the namespace.
        """
        self._depth += 1

    def _pop(self, value):
        """Step up one level in the namespace and return the value.
        If we're at the root, reset the unpickler's state.
        """
        self._depth -= 1
        if self._depth == 0:
            self._reset()
        return value

    def restore(self, obj):
        """Restores a flattened object to its original python state.

        Simply returns any of the basic builtin types

        >>> u = Unpickler()
        >>> u.restore('hello world')
        'hello world'
        >>> u.restore({'key': 'value'})
        {'key': 'value'}
        """
        self._push()

        if has_tag(obj, tags.REF):
            return self._pop(self._namedict.get(obj[tags.REF]))

        if has_tag(obj, tags.TYPE):
            typeref = loadclass(obj[tags.TYPE])
            if not typeref:
                return self._pop(obj)
            return self._pop(typeref)

        if has_tag(obj, tags.REPR):
            return self._pop(loadrepr(obj[tags.REPR]))

        if has_tag(obj, tags.OBJECT):

            cls = loadclass(obj[tags.OBJECT])
            if not cls:
                return self._pop(obj)

            # check custom handlers
            HandlerClass = handlers.registry.get(cls)
            if HandlerClass:
                handler = HandlerClass(self)
                return self._pop(handler.restore(obj))

            try:
                instance = object.__new__(cls)
            except TypeError:
                # old-style classes
                try:
                    instance = cls()
                except TypeError:
                    # fail gracefully if the constructor requires arguments
                    self._mkref(obj)
                    return self._pop(obj)

            # keep a obj->name mapping for use in the _isobjref() case
            self._mkref(instance)

            if hasattr(instance, '__setstate__') and has_tag(obj, tags.STATE):
                state = self.restore(obj[tags.STATE])
                instance.__setstate__(state)
                return self._pop(instance)

            for k, v in obj.iteritems():
                # ignore the reserved attribute
                if k in tags.RESERVED:
                    continue
                self._namestack.append(k)
                # step into the namespace
                value = self.restore(v)
                if (util.is_noncomplex(instance) or
                        util.is_dictionary_subclass(instance)):
                    instance[k] = value
                else:
                    setattr(instance, k, value)
                # step out
                self._namestack.pop()

            # Handle list and set subclasses
            if has_tag(obj, tags.SEQ):
                if hasattr(instance, 'append'):
                    for v in obj[tags.SEQ]:
                        instance.append(self.restore(v))
                if hasattr(instance, 'add'):
                    for v in obj[tags.SEQ]:
                        instance.add(self.restore(v))

            return self._pop(instance)

        if util.is_list(obj):
            return self._pop([self.restore(v) for v in obj])

        if has_tag(obj, tags.TUPLE):
            return self._pop(tuple([self.restore(v) for v in obj[tags.TUPLE]]))

        if has_tag(obj, tags.SET):
            return self._pop(set([self.restore(v) for v in obj[tags.SET]]))

        if util.is_dictionary(obj):
            data = {}
            for k, v in obj.iteritems():
                self._namestack.append(k)
                data[k] = self.restore(v)
                self._namestack.pop()
            return self._pop(data)

        return self._pop(obj)

    def _refname(self):
        """Calculates the name of the current location in the JSON stack.

        This is called as jsonpickle traverses the object structure to
        create references to previously-traversed objects.  This allows
        cyclical data structures such as doubly-linked lists.
        jsonpickle ensures that duplicate python references to the same
        object results in only a single JSON object definition and
        special reference tags to represent each reference.

        >>> u = Unpickler()
        >>> u._namestack = []
        >>> u._refname()
        '/'

        >>> u._namestack = ['a']
        >>> u._refname()
        '/a'

        >>> u._namestack = ['a', 'b']
        >>> u._refname()
        '/a/b'

        """
        return '/' + '/'.join(self._namestack)

    def _mkref(self, obj):
        """
        >>> from samples import Thing
        >>> thing = Thing('referenced-thing')
        >>> u = Unpickler()
        >>> u._mkref(thing)
        '/'
        >>> u._namedict['/']
        samples.Thing("referenced-thing")

        """
        name = self._refname()
        if name not in self._namedict:
            self._namedict[name] = obj
        return name

def loadclass(module_and_name):
    """Loads the module and returns the class.

    >>> loadclass('samples.Thing')
    <class 'samples.Thing'>

    >>> loadclass('example.module.does.not.exist.Missing')


    >>> loadclass('samples.MissingThing')


    """
    try:
        module, name = module_and_name.rsplit('.', 1)
        __import__(module)
        return getattr(sys.modules[module], name)
    except:
        return None

def loadrepr(reprstr):
    """Returns an instance of the object from the object's repr() string.
    It involves the dynamic specification of code.

    >>> from jsonpickle import tags
    >>> loadrepr('samples/samples.Thing("json")')
    samples.Thing("json")

    """
    module, evalstr = reprstr.split('/')
    mylocals = locals()
    localname = module
    if '.' in localname:
        localname = module.split('.', 1)[0]
    mylocals[localname] = __import__(module)
    return eval(evalstr)

def has_tag(obj, tag):
    """Helper class that tests to see if the obj is a dictionary
    and contains a particular key/tag.

    >>> obj = {'test': 1}
    >>> has_tag(obj, 'test')
    True
    >>> has_tag(obj, 'fail')
    False

    >>> has_tag(42, 'fail')
    False

    """
    return type(obj) is dict and tag in obj
