"""Test the cola.gitcfg module."""
import pathlib

from . import helper
from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


def assert_color(context, expect, git_value, key='test', default=None):
    """Helper function for testing color values"""
    helper.run_git('config', 'fanta.color.%s' % key, git_value)
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
    helper.run_git('config', 'core.hooksPath', str(pathlib.Path('/test/hooks')))
    expect = str(pathlib.Path('/test/hooks/example'))
    actual = app_context.cfg.hooks_path('example')
    assert expect == actual


def test_hooks_path_lowercase(app_context):
    helper.run_git(
        'config', 'core.hookspath', str(pathlib.Path('/test/hooks-lowercase'))
    )
    expect = str(pathlib.Path('/test/hooks-lowercase/example'))
    actual = app_context.cfg.hooks_path('example')
    assert expect == actual


def test_new_config_prefix_is_read(app_context):
    """Ein fanta.*-Key wird gelesen."""
    helper.run_git('config', 'fanta.tabwidth', '4')
    app_context.cfg.reset()

    assert app_context.cfg.get('fanta.tabwidth') == 4


def test_legacy_config_prefix_is_still_read(app_context):
    """Ein alter cola.*-Key wirkt weiterhin, wenn kein fanta.*-Key gesetzt ist."""
    helper.run_git('config', 'cola.tabwidth', '8')
    app_context.cfg.reset()

    assert app_context.cfg.get('fanta.tabwidth') == 8


def test_new_config_prefix_wins_over_legacy(app_context):
    """Ist beides gesetzt, gewinnt der neue Key."""
    helper.run_git('config', 'cola.tabwidth', '8')
    helper.run_git('config', 'fanta.tabwidth', '2')
    app_context.cfg.reset()

    assert app_context.cfg.get('fanta.tabwidth') == 2


def test_legacy_config_prefix_is_read_by_get_all(app_context):
    """get_all() beruecksichtigt den alten Prefix ebenfalls."""
    helper.run_git('config', '--add', 'cola.icontheme', 'dark')
    app_context.cfg.reset()

    assert 'dark' in app_context.cfg.get_all('fanta.icontheme')


def test_unknown_key_still_returns_default(app_context):
    """Der Fallback darf nicht dazu fuehren, dass fremde Keys plotzlich treffen."""
    app_context.cfg.reset()

    assert app_context.cfg.get('fanta.doesnotexist', default='x') == 'x'
    assert app_context.cfg.get('other.doesnotexist', default='y') == 'y'
