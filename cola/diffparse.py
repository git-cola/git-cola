import os
import re

from cola import utils
from cola import gitcmds
from cola import gitcfg


class Range(object):

    def __init__(self, begin, end):
        self.begin = self._parse(begin)
        self.end = self._parse(end)

    def _parse(self, range_str):
        if ',' in range_str:
            begin, end = range_str.split(',')
            return [int(begin), int(end)]
        else:
            return [int(range_str), int(range_str)]

    def make(self):
        return '@@ -%s +%s @@' % (self._span(self.begin), self._span(self.end))

    def set_begin_count(self, count):
        self._set_count(self.begin, count)

    def set_end_count(self, count):
        self._set_count(self.end, count)

    def _set_count(self, which, count):
        if count != which[1]:
            which[1] = count
            if count == 1 and which[0] == 0:
                # the file would be empty in the diff, but we're only
                # partially applying it, and thus it's not a +0,0 diff
                # anymore.
                which[0] = 1

    def _span(self, seq):
        a = seq[0]
        b = seq[1]
        if a == b and a == 1:
            return '%d' % a
        else:
            return '%d,%d' % (a, b)


class DiffSource(object):
    def get(self, head, amending, filename, cached, reverse):
        return gitcmds.diff_helper(head=head,
                                   amending=amending,
                                   filename=filename,
                                   with_diff_header=True,
                                   cached=cached,
                                   reverse=reverse)


