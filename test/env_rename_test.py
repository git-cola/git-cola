"""Tests fuer die Umbenennung der GIT_COLA_*-Umgebungsvariablen."""

from cola import compat

from . import helper
from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


def test_getenv_prefers_new_name(monkeypatch):
    """Der neue Name gewinnt, wenn beide gesetzt sind."""
    monkeypatch.setenv('GIT_FANTA_TRACE', 'neu')
    monkeypatch.setenv('GIT_COLA_TRACE', 'alt')

    assert compat.getenv_with_legacy('GIT_FANTA_TRACE') == 'neu'


def test_getenv_falls_back_to_legacy_name(monkeypatch):
    """Ist nur der alte Name gesetzt, wird er benutzt."""
    monkeypatch.delenv('GIT_FANTA_TRACE', raising=False)
    monkeypatch.setenv('GIT_COLA_TRACE', 'alt')

    assert compat.getenv_with_legacy('GIT_FANTA_TRACE') == 'alt'


def test_getenv_returns_default_when_neither_is_set(monkeypatch):
    monkeypatch.delenv('GIT_FANTA_TRACE', raising=False)
    monkeypatch.delenv('GIT_COLA_TRACE', raising=False)

    assert compat.getenv_with_legacy('GIT_FANTA_TRACE', 'standard') == 'standard'


def test_commit_message_path_prefers_new_file(app_context):
    """Existiert .git/GIT_FANTA_MSG, wird diese Datei benutzt."""
    from cola import gitcmds

    new_path = app_context.git.git_path('GIT_FANTA_MSG')
    helper.write_file(new_path, 'neue Nachricht')

    assert gitcmds.commit_message_path(app_context) == new_path


def test_commit_message_path_falls_back_to_legacy_file(app_context):
    """Existiert nur .git/GIT_COLA_MSG, wird diese Datei benutzt."""
    from cola import gitcmds

    legacy_path = app_context.git.git_path('GIT_COLA_MSG')
    helper.write_file(legacy_path, 'alte Nachricht')

    assert gitcmds.commit_message_path(app_context) == legacy_path


def test_commit_message_path_returns_none_without_a_file(app_context):
    """Ohne Datei bleibt der Rueckgabewert None - der bestehende Vertrag."""
    from cola import gitcmds

    assert gitcmds.commit_message_path(app_context) is None


def test_save_commitmsg_writes_the_new_file(app_context):
    """Geschrieben wird immer nur noch .git/GIT_FANTA_MSG."""
    from cola import core

    path = app_context.model.save_commitmsg('hallo')

    assert path.endswith('GIT_FANTA_MSG')
    assert core.read(path) == 'hallo\n'
