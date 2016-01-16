#!/usr/bin/env python
# encoding: utf-8

from __future__ import absolute_import, division, unicode_literals

import os
import unittest

from cola import compat


class CompatTestCase(unittest.TestCase):
    """Tests the compat module"""

    def test_setenv(self):
        """Test the core.decode function
        """
        key = 'COLA_UNICODE_TEST'
        value = '字龍'
        compat.setenv(key, value)
        self.assertTrue(key in os.environ)
        self.assertTrue(os.getenv(key))

        compat.unsetenv(key)
        self.assertFalse(key in os.environ)
        self.assertFalse(os.getenv(key))


if __name__ == '__main__':
    unittest.main()
