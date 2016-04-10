from __future__ import absolute_import, division, unicode_literals

import unittest

from cola import gitcfg

from test import helper


class GitConfigTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.gitcmds module."""
    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)
        self.config = gitcfg.current()

    def test_string(self):
        """Test string values in get()."""
        self.git('config', 'test.value', 'test')
        self.assertEqual(self.config.get('test.value'), 'test')

    def test_int(self):
        """Test int values in get()."""
        self.git('config', 'test.int', '42')
        self.assertEqual(self.config.get('test.int'), 42)

    def test_true(self):
        """Test bool values in get()."""
        self.git('config', 'test.bool', 'true')
        self.assertEqual(self.config.get('test.bool'), True)

    def test_false(self):
        self.git('config', 'test.bool', 'false')
        self.assertEqual(self.config.get('test.bool'), False)

    def test_yes(self):
        self.git('config', 'test.bool', 'yes')
        self.assertEqual(self.config.get('test.bool'), True)

    def test_no(self):
        self.git('config', 'test.bool', 'no')
        self.assertEqual(self.config.get('test.bool'), False)

    def test_bool_no_value(self):
        self.append_file('.git/config', '[test]\n')
        self.append_file('.git/config', '\tbool\n')
        self.assertEqual(self.config.get('test.bool'), True)

    def test_empty_value(self):
        self.append_file('.git/config', '[test]\n')
        self.append_file('.git/config', '\tvalue = \n')
        self.assertEqual(self.config.get('test.value'), '')

    def test_default(self):
        """Test default values in get()."""
        self.assertEqual(self.config.get('does.not.exist'), None)
        self.assertEqual(self.config.get('does.not.exist', default=42), 42)

    def test_guitool_opts(self):
        self.git('config', 'guitool.hello world.cmd', 'hello world')
        opts = self.config.get_guitool_opts('hello world')
        expect = 'hello world'
        actual = opts['cmd']
        self.assertEqual(expect, actual)

    def test_guitool_names(self):
        self.git('config', 'guitool.hello meow.cmd', 'hello meow')
        names = self.config.get_guitool_names()
        self.assertTrue('hello meow' in names)

    def test_guitool_names_mixed_case(self):
        self.git('config', 'guitool.Meow Cat.cmd', 'cat hello')
        names = self.config.get_guitool_names()
        self.assertTrue('Meow Cat' in names)

    def test_find_mixed_case(self):
        self.git('config', 'guitool.Meow Cat.cmd', 'cat hello')
        opts = self.config.find('guitool.Meow Cat.*')
        self.assertEqual(opts['guitool.Meow Cat.cmd'], 'cat hello')

    def test_guitool_opts_mixed_case(self):
        self.git('config', 'guitool.Meow Cat.cmd', 'cat hello')
        opts = self.config.get_guitool_opts('Meow Cat')
        self.assertEqual(opts['cmd'], 'cat hello')


if __name__ == '__main__':
    unittest.main()
