#!/usr/bin/env python
from __future__ import absolute_import, division, unicode_literals

import pytest

from cola import display


def test_shorten_paths():
    paths = (
        '/usr/src/git-cola/src',
        '/usr/src/example/src',
        '/usr/src/super/lib/src',
        '/usr/src/super/tools/src',
        '/usr/src/super/example/src',
        '/lib/src',
    )
    actual = display.shorten_paths(paths)
    assert actual[paths[0]] == 'git-cola/src'
    assert actual[paths[1]] == 'src/example/src'
    assert actual[paths[2]] == 'super/lib/src'
    assert actual[paths[3]] == 'tools/src'
    assert actual[paths[4]] == 'super/example/src'
    assert actual[paths[5]] == '/lib/src'


if __name__ == '__main__':
    pytest.main([__file__])
