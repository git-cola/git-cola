from __future__ import division, absolute_import, unicode_literals

import re

from collections import defaultdict


_HUNK_HEADER_RE = re.compile(r'^@@ -([0-9,]+) \+([0-9,]+) @@(.*)')


class _DiffHunk(object):
    def __init__(self, old_start, old_count, new_start, new_count, heading,
                 first_line_idx, lines):
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


def _parse_range_str(range_str):
    if ',' in range_str:
        begin, end = range_str.split(',', 1)
        return int(begin), int(end)
    else:
        return int(range_str), 1


def _format_range(start, count):
    if count == 1:
        return str(start)
    else:
        return '%d,%d' % (start, count)


def _format_hunk_header(old_start, old_count,
                       new_start, new_count,
                       heading=''):
    return '@@ -%s +%s @@%s' % (_format_range(old_start, old_count),
                                _format_range(new_start, new_count),
                                heading)


def _parse_diff(diff_text):
    hunks = []
    for line_idx, line in enumerate(diff_text.split('\n')):
        match = _HUNK_HEADER_RE.match(line)
        if match:
            old_start, old_count = _parse_range_str(match.group(1))
            new_start, new_count = _parse_range_str(match.group(2))
            heading = match.group(3)
            hunks.append(_DiffHunk(old_start, old_count,
                                   new_start, new_count,
                                   heading, line_idx, lines=[line]))
        elif not hunks:
            # first line of the diff is not a header line
            errmsg = 'Malformed diff?: %s' % diff_text
            raise AssertionError(errmsg)
        elif line:
            hunks[-1].lines.append(line)
    return hunks


class DiffParser(object):

    def __init__(self, filename, diff_text):
        self.filename = filename
        self.hunks = _parse_diff(diff_text)

    def generate_patch(self, first_line_idx, last_line_idx,
                       reverse=False):
        """Return a patch containing a subset of the diff"""

        ADDITION = '+'
        DELETION = '-'
        CONTEXT = ' '
        NO_NEWLINE = '\\'

        lines = ['--- a/%s' % self.filename, '+++ b/%s' % self.filename]

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

            for line_idx, line in enumerate(hunk.lines[1:],
                                            start=hunk.first_line_idx + 1):
                line_type, line_content = line[:1], line[1:]

                if reverse:
                    if line_type == ADDITION:
                        line_type = DELETION
                    elif line_type == DELETION:
                        line_type = ADDITION

                if not (first_line_idx <= line_idx <= last_line_idx):
                    if line_type == ADDITION:
                        # Skip additions that are not selected.
                        prev_skipped = True
                        continue
                    elif line_type == DELETION:
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

            lines.append(_format_hunk_header(old_start, old_count,
                                             new_start, new_count,
                                             hunk.heading))
            lines.extend(filtered_lines)

        # If there are only two lines, that means we did not include any hunks,
        # so return None.
        if len(lines) == 2:
            return None
        else:
            lines.append('')
            return '\n'.join(lines)

    def generate_hunk_patch(self, line_idx, reverse=False):
        """Return a patch containing only the hunk corresponding to the
        specified line."""
        if not self.hunks:
            return None
        for hunk in self.hunks:
            if line_idx <= hunk.last_line_idx:
                break
        return self.generate_patch(hunk.first_line_idx, hunk.last_line_idx,
                                   reverse=reverse)
