from __future__ import absolute_import, division, print_function, unicode_literals
import math
import re
from collections import defaultdict

from . import compat


_HUNK_HEADER_RE = re.compile(r'^@@ -([0-9,]+) \+([0-9,]+) @@(.*)')


class _DiffHunk(object):
    def __init__(
        self, old_start, old_count, new_start, new_count, heading, first_line_idx, lines
    ):
        self.old_start = old_start
        self.old_count = old_count
        self.new_start = new_start
        self.new_count = new_count
        self.heading = heading
        self.first_line_idx = first_line_idx
        self.lines = lines

    @property
    def last_line_idx(self):
        return self.first_line_idx + len(self.lines) - 1


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


def _parse_diff(diff_text):
    hunks = []
    for line_idx, line in enumerate(diff_text.split('\n')):
        match = _HUNK_HEADER_RE.match(line)
        if match:
            old_start, old_count = parse_range_str(match.group(1))
            new_start, new_count = parse_range_str(match.group(2))
            heading = match.group(3)
            hunks.append(
                _DiffHunk(
                    old_start,
                    old_count,
                    new_start,
                    new_count,
                    heading,
                    line_idx,
                    lines=[line + '\n'],
                )
            )
        elif line and hunks:
            hunks[-1].lines.append(line + '\n')
    return hunks


def digits(number):
    """Return the number of digits needed to display a number"""
    if number >= 0:
        result = int(math.log10(number)) + 1
    else:
        result = 1
    return result


class Counter(object):
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
        self.max_value = max(start + count, self.max_value)

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
        self.valid = True
        self.merge = False

        # diff <old> <new>
        # merge <ours> <theirs> <new>
        self.old = Counter()
        self.new = Counter()
        self.ours = Counter()
        self.theirs = Counter()

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
                lines.append((self.EMPTY, theirs.tick(), self.EMPTY))
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


class DiffParser(object):
    """Parse and rewrite diffs to produce edited patches

    This parser is used for modifying the worktree and index by constructing
    temporary patches that are applied using "git apply".

    """

    def __init__(self, filename, diff_text):
        self.filename = filename
        self.hunks = _parse_diff(diff_text)

    def generate_patch(self, first_line_idx, last_line_idx, reverse=False):
        """Return a patch containing a subset of the diff"""

        ADDITION = '+'
        DELETION = '-'
        CONTEXT = ' '
        NO_NEWLINE = '\\'

        lines = ['--- a/%s\n' % self.filename, '+++ b/%s\n' % self.filename]

        start_offset = 0

        for hunk in self.hunks:
            # skip hunks until we get to the one that contains the first
            # selected line
            if hunk.last_line_idx < first_line_idx:
                continue
            # once we have processed the hunk that contains the last selected
            # line, we can stop
            if hunk.first_line_idx > last_line_idx:
                break

            prev_skipped = False
            counts = defaultdict(int)
            filtered_lines = []

            for line_idx, line in enumerate(
                hunk.lines[1:], start=hunk.first_line_idx + 1
            ):
                line_type, line_content = line[:1], line[1:]

                if reverse:
                    if line_type == ADDITION:
                        line_type = DELETION
                    elif line_type == DELETION:
                        line_type = ADDITION

                if not first_line_idx <= line_idx <= last_line_idx:
                    if line_type == ADDITION:
                        # Skip additions that are not selected.
                        prev_skipped = True
                        continue
                    if line_type == DELETION:
                        # Change deletions that are not selected to context.
                        line_type = CONTEXT
                if line_type == NO_NEWLINE and prev_skipped:
                    # If the line immediately before a "No newline" line was
                    # skipped (because it was an unselected addition) skip
                    # the "No newline" line as well.
                    continue
                filtered_lines.append(line_type + line_content)
                counts[line_type] += 1
                prev_skipped = False

            # Do not include hunks that, after filtering, have only context
            # lines (no additions or deletions).
            if not counts[ADDITION] and not counts[DELETION]:
                continue

            old_count = counts[CONTEXT] + counts[DELETION]
            new_count = counts[CONTEXT] + counts[ADDITION]

            if reverse:
                old_start = hunk.new_start
            else:
                old_start = hunk.old_start
            new_start = old_start + start_offset
            if old_count == 0:
                new_start += 1
            if new_count == 0:
                new_start -= 1

            start_offset += counts[ADDITION] - counts[DELETION]

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
        for hunk in self.hunks:
            if line_idx <= hunk.last_line_idx:
                break
        if hunk is None:
            return None
        return self.generate_patch(
            hunk.first_line_idx, hunk.last_line_idx, reverse=reverse
        )
