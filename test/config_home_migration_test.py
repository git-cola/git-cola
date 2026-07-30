"""Tests fuer die Migration von ~/.config/git-cola nach ~/.config/git-fanta."""

import os

from cola import resources


def test_config_home_points_at_git_fanta(monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))

    assert resources.config_home('settings') == str(tmp_path / 'git-fanta' / 'settings')


def test_migration_copies_the_legacy_directory(monkeypatch, tmp_path):
    """Existiert nur das alte Verzeichnis, wird es einmalig kopiert."""
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    legacy = tmp_path / 'git-cola'
    legacy.mkdir()
    (legacy / 'settings').write_text('{"recent": []}', encoding='utf-8')

    resources.migrate_config_home()

    assert (tmp_path / 'git-fanta' / 'settings').read_text(
        encoding='utf-8'
    ) == '{"recent": []}'
    # Das alte Verzeichnis bleibt als Sicherheitsnetz liegen.
    assert legacy.is_dir()


def test_migration_does_not_overwrite_an_existing_directory(monkeypatch, tmp_path):
    """Existiert das neue Verzeichnis schon, wird nichts angefasst."""
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    legacy = tmp_path / 'git-cola'
    legacy.mkdir()
    (legacy / 'settings').write_text('alt', encoding='utf-8')
    current = tmp_path / 'git-fanta'
    current.mkdir()
    (current / 'settings').write_text('neu', encoding='utf-8')

    resources.migrate_config_home()

    assert (current / 'settings').read_text(encoding='utf-8') == 'neu'


def test_migration_is_a_noop_without_a_legacy_directory(monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))

    resources.migrate_config_home()

    assert not (tmp_path / 'git-fanta').exists()
