try:
    set = set
except NameError:
    from sets import Set as set
    set = set

try:
    import hashlib
except ImportError:
    import md5
    class hashlib(object):
        @staticmethod
        def new(*args):
            return md5.new()
