"""Test the textwrap module"""
# pylint: disable=redefined-outer-name
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from cola import textwrap


class WordWrapDefaults(object):
    def __init__(self):
        self.tabwidth = 8
        self.limit = None

    def wrap(self, text, break_on_hyphens=True):
        return textwrap.word_wrap(
            text, self.tabwidth, self.limit, break_on_hyphens=break_on_hyphens
        )


@pytest.fixture
def wordwrap():
    """Provide default word wrap options for tests"""
    return WordWrapDefaults()


def test_word_wrap(wordwrap):
    wordwrap.limit = 16
    text = """
12345678901 3 56 8 01 3 5 7

1 3 5"""
    expect = """
12345678901 3 56
8 01 3 5 7

1 3 5"""
    assert expect == wordwrap.wrap(text)


def test_word_wrap_dashes(wordwrap):
    wordwrap.limit = 4
    text = '123-5'
    expect = '123-5'
    assert expect == wordwrap.wrap(text)


def test_word_wrap_leading_spaces(wordwrap):
    wordwrap.limit = 4
    expect = '1234\n5'

    assert expect == wordwrap.wrap('1234 5')
    assert expect == wordwrap.wrap('1234  5')
    assert expect == wordwrap.wrap('1234   5')
    assert expect == wordwrap.wrap('1234    5')
    assert expect == wordwrap.wrap('1234     5')

    expect = '123\n4'
    assert expect == wordwrap.wrap('123 4')
    assert expect == wordwrap.wrap('123  4')
    assert expect == wordwrap.wrap('123   4')
    assert expect == wordwrap.wrap('123    4')
    assert expect == wordwrap.wrap('123     4')


def test_word_wrap_double_dashes(wordwrap):
    wordwrap.limit = 4
    text = '12--5'
    expect = '12--\n5'
    actual = wordwrap.wrap(text, break_on_hyphens=True)
    assert expect == actual

    expect = '12--5'
    actual = wordwrap.wrap(text, break_on_hyphens=False)
    assert expect == actual


def test_word_wrap_many_lines(wordwrap):
    wordwrap.limit = 2
    text = """
aa


bb cc dd"""

    expect = """
aa


bb
cc
dd"""
    actual = wordwrap.wrap(text)
    assert expect == actual


def test_word_python_code(wordwrap):
    wordwrap.limit = 78
    text = """
if True:
    print "hello world"
else:
    print "hello world"

"""
    expect = text
    actual = wordwrap.wrap(text)
    assert expect == actual


def test_word_wrap_spaces(wordwrap):
    wordwrap.limit = 2
    text = ' ' * 6
    expect = ''
    actual = wordwrap.wrap(text)
    assert expect == actual


def test_word_wrap_special_tag(wordwrap):
    wordwrap.limit = 2
    text = """
This test is so meta, even this sentence

Cheered-on-by: Avoids word-wrap
C.f. This also avoids word-wrap
References: This also avoids word-wrap
See-also: This also avoids word-wrap
Related-to: This also avoids word-wrap
Link: This also avoids word-wrap
"""

    expect = """
This
test
is
so
meta,
even
this
sentence

Cheered-on-by: Avoids word-wrap
C.f. This also avoids word-wrap
References: This also avoids word-wrap
See-also: This also avoids word-wrap
Related-to: This also avoids word-wrap
Link: This also avoids word-wrap
"""
    actual = wordwrap.wrap(text)
    assert expect == actual


def test_word_wrap_space_at_start_of_wrap(wordwrap):
    inputs = """0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 """
    expect = """0 1 2 3 4 5 6 7 8 9\n0 1 2 3 4 5 6 7 8"""
    wordwrap.limit = 20

    actual = wordwrap.wrap(inputs)
    assert expect == actual


def test_word_wrap_keeps_tabs_at_start(wordwrap):
    inputs = """\tfirst line\n\n\tsecond line"""
    expect = """\tfirst line\n\n\tsecond line"""
    wordwrap.limit = 20

    actual = wordwrap.wrap(inputs)
    assert expect == actual


def test_word_wrap_keeps_twospace_indents(wordwrap):
    inputs = """first line\n\n* branch:\n  line1\n  line2\n"""
    expect = """first line\n\n* branch:\n  line1\n  line2\n"""
    wordwrap.limit = 20

    actual = wordwrap.wrap(inputs)
    assert expect == actual


def test_word_wrap_ranges():
    text = 'a bb ccc dddd\neeeee'
    expect = 'a\nbb\nccc\ndddd\neeeee'
    actual = textwrap.word_wrap(text, 8, 2)
    assert expect == actual

    expect = 'a bb\nccc\ndddd\neeeee'
    actual = textwrap.word_wrap(text, 8, 4)
    assert expect == actual

    text = 'a bb ccc dddd\n\teeeee'
    expect = 'a bb\nccc\ndddd\n\t\neeeee'
    actual = textwrap.word_wrap(text, 8, 4)
    assert expect == actual


def test_triplets():
    text = 'xx0 xx1 xx2 xx3 xx4 xx5 xx6 xx7 xx8 xx9 xxa xxb'

    expect = 'xx0 xx1 xx2 xx3 xx4 xx5 xx6\nxx7 xx8 xx9 xxa xxb'
    actual = textwrap.word_wrap(text, 8, 27)
    assert expect == actual

    expect = 'xx0 xx1 xx2 xx3 xx4 xx5\nxx6 xx7 xx8 xx9 xxa xxb'
    actual = textwrap.word_wrap(text, 8, 26)
    assert expect == actual

    actual = textwrap.word_wrap(text, 8, 25)
    assert expect == actual

    actual = textwrap.word_wrap(text, 8, 24)
    assert expect == actual

    actual = textwrap.word_wrap(text, 8, 23)
    assert expect == actual

    expect = 'xx0 xx1 xx2 xx3 xx4\nxx5 xx6 xx7 xx8 xx9\nxxa xxb'
    actual = textwrap.word_wrap(text, 8, 22)
    assert expect == actual
