from __future__ import absolute_import, division, unicode_literals


class Node(object):
    name = 'Not Set'
    full_path = None
    is_staged = None

    def __init__(self, name, **params):
        self.__dict__.update(params, name=name)

    def __repr__(self):
        return '<%s=%s>' % (
            self.__class__.__name__,
            self.name,
        )

    def __eq__(self, other):
        return (
            self.full_path == other.full_path and
            self.is_staged == other.is_staged and
            type(self) == type(other)
        )


class Folder(Node, dict):
    def __repr__(self):
        chs = [
            str(ch)
            for ch in self.values()
        ]
        return '<%s=%s [%s]>' % (
            self.__class__.__name__,
            self.name,
            ', '.join(chs),
        )


class File(Node):
    pass


class Modified(File):
    pass


class Untracked(File):
    pass


class Deleted(File):
    pass


class Unmerged(File):
    pass
