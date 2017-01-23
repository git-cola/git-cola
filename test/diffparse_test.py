from __future__ import absolute_import, division, unicode_literals

import unittest

from cola import core
from cola import diffparse

from test import helper


class ParseDiffTestCase(unittest.TestCase):

    def test_diff(self):
        fixture_path = helper.fixture('diff.txt')
        parser = diffparse.DiffParser('cola/diffparse.py',
                                      core.read(fixture_path))
        hunks = parser.hunks

        self.assertEqual(len(hunks), 3)
        self.assertEqual(hunks[0].first_line_idx, 0)
        self.assertEqual(len(hunks[0].lines), 23)
        self.assertEqual(
                hunks[0].lines[0],
                '@@ -6,10 +6,21 @@ from cola import gitcmds')
        self.assertEqual(
                hunks[0].lines[1],
                ' from cola import gitcfg')
        self.assertEqual(hunks[0].lines[2], ' ')
        self.assertEqual(hunks[0].lines[3], ' ')
        self.assertEqual(hunks[0].lines[4], '+class DiffSource(object):')
        self.assertEqual(
                hunks[0].lines[-1],
                "         self._header_start_re = re.compile('^@@ -(\d+)"
                " \+(\d+),(\d+) @@.*')")

        self.assertEqual(hunks[1].first_line_idx, 23)
        self.assertEqual(len(hunks[1].lines), 18)
        self.assertEqual(
                hunks[1].lines[0],
                '@@ -29,13 +40,11 @@ class DiffParser(object):')
        self.assertEqual(
                hunks[1].lines[1],
                '         self.diff_sel = []')
        self.assertEqual(
                hunks[1].lines[2],
                '         self.selected = []')
        self.assertEqual(
                hunks[1].lines[3],
                '         self.filename = filename')
        self.assertEqual(
                hunks[1].lines[4],
                '+        self.diff_source = diff_source or DiffSource()')
        self.assertEqual(
                hunks[1].lines[-1],
                '         self.header = header')

        self.assertEqual(hunks[2].first_line_idx, 41)
        self.assertEqual(len(hunks[2].lines), 16)
        self.assertEqual(
                hunks[2].lines[0],
                '@@ -43,11 +52,10 @@ class DiffParser(object):')
        self.assertEqual(
                hunks[2].lines[-1],
                '         """Writes a new diff corresponding to the user\'s'
                ' selection."""')

    def test_diff_at_start(self):
        fixture_path = helper.fixture('diff-start.txt')
        parser = diffparse.DiffParser('foo bar/a', core.read(fixture_path))
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
        parser = diffparse.DiffParser('rijndael.js', core.read(fixture_path))
        hunks = parser.hunks

        self.assertEqual(hunks[0].lines[0], '@@ -1,39 +1 @@')
        self.assertEqual(
                hunks[-1].lines[-1],
                "+module.exports = require('./build/Release/rijndael');")
        self.assertEqual(hunks[0].old_start, 1)
        self.assertEqual(hunks[0].old_count, 39)
        self.assertEqual(hunks[0].new_start, 1)
        self.assertEqual(hunks[0].new_count, 1)

    def test_diff_that_empties_file(self):
        fixture_path = helper.fixture('diff-empty.txt')
        parser = diffparse.DiffParser('filename', core.read(fixture_path))
        hunks = parser.hunks

        self.assertEqual(hunks[0].lines[0], '@@ -1,2 +0,0 @@')
        self.assertEqual(hunks[-1].lines[-1], '-second')
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


