# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 John Paulett (john -at- 7oars.com)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Python library for serializing any arbitrary object graph into
`JSON <http://www.json.org/>`_.  It can take almost any Python object and turn
the object into JSON.  Additionally, it can reconstitute the object back into
Python.

    >>> import jsonpickle
    >>> from jsonpickle.tests.classes import Thing

Create an object.

    >>> obj = Thing('A String')
    >>> print obj.name
    A String

Use jsonpickle to transform the object into a JSON string.

    >>> pickled = jsonpickle.encode(obj)
    >>> print pickled
    {"py/object": "jsonpickle.tests.classes.Thing", "name": "A String", "child": null}

Use jsonpickle to recreate a Python object from a JSON string

    >>> unpickled = jsonpickle.decode(pickled)
    >>> str(unpickled.name)
    'A String'

.. warning::

    Loading a JSON string from an untrusted source represents a potential
    security vulnerability.  jsonpickle makes no attempt to sanitize the input.

The new object has the same type and data, but essentially is now a copy of
the original.

    >>> obj == unpickled
    False
    >>> obj.name == unpickled.name
    True
    >>> type(obj) == type(unpickled)
    True

If you will never need to load (regenerate the Python class from JSON), you can
pass in the keyword unpicklable=False to prevent extra information from being
added to JSON.

    >>> oneway = jsonpickle.encode(obj, unpicklable=False)
    >>> print oneway
    {"name": "A String", "child": null}

