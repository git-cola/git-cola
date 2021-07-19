"""Tests for the diffparse module"""
# pylint: disable=redefined-outer-name
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from cola import core
from cola import diffparse

from . import helper


class DiffLinesTestData(object):
    """Test data used by DiffLines tests"""

    def __init__(self):
        self.parser = diffparse.DiffLines()
        fixture_path = helper.fixture('diff.txt')
        self.text = core.read(fixture_path)


@pytest.fixture
def difflines_data():
    """Return test data for diffparse.DiffLines tests"""
    return DiffLinesTestData()


def test_diff():
    fixture_path = helper.fixture('diff.txt')
    parser = diffparse.DiffParser('cola/diffparse.py', core.read(fixture_path))
    hunks = parser.hunks

    assert len(hunks) == 3
    assert hunks[0].first_line_idx == 0
    assert len(hunks[0].lines) == 23
    assert hunks[0].lines[0] == '@@ -6,10 +6,21 @@ from cola import gitcmds\n'
    assert hunks[0].lines[1] == ' from cola import gitcfg\n'
    assert hunks[0].lines[2] == ' \n'
    assert hunks[0].lines[3] == ' \n'
    assert hunks[0].lines[4] == '+class DiffSource(object):\n'
    assert hunks[0].lines[-1] == (
        r"         self._header_start_re = re.compile('^@@ -(\d+)"
        r" \+(\d+),(\d+) @@.*')"
        '\n'
    )
    assert hunks[1].first_line_idx == 23
    assert len(hunks[1].lines) == 18
    assert hunks[1].lines[0] == '@@ -29,13 +40,11 @@ class DiffParser(object):\n'
    assert hunks[1].lines[1] == '         self.diff_sel = []\n'
    assert hunks[1].lines[2] == '         self.selected = []\n'
    assert hunks[1].lines[3] == '         self.filename = filename\n'
    assert hunks[1].lines[4] == (
        '+        self.diff_source = diff_source or DiffSource()\n'
    )
    assert hunks[1].lines[-1] == '         self.header = header\n'

    assert hunks[2].first_line_idx == 41
    assert len(hunks[2].lines) == 16
    assert hunks[2].lines[0] == '@@ -43,11 +52,10 @@ class DiffParser(object):\n'
    assert hunks[2].lines[-1] == (
        '         """Writes a new diff corresponding to the user\'s'
        ' selection."""\n'
    )


def test_diff_at_start():
    fixture_path = helper.fixture('diff-start.txt')
    parser = diffparse.DiffParser('foo bar/a', core.read(fixture_path))
    hunks = parser.hunks

    assert hunks[0].lines[0] == '@@ -1 +1,4 @@\n'
    assert hunks[-1].lines[-1] == '+c\n'
    assert hunks[0].old_start == 1
    assert hunks[0].old_count == 1
    assert hunks[0].new_start == 1
    assert hunks[0].new_count == 4
    assert parser.generate_patch(1, 3) == (
        '--- a/foo bar/a\n'
        '+++ b/foo bar/a\n'
        '@@ -1 +1,3 @@\n'
        ' bar\n'
        '+a\n'
        '+b\n'
    )
    assert parser.generate_patch(0, 4) == (
        '--- a/foo bar/a\n'
        '+++ b/foo bar/a\n'
        '@@ -1 +1,4 @@\n'
        ' bar\n'
        '+a\n'
        '+b\n'
        '+c\n'
    )


def test_diff_at_end():
    fixture_path = helper.fixture('diff-end.txt')
    parser = diffparse.DiffParser('rijndael.js', core.read(fixture_path))
    hunks = parser.hunks

    assert hunks[0].lines[0] == '@@ -1,39 +1 @@\n'
    assert hunks[-1].lines[-1] == (
        "+module.exports = require('./build/Release/rijndael');\n"
    )
    assert hunks[0].old_start == 1
    assert hunks[0].old_count == 39
    assert hunks[0].new_start == 1
    assert hunks[0].new_count == 1


def test_diff_that_empties_file():
    fixture_path = helper.fixture('diff-empty.txt')
    parser = diffparse.DiffParser('filename', core.read(fixture_path))
    hunks = parser.hunks

    assert hunks[0].lines[0] == '@@ -1,2 +0,0 @@\n'
    assert hunks[-1].lines[-1] == '-second\n'
    assert hunks[0].old_start == 1
    assert hunks[0].old_count == 2
    assert hunks[0].new_start == 0
    assert hunks[0].new_count == 0
    assert parser.generate_patch(1, 1) == (
        '--- a/filename\n'
        '+++ b/filename\n'
        '@@ -1,2 +1 @@\n'
        '-first\n'
        ' second\n'
    )
    assert parser.generate_patch(0, 2) == (
        '--- a/filename\n'
        '+++ b/filename\n'
        '@@ -1,2 +0,0 @@\n'
        '-first\n'
        '-second\n'
    )


def test_diff_file_removal():
    diff_text = """\
deleted file mode 100755
@@ -1,1 +0,0 @@
-#!/bin/sh
"""
    parser = diffparse.DiffParser('deleted.txt', diff_text)

    expect = 1
    actual = len(parser.hunks)
    assert expect == actual

    # Selecting the first two lines generate no diff
    expect = None
    actual = parser.generate_patch(0, 1)
    assert expect == actual

    # Selecting the last line should generate a line removal
    expect = """\
--- a/deleted.txt
+++ b/deleted.txt
@@ -1 +0,0 @@
-#!/bin/sh
"""
    actual = parser.generate_patch(1, 2)
    assert expect == actual

    # All three lines should map to the same hunk diff
    actual = parser.generate_hunk_patch(0)
    assert expect == actual

    actual = parser.generate_hunk_patch(1)
    assert expect == actual

    actual = parser.generate_hunk_patch(2)
    assert expect == actual


