"""Tests for the i18n translation module"""
import os

import pytest

from cola import i18n
from cola.i18n import N_


@pytest.fixture(autouse=True)
def i18n_context():
    """Perform cleanup/teardown of the i18n module"""
    yield
    i18n.uninstall()


def test_translates_noun():
    """Test that strings with @@noun are translated"""
    i18n.install('ja_JP')
    expect = chr(0x30B3) + chr(0x30DF) + chr(0x30C3) + chr(0x30C8)
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


def test_translate_push_pull_french():
    i18n.install('fr_FR')
    expect = 'Tirer'
    actual = N_('Pull')
    assert expect == actual

    expect = 'Pousser'
    actual = N_('Push')
    assert expect == actual


def test_get_filename_for_locale():
    """Ensure that the appropriate .po files are found"""
    actual = i18n.get_filename_for_locale('does_not_exist')
    assert actual is None

    actual = i18n.get_filename_for_locale('id_ID')
    assert os.path.basename(actual) == 'id_ID.po'

    actual = i18n.get_filename_for_locale('ja_JP')
    assert os.path.basename(actual) == 'ja.po'
