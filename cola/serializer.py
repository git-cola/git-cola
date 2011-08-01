"""Provides a serializer for arbitrary Python objects"""
import jsonpickle
jsonpickle.set_encoder_options('simplejson', indent=4)

from cola import utils

handlers = {}


def save(obj, path):
    utils.write(path, encode(obj))


def load(path):
    return decode(utils.slurp(path))


def clone(obj):
    # Go in and out of encode/decode to return a clone
    return decode(encode(obj))


def encode(obj):
    handler = _gethandler(obj)
    if handler:
        handler.pre_encode_hook()
    jsonstr = jsonpickle.encode(obj)
    if handler:
        handler.post_encode_hook()
    return jsonstr


def decode(jsonstr):
    obj = jsonpickle.decode(jsonstr)
    handler = _gethandler(obj)
    if handler:
        handler.post_decode_hook()
    return obj


def _gethandler(obj):
    cls = type(obj)
    # Allow base classes to provide a serialization handlers
    # for their subclasses
    if hasattr(cls, 'mro'):
        for supercls in cls.mro():
            if supercls in handlers:
                return handlers[supercls](obj)
    if cls in handlers:
        return handlers[cls](obj)
    return None
