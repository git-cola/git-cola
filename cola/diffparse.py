from __future__ import absolute_import, division, print_function, unicode_literals
import math
import re
from collections import Counter, defaultdict
from itertools import groupby

from . import compat


DIFF_CONTEXT = ' '
DIFF_ADDITION = '+'
DIFF_DELETION = '-'
DIFF_NO_NEWLINE = '\\'


def parse_range_str(range_str):
    if ',' in range_str:
        begin, end = range_str.split(',', 1)
        return int(begin), int(end)
    return int(range_str), 1


def _format_range(start, count):
    if count == 1:
        return str(start)
    return '%d,%d' % (start, count)


def _format_hunk_header(old_start, old_count, new_start, new_count, heading=''):
    return '@@ -%s +%s @@%s\n' % (
        _format_range(old_start, old_count),
        _format_range(new_start, new_count),
        heading,
    )


def digits(number):
    """Return the number of digits needed to display a number"""
    if number >= 0:
        result = int(math.log10(number)) + 1
    else:
        result = 1
    return result


class LineCounter(object):
    """Keep track of a diff range's values"""

    def __init__(self, value=0, max_value=-1):
        self.value = value
        self.max_value = max_value
        self._initial_max_value = max_value

    def reset(self):
        """Reset the max counter and return self for convenience"""
        self.max_value = self._initial_max_value
        return self

    def parse(self, range_str):
        """Parse a diff range and setup internal state"""
        start, count = parse_range_str(range_str)
        self.value = start
        self.max_value = max(start + count - 1, self.max_value)

    def tick(self, amount=1):
        """Return the current value and increment to the next"""
        value = self.value
        self.value += amount
        return value


class DiffLines(object):
    """Parse diffs and gather line numbers"""

    EMPTY = -1
    DASH = -2

    def __init__(self):
        self.merge = False

        # diff <old> <new>
        # merge <ours> <theirs> <new>
        self.old = LineCounter()
        self.new = LineCounter()
        self.ours = LineCounter()
        self.theirs = LineCounter()

    def digits(self):
        return digits(
            max(
                self.old.max_value,
                self.new.max_value,
                self.ours.max_value,
                self.theirs.max_value,
            )
        )

    def parse(self, diff_text):
        lines = []
        DIFF_STATE = 1
        state = INITIAL_STATE = 0
        merge = self.merge = False
        NO_NEWLINE = r'\ No newline at end of file'

        old = self.old.reset()
        new = self.new.reset()
        ours = self.ours.reset()
        theirs = self.theirs.reset()

        for text in diff_text.split('\n'):
            if text.startswith('@@ -'):
                parts = text.split(' ', 4)
                if parts[0] == '@@' and parts[3] == '@@':
                    state = DIFF_STATE
                    old.parse(parts[1][1:])
                    new.parse(parts[2][1:])
                    lines.append((self.DASH, self.DASH))
                    continue
            if text.startswith('@@@ -'):
                self.merge = merge = True
                parts = text.split(' ', 5)
                if parts[0] == '@@@' and parts[4] == '@@@':
                    state = DIFF_STATE
                    ours.parse(parts[1][1:])
                    theirs.parse(parts[2][1:])
                    new.parse(parts[3][1:])
                    lines.append((self.DASH, self.DASH, self.DASH))
                    continue
            if state == INITIAL_STATE or text.rstrip() == NO_NEWLINE:
                if merge:
                    lines.append((self.EMPTY, self.EMPTY, self.EMPTY))
                else:
                    lines.append((self.EMPTY, self.EMPTY))
            elif not merge and text.startswith('-'):
                lines.append((old.tick(), self.EMPTY))
            elif merge and text.startswith('- '):
                lines.append((ours.tick(), self.EMPTY, self.EMPTY))
            elif merge and text.startswith(' -'):
                lines.append((self.EMPTY, theirs.tick(), self.EMPTY))
            elif merge and text.startswith('--'):
                lines.append((ours.tick(), theirs.tick(), self.EMPTY))
            elif not merge and text.startswith('+'):
                lines.append((self.EMPTY, new.tick()))
            elif merge and text.startswith('++'):
                lines.append((self.EMPTY, self.EMPTY, new.tick()))
            elif merge and text.startswith('+ '):
                lines.append((self.EMPTY, theirs.tick(), new.tick()))
            elif merge and text.startswith(' +'):
                lines.append((ours.tick(), self.EMPTY, new.tick()))
            elif not merge and text.startswith(' '):
                lines.append((old.tick(), new.tick()))
            elif merge and text.startswith('  '):
                lines.append((ours.tick(), theirs.tick(), new.tick()))
            elif not text:
                new.tick()
                old.tick()
                ours.tick()
                theirs.tick()
            else:
                state = INITIAL_STATE
                if merge:
                    lines.append((self.EMPTY, self.EMPTY, self.EMPTY))
                else:
                    lines.append((self.EMPTY, self.EMPTY))

        return lines


