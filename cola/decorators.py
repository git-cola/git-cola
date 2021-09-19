from __future__ import absolute_import, division, print_function, unicode_literals
import errno
import functools


__all__ = ('decorator', 'memoize', 'interruptable')


def decorator(caller, func=None):
    """
    Create a new decorator

    decorator(caller) converts a caller function into a decorator;
    decorator(caller, func) decorates a function using a caller.

    """
    if func is None:
        # return a decorator
        # pylint: disable=unused-argument
        @functools.wraps(caller)
        def _decorator(f, *dummy_args, **dummy_opts):
            @functools.wraps(f)
            def _caller(*args, **opts):
                return caller(f, *args, **opts)

            return _caller

        _decorator.func = caller
        return _decorator

    # return a decorated function
    @functools.wraps(func)
    def _decorated(*args, **opts):
        return caller(func, *args, **opts)

    _decorated.func = func
    return _decorated


def memoize(func):
    """
    A decorator for memoizing function calls

    http://en.wikipedia.org/wiki/Memoization

    """
    func.cache = {}
    return decorator(_memoize, func)


def _memoize(func, *args, **opts):
    """Implements memoized cache lookups"""
    if opts:  # frozenset is used to ensure hashability
        key = (args, frozenset(list(opts.items())))
    else:
        key = args
    cache = func.cache  # attribute added by memoize
    try:
        result = cache[key]
    except KeyError:
        result = cache[key] = func(*args, **opts)
    return result


@decorator
def interruptable(func, *args, **opts):
    """Handle interruptible system calls

    OSX and others are known to interrupt system calls

        http://en.wikipedia.org/wiki/PCLSRing
        http://en.wikipedia.org/wiki/Unix_philosophy#Worse_is_better

    The @interruptable decorator handles this situation

    """
    while True:
        try:
            result = func(*args, **opts)
        except (IOError, OSError) as e:
            if e.errno in (errno.EINTR, errno.EINVAL):
                continue
            raise e
        else:
            break
    return result
