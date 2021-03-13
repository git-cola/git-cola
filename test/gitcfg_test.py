from __future__ import absolute_import, division, unicode_literals
import unittest

from . import helper


class GitConfigTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.gitcmds module."""

    def test_string(self):
        """Test string values in get()."""
        self.run_git('config', 'test.value', 'test')
        self.assertEqual(self.cfg.get('test.value'), 'test')

    def test_int(self):
        """Test int values in get()."""
        self.run_git('config', 'test.int', '42')
        self.assertEqual(self.cfg.get('test.int'), 42)

    def test_true(self):
        """Test bool values in get()."""
        self.run_git('config', 'test.bool', 'true')
        self.assertEqual(self.cfg.get('test.bool'), True)

    def test_false(self):
        self.run_git('config', 'test.bool', 'false')
        self.assertEqual(self.cfg.get('test.bool'), False)

    def test_yes(self):
        self.run_git('config', 'test.bool', 'yes')
        self.assertEqual(self.cfg.get('test.bool'), True)

    def test_no(self):
        self.run_git('config', 'test.bool', 'no')
        self.assertEqual(self.cfg.get('test.bool'), False)

    def test_bool_no_value(self):
        self.append_file('.git/config', '[test]\n')
        self.append_file('.git/config', '\tbool\n')
        self.assertEqual(self.cfg.get('test.bool'), True)

    def test_empty_value(self):
        self.append_file('.git/config', '[test]\n')
        self.append_file('.git/config', '\tvalue = \n')
        self.assertEqual(self.cfg.get('test.value'), '')

    def test_default(self):
        """Test default values in get()."""
        self.assertEqual(self.cfg.get('does.not.exist'), None)
        self.assertEqual(self.cfg.get('does.not.exist', default=42), 42)

    def test_get_all(self):
        """Test getting multiple values in get_all()"""
        self.run_git('config', '--add', 'test.value', 'abc')
        self.run_git('config', '--add', 'test.value', 'def')
        expect = ['abc', 'def']
        self.assertEqual(expect, self.cfg.get_all('test.value'))

    def assert_color(self, expect, git_value, key='test', default=None):
        self.run_git('config', 'cola.color.%s' % key, git_value)
        self.cfg.reset()
        actual = self.cfg.color(key, default)
        self.assertEqual(expect, actual)

    def test_color_rrggbb(self):
        self.assert_color((0xAA, 0xBB, 0xCC), 'aabbcc')
        self.assert_color((0xAA, 0xBB, 0xCC), '#aabbcc')

    def test_color_int(self):
        self.assert_color((0x10, 0x20, 0x30), '102030')
        self.assert_color((0x10, 0x20, 0x30), '#102030')

    def test_guitool_opts(self):
        self.run_git('config', 'guitool.hello world.cmd', 'hello world')
        opts = self.cfg.get_guitool_opts('hello world')
        expect = 'hello world'
        actual = opts['cmd']
        self.assertEqual(expect, actual)

    def test_guitool_names(self):
        self.run_git('config', 'guitool.hello meow.cmd', 'hello meow')
        names = self.cfg.get_guitool_names()
        self.assertTrue('hello meow' in names)

    def test_guitool_names_mixed_case(self):
        self.run_git('config', 'guitool.Meow Cat.cmd', 'cat hello')
        names = self.cfg.get_guitool_names()
        self.assertTrue('Meow Cat' in names)

    def test_find_mixed_case(self):
        self.run_git('config', 'guitool.Meow Cat.cmd', 'cat hello')
        opts = self.cfg.find('guitool.Meow Cat.*')
        self.assertEqual(opts['guitool.Meow Cat.cmd'], 'cat hello')

    def test_guitool_opts_mixed_case(self):
        self.run_git('config', 'guitool.Meow Cat.cmd', 'cat hello')
        opts = self.cfg.get_guitool_opts('Meow Cat')
        self.assertEqual(opts['cmd'], 'cat hello')

    def test_hooks(self):
        self.run_git('config', 'core.hooksPath', '/test/hooks')
        expect = '/test/hooks'
        actual = self.cfg.hooks()
        assert expect == actual

    def test_hooks_lowercase(self):
        self.run_git('config', 'core.hookspath', '/test/hooks-lowercase')
        expect = '/test/hooks-lowercase'
        actual = self.cfg.hooks()
        assert expect == actual

    def test_hooks_path(self):
        self.run_git('config', 'core.hooksPath', '/test/hooks')
        expect = '/test/hooks/example'
        actual = self.cfg.hooks_path('example')
        assert expect == actual

    def test_hooks_path_lowercase(self):
        self.run_git('config', 'core.hookspath', '/test/hooks-lowercase')
        expect = '/test/hooks-lowercase/example'
        actual = self.cfg.hooks_path('example')
        assert expect == actual


if __name__ == '__main__':
    unittest.main()