class DiffParser(object):

    """Handles parsing diff for use by the interactive index editor."""

    HEADER_RE = re.compile(r'^@@ -([0-9,]+) \+([0-9,]+) @@.*')

    def __init__(self, model, filename='',
                 cached=True, reverse=False,
                 diff_source=None):

        self._idx = -1
        self._diffs = []
        self._diff_spans = []
        self._diff_offsets = []
        self._ranges = []

        self.config = gitcfg.instance()
        self.head = model.head
        self.amending = model.amending()
        self.start = None
        self.end = None
        self.offset = None
        self.diff_sel = []
        self.selected = []
        self.filename = filename
        self.diff_source = diff_source or DiffSource()

        (header, diff) = self.diff_source.get(self.head, self.amending,
                                              filename, cached,
                                              cached or reverse)
        self.model = model
        self.diff = diff
        self.header = header
        self.parse_diff(diff)

        # Always index into the non-reversed diff
        self.fwd_header, self.fwd_diff = \
                self.diff_source.get(self.head,
                                     self.amending,
                                     filename,
                                     cached, False)

    def write_diff(self,filename,which,selected=False,noop=False):
        """Writes a new diff corresponding to the user's selection."""
        if not noop and which < len(self.diff_sel):
            diff = self.diff_sel[which]
            encoding = self.config.file_encoding(self.filename)
            utils.write(filename, self.header + '\n' + diff + '\n',
                        encoding=encoding)
            return True
        else:
            return False

    def ranges(self):
        """Return the diff header ranges"""
        return self._ranges

    def diffs(self):
        """Returns the list of diffs."""
        return self._diffs

    def diff_subset(self, diff, start, end):
        """Processes the diffs and returns a selected subset from that diff.
        """
        adds = 0
        deletes = 0
        existing = 0
        newdiff = []
        local_offset = 0
        offset = self._diff_spans[diff][0]

        ADD = '+'
        DEL = '-'
        NOP = ' '

        for line in self._diffs[diff]:
            line_start = offset + local_offset
            local_offset += len(line) + 1 #\n
            line_end = offset + local_offset
            # |line1 |line2 |line3 |
            #   |--selection--|
            #   '-start       '-end

            # selection has head of diff (line3)
            has_head = start <= line_start and end > line_start and end <= line_end
            # selection has all of diff (line2)
            has_all = start <= line_start and end >= line_end
            # selection has tail of diff (line1)
            has_tail = start >= line_start and start < line_end - 1

            action = line[0:1]
            if has_head or has_all or has_tail:
                newdiff.append(line)
                if action == ADD:
                    adds += 1
                elif action == DEL:
                    deletes += 1
                elif action == NOP:
                    existing += 1
            else:
                # Don't add new lines unless selected
                if action == ADD:
                    continue
                elif action == DEL:
                    # Don't remove lines unless selected
                    newdiff.append(' ' + line[1:])
                    existing += 1
                elif action == NOP:
                    newdiff.append(line)
                    existing += 1
                else:
                    newdiff.append(line)

        diff_range = self._ranges[diff]
        begin_count = existing + deletes
        end_count = existing + adds

        diff_range.set_begin_count(begin_count)
        diff_range.set_end_count(end_count)
        newdiff[0] = diff_range.make()

        return (self.header + '\n' + '\n'.join(newdiff) + '\n')

    def spans(self):
        """Returns the line spans of each hunk."""
        return self._diff_spans

    def offsets(self):
        """Returns the offsets."""
        return self._diff_offsets

    def set_diff_to_offset(self, offset):
        """Sets the diff selection to be the hunk at a particular offset."""
        self.offset = offset
        self.diff_sel, self.selected = self.diff_for_offset(offset)

    def set_diffs_to_range(self, start, end):
        """Sets the diff selection to be a range of hunks."""
        self.start = start
        self.end = end
        self.diff_sel, self.selected = self.diffs_for_range(start,end)

    def diff_for_offset(self, offset):
        """Returns the hunks for a particular offset."""
        for idx, diff_offset in enumerate(self._diff_offsets):
            if offset < diff_offset:
                return (['\n'.join(self._diffs[idx])], [idx])
        return ([],[])

    def diffs_for_range(self, start, end):
        """Returns the hunks for a selected range."""
        diffs = []
        indices = []
        for idx, span in enumerate(self._diff_spans):
            has_end_of_diff = start >= span[0] and start < span[1]
            has_all_of_diff = start <= span[0] and end >= span[1]
            has_head_of_diff = end >= span[0] and end <= span[1]

            selected_diff =(has_end_of_diff
                    or has_all_of_diff
                    or has_head_of_diff)
            if selected_diff:
                diff = '\n'.join(self._diffs[idx])
                diffs.append(diff)
                indices.append(idx)
        return diffs, indices

    def parse_diff(self, diff):
        """Parses a diff and extracts headers, offsets, hunks, etc.
        """
        total_offset = 0
        self._idx = -1

        for line in diff.split('\n'):
            match = self.HEADER_RE.match(line)
            if match:
                self._ranges.append(Range(match.group(1), match.group(2)))
                self._diffs.append([line])

                line_len = len(line) + 1 #\n
                self._diff_spans.append([total_offset,
                                         total_offset + line_len])
                total_offset += line_len
                self._diff_offsets.append(total_offset)
                self._idx += 1
                continue

            if self._idx < 0:
                errmsg = 'Malformed diff?: %s' % diff
                raise AssertionError(errmsg)

            line_len = len(line) + 1
            total_offset += line_len

            self._diffs[self._idx].append(line)
            self._diff_spans[-1][-1] += line_len
            self._diff_offsets[self._idx] += line_len

    def process_diff_selection(self, selected, offset, selection,
                               apply_to_worktree=False):
        """Processes a diff selection and applies changes to git."""
        if selection:
            # qt destroys \r\n and makes it \n with no way of going back.
            # boo!  we work around that here.
            # I think this was win32-specific.  We might want to do
            # this on win32 only (TODO verify)
            if selection not in self.fwd_diff:
                special_selection = selection.replace('\n', '\r\n')
                if special_selection in self.fwd_diff:
                    selection = special_selection
                else:
                    return 0, ''
            start = self.fwd_diff.index(selection)
            end = start + len(selection)
            self.set_diffs_to_range(start, end)
        else:
            self.set_diff_to_offset(offset)
            selected = False

        output = ''
        status = 0
        # Process diff selection only
        if selected:
            encoding = self.config.file_encoding(self.filename)
            for idx in self.selected:
                contents = self.diff_subset(idx, start, end)
                if not contents:
                    continue
                tmpfile = utils.tmp_filename('selection')
                utils.write(tmpfile, contents, encoding=encoding)
                if apply_to_worktree:
                    stat, out = self.model.apply_diff_to_worktree(tmpfile)
                    output += out
                    status = max(status, stat)
                else:
                    stat, out = self.model.apply_diff(tmpfile)
                    output += out
                    status = max(status, stat)
                os.unlink(tmpfile)
        # Process a complete hunk
        else:
            for idx, diff in enumerate(self.diff_sel):
                tmpfile = utils.tmp_filename('patch%02d' % idx)
                if not self.write_diff(tmpfile,idx):
                    continue
                if apply_to_worktree:
                    stat, out = self.model.apply_diff_to_worktree(tmpfile)
                    output += out
                    status = max(status, stat)
                else:
                    stat, out = self.model.apply_diff(tmpfile)
                    output += out
                    status = max(status, stat)
                os.unlink(tmpfile)
        return status, output
