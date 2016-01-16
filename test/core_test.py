#!/usr/bin/env python
# encoding: utf-8

from __future__ import absolute_import, division, unicode_literals
import unittest

from cola import core

from test import helper


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


if __name__ == '__main__':
    unittest.main()
