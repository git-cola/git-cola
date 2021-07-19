"""Text wrapping and filling"""
from __future__ import absolute_import, division, print_function, unicode_literals
import re

from .compat import ustr

# Copyright (C) 1999-2001 Gregory P. Ward.
# Copyright (C) 2002, 2003 Python Software Foundation.
# Copyright (C) 2013, David Aguilar
# Written by Greg Ward <gward@python.net>
# Simplified for git-cola by David Aguilar <davvid@gmail.com>


class TextWrapper(object):
    """
    Object for wrapping/filling text.  The public interface consists of
    the wrap() and fill() methods; the other methods are just there for
    subclasses to override in order to tweak the default behaviour.
    If you want to completely replace the main wrapping algorithm,
    you'll probably have to override _wrap_chunks().

    Several instance attributes control various aspects of wrapping:
      width (default: 70)
        The preferred width of wrapped lines.
      tabwidth (default: 8)
        The width of a tab used when calculating line length.
      break_on_hyphens (default: false)
        Allow breaking hyphenated words. If true, wrapping will occur
        preferably on whitespaces and right after hyphens part of
        compound words.
      drop_whitespace (default: true)
        Drop leading and trailing whitespace from lines.
    """

    # This funky little regex is just the trick for splitting
    # text up into word-wrappable chunks.  E.g.
    #   "Hello there -- you goof-ball, use the -b option!"
    # splits into
    #   Hello/ /there/ /--/ /you/ /goof-/ball,/ /use/ /the/ /-b/ /option!
    # (after stripping out empty strings).
    wordsep_re = re.compile(
        r'(\s+|'  # any whitespace
        r'[^\s\w]*\w+[^0-9\W]-(?=\w+[^0-9\W])|'  # hyphenated words
        r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w))'
    )  # em-dash

    # This less funky little regex just split on recognized spaces. E.g.
    #   "Hello there -- you goof-ball, use the -b option!"
    # splits into
    #   Hello/ /there/ /--/ /you/ /goof-ball,/ /use/ /the/ /-b/ /option!/
    wordsep_simple_re = re.compile(r'(\s+)')

    def __init__(
        self, width=70, tabwidth=8, break_on_hyphens=False, drop_whitespace=True
    ):
        self.width = width
        self.tabwidth = tabwidth
        self.break_on_hyphens = break_on_hyphens
        self.drop_whitespace = drop_whitespace

        # recompile the regexes for Unicode mode -- done in this clumsy way for
        # backwards compatibility because it's rather common to monkey-patch
        # the TextWrapper class' wordsep_re attribute.
        self.wordsep_re_uni = re.compile(self.wordsep_re.pattern, re.U)
        self.wordsep_simple_re_uni = re.compile(self.wordsep_simple_re.pattern, re.U)

    def _split(self, text):
        """_split(text : string) -> [string]

        Split the text to wrap into indivisible chunks.  Chunks are
        not quite the same as words; see _wrap_chunks() for full
        details.  As an example, the text
          Look, goof-ball -- use the -b option!
        breaks into the following chunks:
          'Look,', ' ', 'goof-', 'ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', 'option!'
        if break_on_hyphens is True, or in:
          'Look,', ' ', 'goof-ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', option!'
        otherwise.
        """
        if isinstance(text, ustr):
            if self.break_on_hyphens:
                pat = self.wordsep_re_uni
            else:
                pat = self.wordsep_simple_re_uni
        else:
            if self.break_on_hyphens:
                pat = self.wordsep_re
            else:
                pat = self.wordsep_simple_re
        chunks = pat.split(text)
        chunks = list(filter(None, chunks))  # remove empty chunks
        return chunks

    def _wrap_chunks(self, chunks):
        """_wrap_chunks(chunks : [string]) -> [string]

        Wrap a sequence of text chunks and return a list of lines of length
        'self.width' or less.  Some lines may be longer than this.  Chunks
        correspond roughly to words and the whitespace between them: each
        chunk is indivisible, but a line break can come between any two
        chunks.  Chunks should not have internal whitespace; ie. a chunk is
        either all whitespace or a "word".  Whitespace chunks will be removed
        from the beginning and end of lines, but apart from that whitespace is
        preserved.
        """
        lines = []

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks = list(reversed(chunks))

        while chunks:

            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Maximum width for this line.
            width = self.width

            # First chunk on line is a space -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and is_blank(chunks[-1]) and lines:
                chunks.pop()

            linebreak = False
            while chunks:
                length = self.chunklen(chunks[-1])

                # Can at least squeeze this chunk onto the current line.
                if cur_len + length <= width:
                    cur_line.append(chunks.pop())
                    cur_len += length
                # Nope, this line is full.
                else:
                    linebreak = True
                    break

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and self.chunklen(chunks[-1]) > width:
                if not cur_line:
                    cur_line.append(chunks.pop())

            # Avoid whitespace at the beginining of split lines
            if (
                linebreak
                and self.drop_whitespace
                and cur_line
                and is_blank(cur_line[0])
            ):
                cur_line.pop(0)

            # If the last chunk on this line is all a space, drop it.
            if self.drop_whitespace and cur_line and is_blank(cur_line[-1]):
                cur_line.pop()

            # Convert current line back to a string and store it in list
            # of all lines (return value).
            if cur_line:
                lines.append(''.join(cur_line))

        return lines

    def chunklen(self, word):
        """Return length of a word taking tabs into account

        >>> w = TextWrapper(tabwidth=8)
        >>> w.chunklen("\\t\\t\\t\\tX")
        33

        """
        return len(word.replace('\t', '')) + word.count('\t') * self.tabwidth

    # -- Public interface ----------------------------------------------

    def wrap(self, text):
        """wrap(text : string) -> [string]

        Reformat the single paragraph in 'text' so it fits in lines of
        no more than 'self.width' columns, and return a list of wrapped
        lines.  Tabs in 'text' are expanded with string.expandtabs(),
        and all other whitespace characters (including newline) are
        converted to space.
        """
        chunks = self._split(text)
        return self._wrap_chunks(chunks)

    def fill(self, text):
        """fill(text : string) -> string

        Reformat the single paragraph in 'text' to fit in lines of no
        more than 'self.width' columns, and return a new string
        containing the entire wrapped paragraph.
        """
        return "\n".join(self.wrap(text))


