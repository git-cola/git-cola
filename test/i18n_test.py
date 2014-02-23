# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import sip
sip.setapi('QString', 1)

import unittest

from PyQt4 import QtCore

from cola import i18n
from cola.i18n import N_
from cola.compat import unichr


class ColaI18nTestCase(unittest.TestCase):
    """Test cases for the ColaApplication class"""

    def tearDown(self):
        i18n.uninstall()

    def test_translates_noun(self):
        """Test that strings with @@noun are translated
        """
        i18n.install('ja_JP')
        expect = (unichr(0x30b3) + unichr(0x30df) +
                  unichr(0x30c3) + unichr(0x30c8))
        actual = N_('Commit@@verb')
        self.assertEqual(expect, actual)

    def test_translates_verb(self):
        """Test that strings with @@verb are translated
        """
        i18n.install('de_DE')
        expect = 'Version aufnehmen'
        actual = N_('Commit@@verb')
        self.assertEqual(expect, actual)

    def test_translates_english_noun(self):
        """Test that English strings with @@noun are properly handled
        """
        i18n.install('en_US.UTF-8')
        expect = 'Commit'
        actual = N_('Commit@@noun')
        self.assertEqual(expect, actual)

    def test_translates_english_verb(self):
        """Test that English strings with @@verb are properly handled
        """
        i18n.install('en_US.UTF-8')
        expect = 'Commit'
        actual = N_('Commit@@verb')
        self.assertEqual(expect, actual)

    def test_translates_random_english(self):
        """Test that random English strings are passed through as-is
        """
        i18n.install('en_US.UTF-8')
        expect = 'Random'
        actual = N_('Random')
        self.assertEqual(expect, actual)

    def test_guards_against_qstring(self):
        """Test that random QString is passed through as-is
        """
        i18n.install('en_US.UTF-8')
        expect = 'Random'
        actual = i18n.gettext(QtCore.QString('Random'))
        self.assertEqual(expect, actual)


if __name__ == '__main__':
    unittest.main()
