"""Test the cola.gitcfg module."""
# pylint: disable=redefined-outer-name
from __future__ import absolute_import, division, print_function, unicode_literals

from . import helper
from .helper import app_context


# These assertions make flake8 happy. It considers them unused imports otherwise.
assert app_context is not None


def assert_color(context, expect, git_value, key='test', default=None):
    """Helper function for testing color values"""
    helper.run_git('config', 'cola.color.%s' % key, git_value)
    context.cfg.reset()
    actual = context.cfg.color(key, default)
    assert expect == actual


def test_string(app_context):
    """Test string values in get()."""
    helper.run_git('config', 'test.value', 'test')
    assert app_context.cfg.get('test.value') == 'test'


def test_int(app_context):
    """Test int values in get()."""
    helper.run_git('config', 'test.int', '42')
    expect = 42
    actual = app_context.cfg.get('test.int')
    assert expect == actual


def test_true(app_context):
    """Test bool values in get()."""
    helper.run_git('config', 'test.bool', 'true')
    assert app_context.cfg.get('test.bool') is True


def test_false(app_context):
    helper.run_git('config', 'test.bool', 'false')
    assert app_context.cfg.get('test.bool') is False


def test_yes(app_context):
    helper.run_git('config', 'test.bool', 'yes')
    assert app_context.cfg.get('test.bool') is True


def test_no(app_context):
    helper.run_git('config', 'test.bool', 'no')
    assert app_context.cfg.get('test.bool') is False


def test_bool_no_value(app_context):
    helper.append_file('.git/config', '[test]\n')
    helper.append_file('.git/config', '\tbool\n')
    assert app_context.cfg.get('test.bool') is True


def test_empty_value(app_context):
    helper.append_file('.git/config', '[test]\n')
    helper.append_file('.git/config', '\tvalue = \n')
    assert app_context.cfg.get('test.value') == ''


def test_default(app_context):
    """Test default values in get()."""
    assert app_context.cfg.get('does.not.exist') is None
    assert app_context.cfg.get('does.not.exist', default=42) == 42


def test_get_all(app_context):
    """Test getting multiple values in get_all()"""
    helper.run_git('config', '--add', 'test.value', 'abc')
    helper.run_git('config', '--add', 'test.value', 'def')
    expect = ['abc', 'def']
    assert expect == app_context.cfg.get_all('test.value')


def test_color_rrggbb(app_context):
    assert_color(app_context, (0xAA, 0xBB, 0xCC), 'aabbcc')
    assert_color(app_context, (0xAA, 0xBB, 0xCC), '#aabbcc')


def test_color_int(app_context):
    assert_color(app_context, (0x10, 0x20, 0x30), '102030')
    assert_color(app_context, (0x10, 0x20, 0x30), '#102030')


def test_guitool_opts(app_context):
    helper.run_git('config', 'guitool.hello world.cmd', 'hello world')
    opts = app_context.cfg.get_guitool_opts('hello world')
    expect = 'hello world'
    actual = opts['cmd']
    assert expect == actual


def test_guitool_names(app_context):
    helper.run_git('config', 'guitool.hello meow.cmd', 'hello meow')
    names = app_context.cfg.get_guitool_names()
    assert 'hello meow' in names


def test_guitool_names_mixed_case(app_context):
    helper.run_git('config', 'guitool.Meow Cat.cmd', 'cat hello')
    names = app_context.cfg.get_guitool_names()
    assert 'Meow Cat' in names


def test_find_mixed_case(app_context):
    helper.run_git('config', 'guitool.Meow Cat.cmd', 'cat hello')
    opts = app_context.cfg.find('guitool.Meow Cat.*')
    assert opts['guitool.Meow Cat.cmd'] == 'cat hello'


def test_guitool_opts_mixed_case(app_context):
    helper.run_git('config', 'guitool.Meow Cat.cmd', 'cat hello')
    opts = app_context.cfg.get_guitool_opts('Meow Cat')
    assert opts['cmd'] == 'cat hello'


def test_hooks(app_context):
    helper.run_git('config', 'core.hooksPath', '/test/hooks')
    expect = '/test/hooks'
    actual = app_context.cfg.hooks()
    assert expect == actual


def test_hooks_lowercase(app_context):
    helper.run_git('config', 'core.hookspath', '/test/hooks-lowercase')
    expect = '/test/hooks-lowercase'
    actual = app_context.cfg.hooks()
    assert expect == actual


def test_hooks_path(app_context):
    helper.run_git('config', 'core.hooksPath', '/test/hooks')
    expect = '/test/hooks/example'
    actual = app_context.cfg.hooks_path('example')
    assert expect == actual


def test_hooks_path_lowercase(app_context):
    helper.run_git('config', 'core.hookspath', '/test/hooks-lowercase')
    expect = '/test/hooks-lowercase/example'
    actual = app_context.cfg.hooks_path('example')
    assert expect == actual
