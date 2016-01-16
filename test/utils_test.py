#!/usr/bin/env python

from __future__ import absolute_import, division, unicode_literals

import shutil
import os
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
        paths = set(['foo///bar///baz'])
        path_set = utils.add_parents(paths)

        self.assertTrue('foo/bar/baz' in path_set)
        self.assertTrue('foo/bar' in path_set)
        self.assertTrue('foo' in path_set)
        self.assertFalse('foo///bar///baz' in path_set)

        # Ensure that the original set is unchanged
        expect = set(['foo///bar///baz'])
        self.assertEqual(expect, paths)


    def test_tmpdir_gives_consistent_results(self):
        utils.tmpdir.func.cache.clear()

        first = utils.tmpdir()
        second = utils.tmpdir()
        third = utils.tmpdir()

        self.assertEqual(first, second)
        self.assertEqual(first, third)

        shutil.rmtree(first)

    def test_tmp_filename_gives_good_file(self):
        utils.tmpdir.func.cache.clear()

        tmpdir = utils.tmpdir()
        first = utils.tmp_filename('test')
        second = utils.tmp_filename('test')

        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith(os.path.join(tmpdir, 'test')))
        self.assertTrue(second.startswith(os.path.join(tmpdir, 'test')))

        shutil.rmtree(tmpdir)


if __name__ == '__main__':
    unittest.main()
