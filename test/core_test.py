#!/usr/bin/env python
# encoding: utf-8
from __future__ import absolute_import, division, unicode_literals
import unittest

from cola import core

from . import helper


class CoreColaUnicodeTestCase(unittest.TestCase):
    """Tests the cola.core module's unicode handling
    """

    def test_core_decode(self):
        """Test the core.decode function
        """
        filename = helper.fixture('unicode.txt')
        expect = core.decode(core.encode('unicøde'))
        actual = core.read(filename).strip()
        self.assertEqual(expect, actual)

    def test_core_encode(self):
        """Test the core.encode function
        """
        filename = helper.fixture('unicode.txt')
        expect = core.encode('unicøde')
        actual = core.encode(core.read(filename).strip())
        self.assertEqual(expect, actual)

    def test_decode_None(self):
        """Ensure that decode(None) returns None"""
        expect = None
        actual = core.decode(None)
        self.assertEqual(expect, actual)

    def test_decode_utf8(self):
        filename = helper.fixture('cyrillic-utf-8.txt')
        actual = core.read(filename)
        self.assertEqual(actual.encoding, 'utf-8')

    def test_decode_non_utf8(self):
        filename = helper.fixture('cyrillic-cp1251.txt')
        actual = core.read(filename)
        self.assertEqual(actual.encoding, 'iso-8859-15')

    def test_decode_non_utf8_string(self):
        filename = helper.fixture('cyrillic-cp1251.txt')
        with open(filename, 'rb') as f:
            content = f.read()
        actual = core.decode(content)
        self.assertEqual(actual.encoding, 'iso-8859-15')


if __name__ == '__main__':
    unittest.main()
