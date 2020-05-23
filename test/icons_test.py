#!/usr/bin/env python
# encoding: utf-8
from __future__ import absolute_import, division, unicode_literals
import unittest

from cola import compat
from cola import core
from cola import icons


class IconTestCase(unittest.TestCase):
    def test_from_filename_unicode(self):
        filename = compat.uchr(0x400) + '.py'
        expect = 'file-code.svg'
        actual = icons.basename_from_filename(filename)
        self.assertEqual(expect, actual)

        actual = icons.basename_from_filename(core.encode(filename))
        self.assertEqual(expect, actual)
