from __future__ import absolute_import, division, print_function, unicode_literals

from cola.models import selection

from .helper import Mock


def test_union():
    t = Mock()
    t.staged = ['a']
    t.unmerged = ['a', 'b']
    t.modified = ['b', 'a', 'c']
    t.untracked = ['d']

    expect = ['a', 'b', 'c', 'd']
    actual = selection.union(t)
    assert expect == actual