def word_wrap(text, tabwidth, limit, break_on_hyphens=False):
    """Wrap long lines to the specified limit"""

    lines = []

    # Acked-by:, Signed-off-by:, Helped-by:, etc.
    special_tag_rgx = re.compile(
        r'^('
        r'(('
        r'Acked-by|'
        r"Ack'd-by|"
        r'Based-on-patch-by|'
        r'Cheered-on-by|'
        r'Co-authored-by|'
        r'Comments-by|'
        r'Confirmed-by|'
        r'Contributions-by|'
        r'Debugged-by|'
        r'Discovered-by|'
        r'Explained-by|'
        r'Backtraced-by|'
        r'Helped-by|'
        r'Liked-by|'
        r'Link|'
        r'Improved-by|'
        r'Inspired-by|'
        r'Initial-patch-by|'
        r'Noticed-by|'
        r'Original-patch-by|'
        r'Originally-by|'
        r'Mentored-by|'
        r'Patch-by|'
        r'Proposed-by|'
        r'References|'
        r'Related-to|'
        r'Reported-by|'
        r'Requested-by|'
        r'Reviewed-by|'
        r'See-also|'
        r'Signed-off-by|'
        r'Signed-Off-by|'
        r'Spotted-by|'
        r'Suggested-by|'
        r'Tested-by|'
        r'Tested-on-([a-zA-Z-_]+)-by|'
        r'With-suggestions-by'
        r'):)'
        r'|([Cc]\.\s*[Ff]\.\s+)'
        r')'
    )

    w = TextWrapper(
        width=limit,
        tabwidth=tabwidth,
        break_on_hyphens=break_on_hyphens,
        drop_whitespace=True,
    )

    for line in text.split('\n'):
        if special_tag_rgx.match(line):
            lines.append(line)
        else:
            lines.append(w.fill(line))

    return '\n'.join(lines)


def is_blank(string):
    return string and not string.strip(' ')
