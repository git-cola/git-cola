from __future__ import absolute_import, division, unicode_literals
import unittest

from cola import i18n
from cola.i18n import N_
from cola.compat import uchr


class ColaI18nTestCase(unittest.TestCase):
    """Test cases for the ColaApplication class"""

    def tearDown(self):
        i18n.uninstall()

    def test_translates_noun(self):
        """Test that strings with @@noun are translated"""
        i18n.install('ja_JP')
        expect = uchr(0x30B3) + uchr(0x30DF) + uchr(0x30C3) + uchr(0x30C8)
        actual = N_('Commit@@verb')
        self.assertEqual(expect, actual)

    def test_translates_verb(self):
        """Test that strings with @@verb are translated"""
        i18n.install('de_DE')
        expect = 'Commit aufnehmen'
        actual = N_('Commit@@verb')
        self.assertEqual(expect, actual)

    def test_translates_english_noun(self):
        """Test that English strings with @@noun are properly handled"""
        i18n.install('en_US.UTF-8')
        expect = 'Commit'
        actual = N_('Commit@@noun')
        self.assertEqual(expect, actual)

    def test_translates_english_verb(self):
        """Test that English strings with @@verb are properly handled"""
        i18n.install('en_US.UTF-8')
        expect = 'Commit'
        actual = N_('Commit@@verb')
        self.assertEqual(expect, actual)

    def test_translates_random_english(self):
        """Test that random English strings are passed through as-is"""
        i18n.install('en_US.UTF-8')
        expect = 'Random'
        actual = N_('Random')
        self.assertEqual(expect, actual)

    def test_translate_push_pull_french(self):
        i18n.install('fr_FR')
        expect = 'Tirer'
        actual = N_('Pull')
        self.assertEqual(expect, actual)

        expect = 'Pousser'
        actual = N_('Push')
        self.assertEqual(expect, actual)


if __name__ == '__main__':
    unittest.main()