"""

from jsonpickle.pickler import Pickler
from jsonpickle.unpickler import Unpickler

__version__ = '0.2.0'
__all__ = ('encode', 'decode')


class JSONPluginMgr(object):
    """The JSONPluginMgr handles encoding and decoding.

    It tries these modules in this order:
        cjson, json, simplejson, demjson

    cjson is the fastest, and is tried first.
    json comes with python2.6 and is tried second.
    simplejson is a very popular backend and is tried third.
    demjson is the most permissive backend and is tried last.
    """
    def __init__(self):
        ## The names of backends that have been successfully imported
        self._backend_names = []

        ## A dictionary mapping backend names to encode/decode functions
        self._encoders = {}
        self._decoders = {}

        ## Options to pass to specific encoders
        self._encoder_options = {}

        ## The exception class that is thrown when a decoding error occurs
        self._decoder_exceptions = {}

        ## Whether we've loaded any backends successfully
        self._verified = False

        ## Try loading cjson, simplejson and demjson
        self.load_backend('cjson', 'encode', 'decode', 'DecodeError')
        self.load_backend('json', 'dumps', 'loads', ValueError)
        self.load_backend('simplejson', 'dumps', 'loads', ValueError)
        self.load_backend('demjson', 'encode', 'decode', 'JSONDecodeError')

    def _verify(self):
        """Ensures that we've loaded at least one JSON backend.
        """
        if self._verified:
            return
        raise AssertionError('jsonpickle requires at least one of the '
                             'following:\n'
                             '    cjson, python2.6, simplejson, or demjson')

    def load_backend(self, name, encode_name, decode_name, decode_exc):
        """Loads a backend by name.

        This method loads a backend and sets up references to that
        backend's encode/decode functions and exception classes.

        encode_name is the name of the backend's encode method.
        The method should take an object and return a string.

        decode_name names the backend's method for the reverse
        operation -- returning a Python object from a string.

        decode_exc can be either the name of the exception class
        used to denote decoding errors, or it can be a direct reference
        to the appropriate exception class itself.  If it is a name,
        then the assumption is that an exception class of that name
        can be found in the backend module's namespace.
        """
        try:
            ## Load the JSON backend
            mod = __import__(name)
        except ImportError:
            return

        try:
            ## Handle submodules, e.g. django.utils.simplejson
            components = name.split('.')
            for comp in components[1:]:
                mod = getattr(mod, comp)
        except AttributeError:
            return

        try:
            ## Setup the backend's encode/decode methods
            self._encoders[name] = getattr(mod, encode_name)
            self._decoders[name] = getattr(mod, decode_name)
        except AttributeError:
            self.remove_backend(name)
            return

        try:
            if type(decode_exc) is str:
                ## This backend's decoder exception is part of the backend
                self._decoder_exceptions[name] = getattr(mod, decode_exc)
            else:
                ## simplejson uses the ValueError exception
                self._decoder_exceptions[name] = decode_exc
        except AttributeError:
            self.remove_backend(name)
            return

        ## Setup the default args and kwargs for this encoder
        self._encoder_options[name] = ([], {})

        ## Add this backend to the list of candidate backends
        self._backend_names.append(name)

        ## Indicate that we successfully loaded a JSON backend
        self._verified = True

    def remove_backend(self, name):
        """Removes all entries for a particular backend.
        """
        self._encoders.pop(name, None)
        self._decoders.pop(name, None)
        self._decoder_exceptions.pop(name, None)
        self._encoder_options.pop(name, None)
        if name in self._backend_names:
            self._backend_names.remove(name)
        self._verified = bool(self._backend_names)

    def encode(self, obj):
        """Attempts to encode an object into JSON.

        This tries the loaded backends in order and passes along the last
        exception if no backend is able to encode the object.
        """
        self._verify()
        for idx, name in enumerate(self._backend_names):
            try:
                optargs, kwargs = self._encoder_options[name]
                args = (obj,) + tuple(optargs)
                return self._encoders[name](*args, **kwargs)
            except:
                if idx == len(self._backend_names) - 1:
                    raise

    def decode(self, string):
        """Attempts to decode an object from a JSON string.

        This tries the loaded backends in order and passes along the last
        exception if no backends are able to decode the string.
        """
        self._verify()
        for idx, name in enumerate(self._backend_names):
            try:
                return self._decoders[name](string)
            except self._decoder_exceptions[name], e:
                if idx == len(self._backend_names) - 1:
                    raise e
                else:
                    pass # and try a more forgiving encoder, e.g. demjson

    def set_preferred_backend(self, name):
        """Sets the preferred json backend.

        If a preferred backend is set then jsonpickle tries to use it
        before any other backend.

        For example,
            set_preferred_backend('simplejson')

        If the backend is not one of the built-in jsonpickle backends
        (cjson, json/simplejson, or demjson) then you must load the
        backend prior to calling set_preferred_backend.  An AssertionError
        exception is raised if the backend has not been loaded.
        """
        if name in self._backend_names:
            self._backend_names.remove(name)
            self._backend_names.insert(0, name)
        else:
            errmsg = 'The "%s" backend has not been loaded.' % name
            raise AssertionError(errmsg)

    def set_encoder_options(self, name, *args, **kwargs):
        """Associates encoder-specific options with an encoder.

        After calling set_encoder_options, any calls to jsonpickle's
        encode method will pass the supplied args and kwargs along to
        the appropriate backend's encode method.

        For example,
            set_encoder_options('simplejson', sort_keys=True, indent=4)
            set_encoder_options('demjson', compactly=False)

        See the appropriate encoder's documentation for details about
        the supported arguments and keyword arguments.
        """
        self._encoder_options[name] = (args, kwargs)

# Initialize a JSONPluginMgr
json = JSONPluginMgr()

# Export specific JSONPluginMgr methods into the jsonpickle namespace
set_preferred_backend = json.set_preferred_backend
set_encoder_options = json.set_encoder_options
load_backend = json.load_backend
remove_backend = json.remove_backend


def encode(value, unpicklable=True, max_depth=None, **kwargs):
    """Returns a JSON formatted representation of value, a Python object.

    The keyword argument 'unpicklable' defaults to True.
    If set to False, the output will not contain the information
    necessary to turn the JSON data back into Python objects.

    The keyword argument 'max_depth' defaults to None.
    If set to a non-negative integer then jsonpickle will not recurse
    deeper than 'max_depth' steps into the object.  Anything deeper
    than 'max_depth' is represented using a Python repr() of the object.

    >>> encode('my string')
    '"my string"'
    >>> encode(36)
    '36'

    >>> encode({'foo': True})
    '{"foo": true}'

    >>> encode({'foo': True}, max_depth=0)
    '"{\\'foo\\': True}"'

    >>> encode({'foo': True}, max_depth=1)
    '{"foo": "True"}'


    """
    j = Pickler(unpicklable=unpicklable,
                max_depth=max_depth)
    return json.encode(j.flatten(value))

def decode(string):
    """Converts the JSON string into a Python object.

    >>> str(decode('"my string"'))
    'my string'
    >>> decode('36')
    36
    """
    j = Unpickler()
    return j.restore(json.decode(string))
