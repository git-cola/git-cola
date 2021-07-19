from __future__ import absolute_import, division, print_function, unicode_literals

from cola import compat
from cola import core
from cola import icons


def test_from_filename_unicode():
    filename = compat.uchr(0x400) + '.py'
    expect = 'file-code.svg'
    actual = icons.basename_from_filename(filename)
    assert expect == actual

    actual = icons.basename_from_filename(core.encode(filename))
    assert expect == actual