def test_basic_diff_line_count(difflines_data):
    """Verify the basic line counts"""
    lines = difflines_data.parser.parse(difflines_data.text)
    expect = len(difflines_data.text.splitlines())
    actual = len(lines)
    assert expect == actual


def test_diff_line_count_ranges(difflines_data):
    parser = difflines_data.parser
    lines = parser.parse(difflines_data.text)

    # Diff header
    line = 0
    count = 1
    assert lines[line][0] == parser.DASH
    assert lines[line][1] == parser.DASH
    line += count

    # 3 lines of context
    count = 3
    current_old = 6
    current_new = 6
    for i in range(count):
        assert lines[line + i][0] == current_old + i
        assert lines[line + i][1] == current_new + i
    line += count
    current_old += count
    current_new += count

    # 10 lines of new text
    count = 10
    for i in range(count):
        assert lines[line + i][0] == parser.EMPTY
        assert lines[line + i][1] == current_new + i

    line += count
    current_new += count

    # 3 more lines of context
    count = 3
    for i in range(count):
        assert lines[line + i][0] == current_old + i
        assert lines[line + i][1] == current_new + i
    line += count
    current_new += count
    current_old += count

    # 1 line of removal
    count = 1
    for i in range(count):
        assert lines[line + i][0] == current_old + i
        assert lines[line + i][1] == parser.EMPTY
    line += count
    current_old += count

    # 2 lines of addition
    count = 2
    for i in range(count):
        assert lines[line + i][0] == parser.EMPTY
        assert lines[line + i][1] == current_new + i
    line += count
    current_new += count

    # 3 more lines of context
    count = 3
    for i in range(count):
        assert lines[line + i][0] == current_old + i
        assert lines[line + i][1] == current_new + i
    line += count
    current_new += count
    current_old += count

    # 1 line of header
    count = 1
    for i in range(count):
        assert lines[line + i][0] == parser.DASH
        assert lines[line + i][1] == parser.DASH
    line += count

    # 3 more lines of context
    current_old = 29
    current_new = 40
    count = 3
    for i in range(count):
        assert lines[line + i][0] == current_old + i
        assert lines[line + i][1] == current_new + i
    line += count
    current_new += count
    current_old += count

    expect_max_old = 54
    assert expect_max_old == parser.old.max_value

    expect_max_new = 62
    assert expect_max_new == parser.new.max_value

    assert parser.digits() == 2


def test_diff_line_for_merge(difflines_data):
    """Verify the basic line counts"""
    text = """@@@ -1,23 -1,33 +1,75 @@@
++<<<<<<< upstream
 +
 +Ok
"""
    parser = difflines_data.parser
    lines = parser.parse(text)
    assert len(lines) == 4
    assert len(lines[0]) == 3
    assert len(lines[1]) == 3
    assert len(lines[2]) == 3
    assert len(lines[3]) == 3

    assert lines[0][0] == parser.DASH
    assert lines[0][1] == parser.DASH
    assert lines[0][2] == parser.DASH

    assert lines[1][0] == parser.EMPTY
    assert lines[1][1] == parser.EMPTY
    assert lines[1][2] == 1

    assert lines[2][0] == 1
    assert lines[2][1] == parser.EMPTY
    assert lines[2][2] == 2

    assert lines[3][0] == 2
    assert lines[3][1] == parser.EMPTY
    assert lines[3][2] == 3


def test_format_basic():
    fmt = diffparse.FormatDigits()
    fmt.set_digits(2)

    expect = '01 99'
    actual = fmt.value(1, 99)
    assert expect == actual


def test_format_reuse():
    fmt = diffparse.FormatDigits()

    fmt.set_digits(3)
    expect = '001 099'
    actual = fmt.value(1, 99)
    assert expect == actual

    fmt.set_digits(4)
    expect = '0001 0099'
    actual = fmt.value(1, 99)
    assert expect == actual


def test_format_special_values():
    fmt = diffparse.FormatDigits(dash='-')
    fmt.set_digits(3)

    expect = '    099'
    actual = fmt.value(fmt.EMPTY, 99)
    assert expect == actual

    expect = '001    '
    actual = fmt.value(1, fmt.EMPTY)
    assert expect == actual

    expect = '       '
    actual = fmt.value(fmt.EMPTY, fmt.EMPTY)
    assert expect == actual

    expect = '--- 001'
    actual = fmt.value(fmt.DASH, 1)
    assert expect == actual

    expect = '099 ---'
    actual = fmt.value(99, fmt.DASH)
    assert expect == actual

    expect = '--- ---'
    actual = fmt.value(fmt.DASH, fmt.DASH)
    assert expect == actual

    expect = '    ---'
    actual = fmt.value(fmt.EMPTY, fmt.DASH)
    assert expect == actual

    expect = '---    '
    actual = fmt.value(fmt.DASH, fmt.EMPTY)
    assert expect == actual


def test_parse_range_str():
    start, count = diffparse.parse_range_str('1,2')
    assert start == 1
    assert count == 2


def test_parse_range_str_single_line():
    start, count = diffparse.parse_range_str('2')
    assert start == 2
    assert count == 1


def test_parse_range_str_empty():
    start, count = diffparse.parse_range_str('0,0')
    assert start == 0
    assert count == 0