class DiffLinesTestCase(unittest.TestCase):

    def setUp(self):
        self.parser = diffparse.DiffLines()
        fixture_path = helper.fixture('diff.txt')
        self.text = core.read(fixture_path)

    def test_basic_diff_line_count(self):
        """Verify the basic line counts"""
        lines = self.parser.parse(self.text)
        expect = len(self.text.splitlines())
        actual = len(lines)
        self.assertEqual(expect, actual)

    def test_diff_line_count_ranges(self):
        parser = self.parser
        lines = parser.parse(self.text)

        # Diff header
        line = 0
        count = 1
        self.assertEqual(lines[line][0], parser.DASH)
        self.assertEqual(lines[line][1], parser.DASH)
        line += count

        # 3 lines of context
        count = 3
        current_old = 6
        current_new = 6
        for i in range(count):
            self.assertEqual(lines[line+i][0], current_old+i)
            self.assertEqual(lines[line+i][1], current_new+i)
        line += count
        current_old += count
        current_new += count

        # 10 lines of new text
        count = 10
        for i in range(count):
            self.assertEqual(lines[line+i][0], parser.EMPTY)
            self.assertEqual(lines[line+i][1], current_new+i)

        line += count
        current_new += count

        # 3 more lines of context
        count = 3
        for i in range(count):
            self.assertEqual(lines[line+i][0], current_old+i)
            self.assertEqual(lines[line+i][1], current_new+i)
        line += count
        current_new += count
        current_old += count

        # 1 line of removal
        count = 1
        for i in range(count):
            self.assertEqual(lines[line+i][0], current_old+i)
            self.assertEqual(lines[line+i][1], parser.EMPTY)
        line += count
        current_old += count

        # 2 lines of addition
        count = 2
        for i in range(count):
            self.assertEqual(lines[line+i][0], parser.EMPTY)
            self.assertEqual(lines[line+i][1], current_new+i)
        line += count
        current_new += count

        # 3 more lines of context
        count = 3
        for i in range(count):
            self.assertEqual(lines[line+i][0], current_old+i)
            self.assertEqual(lines[line+i][1], current_new+i)
        line += count
        current_new += count
        current_old += count

        # 1 line of header
        count = 1
        for i in range(count):
            self.assertEqual(lines[line+i][0], parser.DASH)
            self.assertEqual(lines[line+i][1], parser.DASH)
        line += count

        # 3 more lines of context
        current_old = 29
        current_new = 40
        count = 3
        for i in range(count):
            self.assertEqual(lines[line+i][0], current_old+i)
            self.assertEqual(lines[line+i][1], current_new+i)
        line += count
        current_new += count
        current_old += count

        expect_max_old = 54
        self.assertEqual(expect_max_old, parser.max_old)

        expect_max_new = 62
        self.assertEqual(expect_max_new, parser.max_new)

        self.assertEqual(parser.digits(), 2)


class FormatDiffLinesTestCase(unittest.TestCase):

    def test_format_basic(self):
        fmt = diffparse.FormatDigits()
        fmt.set_digits(2)

        expect = '01 99'
        actual = fmt.value(1, 99)
        self.assertEqual(expect, actual)

    def test_format_reuse(self):
        fmt = diffparse.FormatDigits()

        fmt.set_digits(3)
        expect = '001 099'
        actual = fmt.value(1, 99)
        self.assertEqual(expect, actual)

        fmt.set_digits(4)
        expect = '0001 0099'
        actual = fmt.value(1, 99)
        self.assertEqual(expect, actual)

    def test_format_special_values(self):
        fmt = diffparse.FormatDigits(dash='-')
        fmt.set_digits(3)

        expect = '    099'
        actual = fmt.value(fmt.EMPTY, 99)
        self.assertEqual(expect, actual)

        expect = '001    '
        actual = fmt.value(1, fmt.EMPTY)
        self.assertEqual(expect, actual)

        expect = '       '
        actual = fmt.value(fmt.EMPTY, fmt.EMPTY)
        self.assertEqual(expect, actual)

        expect = '--- 001'
        actual = fmt.value(fmt.DASH, 1)
        self.assertEqual(expect, actual)

        expect = '099 ---'
        actual = fmt.value(99, fmt.DASH)
        self.assertEqual(expect, actual)

        expect = '--- ---'
        actual = fmt.value(fmt.DASH, fmt.DASH)
        self.assertEqual(expect, actual)

        expect = '    ---'
        actual = fmt.value(fmt.EMPTY, fmt.DASH)
        self.assertEqual(expect, actual)

        expect = '---    '
        actual = fmt.value(fmt.DASH, fmt.EMPTY)
        self.assertEqual(expect, actual)


class ParseRangeStrTestCase(unittest.TestCase):

    def test_parse_range_str(self):
        start, count = diffparse._parse_range_str('1,2')
        self.assertEqual(start, 1)
        self.assertEqual(count, 2)

    def test_parse_range_str_single_line(self):
        start, count = diffparse._parse_range_str('2')
        self.assertEqual(start, 2)
        self.assertEqual(count, 1)

    def test_parse_range_str_empty(self):
        start, count = diffparse._parse_range_str('0,0')
        self.assertEqual(start, 0)
        self.assertEqual(count, 0)


if __name__ == '__main__':
    unittest.main()
