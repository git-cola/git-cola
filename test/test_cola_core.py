#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import os
import unittest

import helper

from cola import core

class CoreColaUnicodeTestCase(unittest.TestCase):
    """Tests the cola.core module's unicode handling
    """

    def test_core_decode(self):
        """Test the core.decode function
        """
        filename = helper.fixture('unicode.txt')
        fh = open(filename)
        content = fh.read().strip()
        fh.close()
        self.assertEqual(core.decode(content), u'unicøde')

    def test_core_encode(self):
        """Test the core.encode function
        """
        filename = helper.fixture('unicode.txt')
        fh = open(filename)
        content = fh.read().strip()
        fh.close()
        self.assertEqual(content, core.encode(u'unicøde'))

if __name__ == '__main__':
    unittest.main()
