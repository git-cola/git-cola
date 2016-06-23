#!/usr/bin/env python

from __future__ import absolute_import, division, unicode_literals

import unittest
from cola import gravatar
from cola.compat import ustr


class GravatarTestCase(unittest.TestCase):

    def test_url_for_email_(self):
        email = 'email@example.com'
        expect = (r'https://gravatar.com/avatar/'
                  r'5658ffccee7f0ebfda2b226238b1eb6e'
                  r'?s=64'
                  r'&d=https%3A%2F%2Fgit-cola.github.io'
                  r'%2Fimages%2Fgit-64x64.jpg')
        actual = gravatar.Gravatar.url_for_email(email, 64)
        self.assertEqual(expect, actual)
        self.assertEqual(ustr, type(actual))


if __name__ == '__main__':
    unittest.main()
