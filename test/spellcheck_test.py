#!/usr/bin/env python
from __future__ import absolute_import, division, unicode_literals
import unittest

from cola import compat
from cola import spellcheck

from . import helper


class TestCase(unittest.TestCase):
    def test_spellcheck_generator(self):
        check = spellcheck.NorvigSpellCheck()
        self.assert_spellcheck(check)

    def test_spellcheck_unicode(self):
        path = helper.fixture('unicode.txt')
        check = spellcheck.NorvigSpellCheck(cracklib=path)
        self.assert_spellcheck(check)

    def assert_spellcheck(self, check):
        for word in check.read():
            self.assertTrue(word is not None)
            self.assertTrue(isinstance(word, compat.ustr))


if __name__ == '__main__':
    unittest.main()
