"""Tests for the i18n translation module"""
import os

import pytest

from cola import i18n
from cola.i18n import N_
from cola.compat import uchr


@pytest.fixture(autouse=True)
def i18n_context():
    """Perform cleanup/teardown of the i18n module"""
    yield
    i18n.uninstall()


def test_translates_noun():
    """Test that strings with @@noun are translated"""
    i18n.install('ja_JP')
    expect = uchr(0x30B3) + uchr(0x30DF) + uchr(0x30C3) + uchr(0x30C8)
    actual = N_('Commit@@verb')
    assert expect == actual


def test_translates_verb():
    """Test that strings with @@verb are translated"""
    i18n.install('de_DE')
    expect = 'Commit aufnehmen'
    actual = N_('Commit@@verb')
    assert expect == actual


def test_translates_english_noun():
    """Test that English strings with @@noun are properly handled"""
    i18n.install('en_US.UTF-8')
    expect = 'Commit'
    actual = N_('Commit@@noun')
    assert expect == actual


def test_translates_english_verb():
    """Test that English strings with @@verb are properly handled"""
    i18n.install('en_US.UTF-8')
    expect = 'Commit'
    actual = N_('Commit@@verb')
    assert expect == actual


def test_translates_random_english():
    """Test that random English strings are passed through as-is"""
    i18n.install('en_US.UTF-8')
    expect = 'Random'
    actual = N_('Random')
    assert expect == actual


def test_avoid_translation_git_jargon():
    languages = [
        'cs_CS',
        'de_DE',
        'es_ES',
        'fr_FR',
        'hu_HU',
        'id_ID',
        'it_IT',
        'ja_JP',
        'pl_PL',
        'pt_BR',
        'ru_RU',
        'sv_SV',
        'tr_TR',
        'uk_UK',
        'zh_CN',
        'zh_TW',
    ]

    expected_pull = 'Pull'
    expected_push = 'Push'
    failed_languages_pull = []
    failed_languages_push = []

    for language in languages:
        i18n.install(language)
        if not expected_pull == N_(expected_pull):
            failed_languages_pull.append(language)

        if not expected_push == N_(expected_push):
            failed_languages_push.append(language)

        i18n.uninstall()

    if failed_languages_pull:
        print('\nFailed languages pull:', failed_languages_pull)
    if failed_languages_push:
        print('Failed languages push:', failed_languages_push)

    assert failed_languages_push == []
    assert failed_languages_push == []


def test_get_filename_for_locale():
    """Ensure that the appropriate .po files are found"""
    actual = i18n.get_filename_for_locale('does_not_exist')
    assert actual is None

    actual = i18n.get_filename_for_locale('id_ID')
    assert os.path.basename(actual) == 'id_ID.po'

    actual = i18n.get_filename_for_locale('ja_JP')
    assert os.path.basename(actual) == 'ja.po'
