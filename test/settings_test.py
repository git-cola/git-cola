"""Test the cola.settings module"""
# pylint: disable=redefined-outer-name
from __future__ import absolute_import, division, print_function, unicode_literals
import os

import pytest

from cola.settings import Settings

from . import helper


@pytest.fixture(autouse=True)
def settings_fixture():
    """Provide Settings that save into a temporary location to all tests"""
    filename = helper.tmp_path('settings')
    Settings.config_path = filename

    yield Settings.read()

    if os.path.exists(filename):
        os.remove(filename)


def test_gui_save_restore(settings_fixture):
    """Test saving and restoring gui state"""
    settings = settings_fixture
    settings.gui_state['test-gui'] = {'foo': 'bar'}
    settings.save()

    settings = Settings.read()
    state = settings.gui_state.get('test-gui', {})
    assert 'foo' in state
    assert state['foo'] == 'bar'


def test_bookmarks_save_restore():
    """Test the bookmark save/restore feature"""
    # We automatically purge missing entries so we mock-out
    # git.is_git_worktree() so that this bookmark is kept.
    bookmark = {'path': '/tmp/python/thinks/this/exists', 'name': 'exists'}

    def mock_verify(path):
        return path == bookmark['path']

    settings = Settings.read()
    settings.add_bookmark(bookmark['path'], bookmark['name'])
    settings.save()

    settings = Settings.read(verify=mock_verify)

    bookmarks = settings.bookmarks
    assert len(settings.bookmarks) == 1
    assert bookmark in bookmarks

    settings.remove_bookmark(bookmark['path'], bookmark['name'])
    bookmarks = settings.bookmarks
    expect = 0
    actual = len(bookmarks)
    assert expect == actual
    assert bookmark not in bookmarks


def test_bookmarks_removes_missing_entries():
    """Test that missing entries are removed after a reload"""
    # verify returns False so all entries will be removed.
    bookmark = {'path': '.', 'name': 'does-not-exist'}
    settings = Settings.read(verify=lambda x: False)
    settings.add_bookmark(bookmark['path'], bookmark['name'])
    settings.remove_missing_bookmarks()
    settings.save()

    settings = Settings.read()
    bookmarks = settings.bookmarks
    expect = 0
    actual = len(bookmarks)
    assert expect == actual
    assert bookmark not in bookmarks


def test_rename_bookmark():
    settings = Settings.read()
    settings.add_bookmark('/tmp/repo', 'a')
    settings.add_bookmark('/tmp/repo', 'b')
    settings.add_bookmark('/tmp/repo', 'c')

    settings.rename_bookmark('/tmp/repo', 'b', 'test')

    expect = ['a', 'test', 'c']
    actual = [i['name'] for i in settings.bookmarks]
    assert expect == actual