class FormatDigits(object):
    """Format numbers for use in diff line numbers"""

    DASH = DiffLines.DASH
    EMPTY = DiffLines.EMPTY

    def __init__(self, dash='', empty=''):
        self.fmt = ''
        self.empty = ''
        self.dash = ''
        self._dash = dash or compat.uchr(0xB7)
        self._empty = empty or ' '

    def set_digits(self, value):
        self.fmt = '%%0%dd' % value
        self.empty = self._empty * value
        self.dash = self._dash * value

    def value(self, old, new):
        old_str = self._format(old)
        new_str = self._format(new)
        return '%s %s' % (old_str, new_str)

    def merge_value(self, old, base, new):
        old_str = self._format(old)
        base_str = self._format(base)
        new_str = self._format(new)
        return '%s %s %s' % (old_str, base_str, new_str)

    def number(self, value):
        return self.fmt % value

    def _format(self, value):
        if value == self.DASH:
            result = self.dash
        elif value == self.EMPTY:
            result = self.empty
        else:
            result = self.number(value)
        return result


class _HunkGrouper:
    _HUNK_HEADER_RE = re.compile(r'^@@ -([0-9,]+) \+([0-9,]+) @@(.*)')

    def __init__(self):
        self.match = None

    def __call__(self, line):
        match = self._HUNK_HEADER_RE.match(line)
        if match is not None:
            self.match = match
        return self.match


class _DiffHunk:
    def __init__(self, old_start, start_offset, heading, content_lines):
        type_counts = Counter(line[:1] for line in content_lines)
        self.old_count = type_counts[DIFF_CONTEXT] + type_counts[DIFF_DELETION]
        self.new_count = type_counts[DIFF_CONTEXT] + type_counts[DIFF_ADDITION]

        if self.old_count == 0:
            self.old_start = 0
        else:
            self.old_start = old_start

        if self.new_count == 0:
            self.new_start = 0
        elif self.old_start == 0:
            self.new_start = 1
        else:
            self.new_start = self.old_start + start_offset

        self.heading = heading

        self.lines = [
            _format_hunk_header(
                self.old_start,
                self.old_count,
                self.new_start,
                self.new_count,
                heading,
            ),
            *content_lines,
        ]
        self.content_lines = content_lines

    def line_delta(self):
        return self.new_count - self.old_count


