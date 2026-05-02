"""Per-repository theme: coercion, prefs helpers, and config model (mocked git).

Requires the same Qt stack as the rest of git-cola (qtpy + PyQt/PySide).
Without it, the whole module is skipped at import time.
"""
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

import pytest

try:
    from qtpy import QtCore  # noqa: F401
except Exception as exc:
    pytest.skip(f'Qt bindings required: {exc}', allow_module_level=True)

from cola import app as cola_app
from cola import themes
from cola.models import prefs
from cola.models.prefs import PreferencesModel
from cola.models.prefs import SetConfig


@pytest.mark.parametrize(
    'raw,expected',
    [
        (None, 'default'),
        ('', 'default'),
        ('   ', 'default'),
        (True, 'default'),
        (False, 'default'),
        (42, 'default'),
        ('no-such-theme-ever-xyz-999', 'default'),
        ('default', 'default'),
        ('flat-dark-blue', 'flat-dark-blue'),
    ],
)
def test_coerce_gui_theme_name(raw, expected):
    assert themes.coerce_gui_theme_name(raw) == expected


def test_registered_theme_names_contains_default():
    names = themes.registered_theme_names()
    assert 'default' in names
    assert 'flat-dark-blue' in names


def test_find_theme_unknown_returns_default_named_theme():
    theme = themes.find_theme('__invalid__')
    assert theme.name == 'default'


def test_gui_theme_reads_cfg_and_coerces():
    context = Mock()
    context.cfg = Mock()
    context.cfg.get = Mock(return_value='not-a-real-theme')
    assert prefs.gui_theme(context) == 'default'
    context.cfg.get.assert_called_once_with(prefs.THEME, default=prefs.Defaults.theme)


def test_gui_theme_preserves_valid_name():
    context = Mock()
    context.cfg = Mock()
    context.cfg.get = Mock(return_value='flat-dark-green')
    assert prefs.gui_theme(context) == 'flat-dark-green'


def test_preferences_model_set_config_local_theme():
    context = Mock()
    context.cfg = Mock()
    model = PreferencesModel(context)
    model.set_config('local', prefs.THEME, 'flat-dark-blue')
    context.cfg.set_repo.assert_called_once_with(prefs.THEME, 'flat-dark-blue')


def test_preferences_model_set_config_global_theme():
    context = Mock()
    context.cfg = Mock()
    model = PreferencesModel(context)
    model.set_config('global', prefs.THEME, 'default')
    context.cfg.set_user.assert_called_once_with(prefs.THEME, 'default')


def test_preferences_model_get_config_routes_by_source():
    context = Mock()
    context.cfg = Mock()
    context.cfg.get_repo = Mock(return_value='flat-light-blue')
    context.cfg.get_user_or_system = Mock(return_value='flat-dark-grey')
    model = PreferencesModel(context)
    assert model.get_config('local', prefs.THEME) == 'flat-light-blue'
    assert model.get_config('global', prefs.THEME) == 'flat-dark-grey'


def test_set_config_command_local_roundtrip_mock():
    context = Mock()
    cfg = Mock()
    cfg.get_repo = Mock(return_value='default')
    context.cfg = cfg
    model = PreferencesModel(context)
    cmd = SetConfig(model, 'local', prefs.THEME, 'flat-dark-red')
    cmd.do()
    cfg.get_repo.assert_called_with(prefs.THEME)
    cfg.set_repo.assert_called_once_with(prefs.THEME, 'flat-dark-red')
    cmd.undo()
    assert cfg.set_repo.call_args_list[-1] == call(prefs.THEME, 'default')


def test_get_icon_themes_strips_and_skips_empty():
    context = Mock()
    context.cfg = Mock()
    context.cfg.get_all = Mock(return_value=['', '  dark  ', 'light'])
    with patch.object(cola_app.core, 'getenv', return_value=None):
        names = cola_app.get_icon_themes(context)
    assert 'dark' in names
    assert 'light' in names


def test_get_icon_themes_env_split_strips():
    context = Mock()
    context.cfg = Mock()
    context.cfg.get_all = Mock(return_value=[])
    with patch.object(cola_app.core, 'getenv', return_value=' dark : light '):
        names = cola_app.get_icon_themes(context)
    assert names[:2] == ['dark', 'light']


def test_get_icon_themes_non_strings_skipped():
    context = Mock()
    context.cfg = Mock()
    context.cfg.get_all = Mock(return_value=[99, None, 'dark'])
    with patch.object(cola_app.core, 'getenv', return_value=None):
        names = cola_app.get_icon_themes(context)
    assert names == ['dark']


def test_get_icon_themes_defaults_to_light_when_empty():
    context = Mock()
    context.cfg = Mock()
    context.cfg.get_all = Mock(return_value=[])
    with patch.object(cola_app.core, 'getenv', return_value=None):
        names = cola_app.get_icon_themes(context)
    assert names == ['light']
