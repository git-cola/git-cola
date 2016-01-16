from __future__ import absolute_import, division, unicode_literals

import unittest

from cola import core
from cola.diffparse import _parse_range_str, DiffParser

from test import helper


class ParseDiffTestCase(unittest.TestCase):
    def test_diff(self):
        fixture_path = helper.fixture('diff.txt')
        parser = DiffParser('cola/diffparse.py', core.read(fixture_path))
        hunks = parser.hunks

        self.assertEqual(len(hunks), 3)

        self.assertEqual(hunks[0].first_line_idx, 0)
        self.assertEqual(len(hunks[0].lines), 23)
        self.assertEqual(hunks[0].lines[0],
                '@@ -6,10 +6,21 @@ from cola import gitcmds')
        self.assertEqual(hunks[0].lines[1],
                ' from cola import gitcfg')
        self.assertEqual(hunks[0].lines[2],
                ' ')
        self.assertEqual(hunks[0].lines[3],
                ' ')
        self.assertEqual(hunks[0].lines[4],
                '+class DiffSource(object):')
        self.assertEqual(hunks[0].lines[-1],
                "         self._header_start_re = re.compile('^@@ -(\d+)"
                " \+(\d+),(\d+) @@.*')")

        self.assertEqual(hunks[1].first_line_idx, 23)
        self.assertEqual(len(hunks[1].lines), 18)
        self.assertEqual(hunks[1].lines[0],
                '@@ -29,13 +40,11 @@ class DiffParser(object):')
        self.assertEqual(hunks[1].lines[1],
                '         self.diff_sel = []')
        self.assertEqual(hunks[1].lines[2],
                '         self.selected = []')
        self.assertEqual(hunks[1].lines[3],
                '         self.filename = filename')
        self.assertEqual(hunks[1].lines[4],
                '+        self.diff_source = diff_source or DiffSource()')
        self.assertEqual(hunks[1].lines[-1],
                '         self.header = header')

        self.assertEqual(hunks[2].first_line_idx, 41)
        self.assertEqual(len(hunks[2].lines), 16)
        self.assertEqual(hunks[2].lines[0],
                '@@ -43,11 +52,10 @@ class DiffParser(object):')
        self.assertEqual(hunks[2].lines[-1],
                '         """Writes a new diff corresponding to the user\'s'
                ' selection."""')

    def test_diff_at_start(self):
        fixture_path = helper.fixture('diff-start.txt')
        parser = DiffParser('foo bar/a', core.read(fixture_path))
        hunks = parser.hunks

        self.assertEqual(hunks[0].lines[0], '@@ -1 +1,4 @@')
        self.assertEqual(hunks[-1].lines[-1], '+c')
        self.assertEqual(hunks[0].old_start, 1)
        self.assertEqual(hunks[0].old_count, 1)
        self.assertEqual(hunks[0].new_start, 1)
        self.assertEqual(hunks[0].new_count, 4)
        self.assertEqual(parser.generate_patch(1, 3),
                         '--- a/foo bar/a\n'
                         '+++ b/foo bar/a\n'
                         '@@ -1 +1,3 @@\n'
                         ' bar\n'
                         '+a\n'
                         '+b\n')
        self.assertEqual(parser.generate_patch(0, 4),
                         '--- a/foo bar/a\n'
                         '+++ b/foo bar/a\n'
                         '@@ -1 +1,4 @@\n'
                         ' bar\n'
                         '+a\n'
                         '+b\n'
                         '+c\n')

    def test_diff_at_end(self):
        fixture_path = helper.fixture('diff-end.txt')
        parser = DiffParser('rijndael.js', core.read(fixture_path))
        hunks = parser.hunks

        self.assertEqual(hunks[0].lines[0],
                '@@ -1,39 +1 @@')
        self.assertEqual(hunks[-1].lines[-1],
                "+module.exports = require('./build/Release/rijndael');")
        self.assertEqual(hunks[0].old_start, 1)
        self.assertEqual(hunks[0].old_count, 39)
        self.assertEqual(hunks[0].new_start, 1)
        self.assertEqual(hunks[0].new_count, 1)

    def test_diff_that_empties_file(self):
        fixture_path = helper.fixture('diff-empty.txt')
        parser = DiffParser('filename', core.read(fixture_path))
        hunks = parser.hunks

        self.assertEqual(hunks[0].lines[0],
                '@@ -1,2 +0,0 @@')
        self.assertEqual(hunks[-1].lines[-1],
                '-second')
        self.assertEqual(hunks[0].old_start, 1)
        self.assertEqual(hunks[0].old_count, 2)
        self.assertEqual(hunks[0].new_start, 0)
        self.assertEqual(hunks[0].new_count, 0)
        self.assertEqual(parser.generate_patch(1, 1),
                         '--- a/filename\n'
                         '+++ b/filename\n'
                         '@@ -1,2 +1 @@\n'
                         '-first\n'
                         ' second\n')
        self.assertEqual(parser.generate_patch(0, 2),
                         '--- a/filename\n'
                         '+++ b/filename\n'
                         '@@ -1,2 +0,0 @@\n'
                         '-first\n'
                         '-second\n')


class ParseRangeStrTestCase(unittest.TestCase):
    def test_parse_range_str(self):
        start, count = _parse_range_str('1,2')
        self.assertEqual(start, 1)
        self.assertEqual(count, 2)

    def test_parse_range_str_single_line(self):
        start, count = _parse_range_str('2')
        self.assertEqual(start, 2)
        self.assertEqual(count, 1)

    def test_parse_range_str_empty(self):
        start, count = _parse_range_str('0,0')
        self.assertEqual(start, 0)
        self.assertEqual(count, 0)


if __name__ == '__main__':
    unittest.main()