class Patch:
    """Parse and rewrite diffs to produce edited patches

    This parser is used for modifying the worktree and index by constructing
    temporary patches that are applied using "git apply".

    """

    def __init__(self, filename, hunks, header_line_count=0):
        self.filename = filename
        self.hunks = hunks
        self.header_line_count = header_line_count

    @classmethod
    def parse(cls, filename, diff_text):
        header_line_count = 0
        hunks = []
        start_offset = 0
        for match, hunk_lines in groupby(diff_text.split('\n'), _HunkGrouper()):
            if match is not None:
                # Skip the hunk range header line as it will be regenerated by the
                # _DiffHunk.
                next(hunk_lines)
                hunk = _DiffHunk(
                    old_start=parse_range_str(match.group(1))[0],
                    start_offset=start_offset,
                    heading=match.group(3),
                    content_lines=[line + '\n' for line in hunk_lines if line],
                )
                hunks.append(hunk)
                start_offset += hunk.line_delta()
            else:
                header_line_count = len(list(hunk_lines))
        return cls(filename, hunks, header_line_count)

    def has_changes(self):
        return bool(self.hunks)

    def as_text(self, *, file_headers=True):
        lines = []
        if self.hunks:
            if file_headers:
                lines.append('--- a/%s\n' % self.filename)
                lines.append('+++ b/%s\n' % self.filename)
            for hunk in self.hunks:
                lines.extend(hunk.lines)
        return ''.join(lines)

    def _hunk_iter(self):
        hunk_last_line_idx = self.header_line_count - 1
        for hunk in self.hunks:
            hunk_first_line_idx = hunk_last_line_idx + 1
            hunk_last_line_idx += len(hunk.lines)
            yield hunk_first_line_idx, hunk_last_line_idx, hunk

    def generate_patch(self, first_line_idx, last_line_idx, reverse=False):
        """Return a patch containing a subset of the diff"""

        lines = ['--- a/%s\n' % self.filename, '+++ b/%s\n' % self.filename]

        start_offset = 0

        for hunk_first_line_idx, hunk_last_line_idx, hunk in self._hunk_iter():
            # skip hunks until we get to the one that contains the first
            # selected line
            if hunk_last_line_idx < first_line_idx:
                continue
            # once we have processed the hunk that contains the last selected
            # line, we can stop
            if hunk_first_line_idx > last_line_idx:
                break

            prev_skipped = False
            counts = defaultdict(int)
            filtered_lines = []

            for line_idx, line in enumerate(
                hunk.lines[1:], start=hunk_first_line_idx + 1
            ):
                line_type, line_content = line[:1], line[1:]

                if reverse:
                    if line_type == DIFF_ADDITION:
                        line_type = DIFF_DELETION
                    elif line_type == DIFF_DELETION:
                        line_type = DIFF_ADDITION

                if not first_line_idx <= line_idx <= last_line_idx:
                    if line_type == DIFF_ADDITION:
                        # Skip additions that are not selected.
                        prev_skipped = True
                        continue
                    if line_type == DIFF_DELETION:
                        # Change deletions that are not selected to context.
                        line_type = DIFF_CONTEXT
                if line_type == DIFF_NO_NEWLINE and prev_skipped:
                    # If the line immediately before a "No newline" line was
                    # skipped (because it was an unselected addition) skip
                    # the "No newline" line as well.
                    continue
                filtered_lines.append(line_type + line_content)
                counts[line_type] += 1
                prev_skipped = False

            # Do not include hunks that, after filtering, have only context
            # lines (no additions or deletions).
            if not counts[DIFF_ADDITION] and not counts[DIFF_DELETION]:
                continue

            old_count = counts[DIFF_CONTEXT] + counts[DIFF_DELETION]
            new_count = counts[DIFF_CONTEXT] + counts[DIFF_ADDITION]

            if reverse:
                old_start = hunk.new_start
            else:
                old_start = hunk.old_start
            new_start = old_start + start_offset
            if old_count == 0:
                new_start += 1
            if new_count == 0:
                new_start -= 1

            start_offset += counts[DIFF_ADDITION] - counts[DIFF_DELETION]

            lines.append(
                _format_hunk_header(
                    old_start, old_count, new_start, new_count, hunk.heading
                )
            )
            lines.extend(filtered_lines)

        # If there are only two lines, that means we did not include any hunks,
        # so return None.
        if len(lines) == 2:
            return None
        return ''.join(lines)

    def generate_hunk_patch(self, line_idx, reverse=False):
        """Return a patch containing the hunk for the specified line only"""
        hunk = None
        for hunk_first_line_idx, hunk_last_line_idx, hunk in self._hunk_iter():
            if line_idx <= hunk_last_line_idx:
                break
        if hunk is None:
            return None
        return self.generate_patch(
            hunk_first_line_idx, hunk_last_line_idx, reverse=reverse
        )
