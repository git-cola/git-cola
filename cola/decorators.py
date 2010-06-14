__all__ = ('decorator', 'deprecated', 'memoize')


def decorator(caller, func=None):
    """
    decorator(caller) converts a caller function into a decorator;
    decorator(caller, func) decorates a function using a caller.
    """
    if func is None: # returns a decorator
        def _decorator(f, *args, **opts):
            def _caller(*args, **opts):
                return caller(f, *args, **opts)
            return _caller
        return _decorator

    else: # returns a decorated function
        def _decorator(*args, **opts):
            return caller(func, *args, **opts)
        return _decorator


@decorator
def deprecated(func, *args, **kw):
    "A decorator for deprecated functions"
    import warnings
    warnings.warn('Calling deprecated function %r' % func.__name__,
                  DeprecationWarning, stacklevel=3)
    return func(*args, **kw)


def memoize(func):
    """
    A decorator for memoizing function calls

    http://en.wikipedia.org/wiki/Memoization

    """
    func.cache = {}
    return decorator(_memoize, func)


def _memoize(func, *args, **opts):
    """Implements memoized cache lookups"""
    if opts: # frozenset is used to ensure hashability
        key = args, frozenset(opts.items())
    else:
        key = args
    cache = func.cache # attribute added by memoize
    try:
        return cache[key]
    except KeyError:
        cache[key] = result = func(*args, **opts)
        return result
