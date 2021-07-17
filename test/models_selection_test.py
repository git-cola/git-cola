from __future__ import absolute_import, division, unicode_literals

import mock

from cola.models import selection


def test_union():
    t = mock.Mock()
    t.staged = ['a']
    t.unmerged = ['a', 'b']
    t.modified = ['b', 'a', 'c']
    t.untracked = ['d']

    expect = ['a', 'b', 'c', 'd']
    actual = selection.union(t)
    assert expect == actual
