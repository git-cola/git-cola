#!/usr/bin/env python

from __future__ import absolute_import, division, unicode_literals

import os
import unittest

from cola import core
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
        paths = set(['foo///bar///baz'])
        path_set = utils.add_parents(paths)

        self.assertTrue('foo/bar/baz' in path_set)
        self.assertTrue('foo/bar' in path_set)
        self.assertTrue('foo' in path_set)
        self.assertFalse('foo///bar///baz' in path_set)

        # Ensure that the original set is unchanged
        expect = set(['foo///bar///baz'])
        self.assertEqual(expect, paths)

    def test_tmp_filename_gives_good_file(self):
        first = utils.tmp_filename('test')
        second = utils.tmp_filename('test')

        self.assertFalse(core.exists(first))
        self.assertFalse(core.exists(second))

        self.assertNotEqual(first, second)
        self.assertTrue(os.path.basename(first).startswith('git-cola-test'))
        self.assertTrue(os.path.basename(second).startswith('git-cola-test'))

    def test_strip_one_abspath(self):
        expect = 'bin/git'
        actual = utils.strip_one('/usr/bin/git')
        self.assertEqual(expect, actual)

    def test_strip_one_relpath(self):
        expect = 'git'
        actual = utils.strip_one('bin/git')
        self.assertEqual(expect, actual)

    def test_strip_one_nested_relpath(self):
        expect = 'bin/git'
        actual = utils.strip_one('local/bin/git')
        self.assertEqual(expect, actual)

    def test_strip_one_basename(self):
        expect = 'git'
        actual = utils.strip_one('git')
        self.assertEqual(expect, actual)


if __name__ == '__main__':
    unittest.main()
