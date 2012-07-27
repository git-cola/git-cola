#!/usr/bin/env python

import unittest

from cola import utils

class ColaUtilsTestCase(unittest.TestCase):
    """Tests the cola.utils module."""

    def test_basename(self):
        """Test the utils.basename function."""
        self.assertEqual(utils.basename('bar'), 'bar')
        self.assertEqual(utils.basename('/bar'), 'bar')
        self.assertEqual(utils.basename('/bar '), 'bar ')
        self.assertEqual(utils.basename('foo/bar'), 'bar')
        self.assertEqual(utils.basename('/foo/bar'), 'bar')
        self.assertEqual(utils.basename('foo/foo/bar'), 'bar')
        self.assertEqual(utils.basename('/foo/foo/bar'), 'bar')
        self.assertEqual(utils.basename('/foo/foo//bar'), 'bar')
        self.assertEqual(utils.basename('////foo //foo//bar'), 'bar')

    def test_dirname(self):
        """Test the utils.dirname function."""
        self.assertEqual(utils.dirname('bar'), '')
        self.assertEqual(utils.dirname('/bar'), '')
        self.assertEqual(utils.dirname('//bar'), '')
        self.assertEqual(utils.dirname('///bar'), '')
        self.assertEqual(utils.dirname('foo/bar'), 'foo')
        self.assertEqual(utils.dirname('foo//bar'), 'foo')
        self.assertEqual(utils.dirname('foo /bar'), 'foo ')
        self.assertEqual(utils.dirname('/foo//bar'), '/foo')
        self.assertEqual(utils.dirname('/foo /bar'), '/foo ')
        self.assertEqual(utils.dirname('//foo//bar'), '/foo')
        self.assertEqual(utils.dirname('///foo///bar'), '/foo')

    def test_add_parents(self):
        """Test the utils.add_parents() function."""
        path_set = set(['foo///bar///baz'])
        utils.add_parents(path_set)

        self.assertTrue('foo/bar/baz' in path_set)
        self.assertTrue('foo/bar' in path_set)
        self.assertTrue('foo' in path_set)


class WordWrapTestCase(unittest.TestCase):
    def setUp(self):
        self.tabwidth = 8
        self.limit = None

    def wrap(self, text):
        return utils.word_wrap(text, self.tabwidth, self.limit)

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
        expect = '123-\n5'
        self.assertEqual(expect, self.wrap(text))

    def test_word_wrap_double_dashes(self):
        self.limit = 4
        text = '12--5'
        expect = '12-\n-5'
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
        self.assertEqual('  \n  \n', self.wrap(text))


if __name__ == '__main__':
    unittest.main()
