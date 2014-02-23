#!/usr/bin/env python
from __future__ import unicode_literals

import unittest
from cola import textwrap


class WordWrapTestCase(unittest.TestCase):
    def setUp(self):
        self.tabwidth = 8
        self.limit = None

    def wrap(self, text):
        return textwrap.word_wrap(text, self.tabwidth, self.limit)

    def test_word_wrap(self):
        self.limit = 16
        text = """
12345678901 3 56 8 01 3 5 7

1 3 5"""
        expect = """
12345678901 3 56
8 01 3 5 7

1 3 5"""
        self.assertEqual(expect, self.wrap(text))

    def test_word_wrap_dashes(self):
        self.limit = 4
        text = '123-5'
        expect = '123-5'
        self.assertEqual(expect, self.wrap(text))

    def test_word_wrap_double_dashes(self):
        self.limit = 4
        text = '12--5'
        expect = '12--\n5'
        self.assertEqual(expect, self.wrap(text))

    def test_word_wrap_many_lines(self):
        self.limit = 2
        text = """
aa


bb cc dd"""
        expect = """
aa


bb
cc
dd"""
        self.assertEqual(expect, self.wrap(text))

    def test_word_python_code(self):
        self.limit = 78
        text = """
if True:
    print "hello world"
else:
    print "hello world"

"""
        self.assertEqual(text, self.wrap(text))

    def test_word_wrap_spaces(self):
        self.limit = 2
        text = ' ' * 6
        self.assertEqual(' ' * 6, self.wrap(text))

    def test_word_wrap_special_tag(self):
        self.limit = 2
        text = """
This test is so meta, even this sentence

With-special-tag: Avoids word-wrap
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

With-special-tag: Avoids word-wrap
"""

        self.assertEqual(self.wrap(text), expect)

    def test_word_wrap_space_at_start_of_wrap(self):
        inputs = """0 1 2 3 4 5 6 7 8 9  0 1 2 3 4 5 6 7 8 """
        expect = """0 1 2 3 4 5 6 7 8 9\n0 1 2 3 4 5 6 7 8"""
        self.limit = 20
        actual = self.wrap(inputs)
        self.assertEqual(expect, actual)


if __name__ == '__main__':
    unittest.main()
