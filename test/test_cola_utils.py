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

    def test_word_wrap(self):
        tabwidth = 8
        limit = 16
        text = """
12345678901 3 56 8 01 3 5 7

1 3 5"""
        expect = """
12345678901 3 56
8 01 3 5 7

1 3 5"""
        wrapped = utils.word_wrap(text, tabwidth, limit)
        self.assertEqual(expect, wrapped)


if __name__ == '__main__':
    unittest.main()
