from __future__ import absolute_import, division, unicode_literals

import unittest
import os

from cola.settings import Settings

from test import helper


class SettingsTestCase(unittest.TestCase):
    """Tests the cola.settings module"""

    def setUp(self):
        Settings._file = self._file = helper.tmp_path('settings')
        self.settings = self.new_settings()

    def tearDown(self):
        if os.path.exists(self._file):
            os.remove(self._file)

    def new_settings(self, **kwargs):
        settings = Settings(**kwargs)
        settings.load()
        return settings

    def test_gui_save_restore(self):
        """Test saving and restoring gui state"""
        settings = self.new_settings()
        settings.gui_state['test-gui'] = {'foo': 'bar'}
        settings.save()

        settings = self.new_settings()
        state = settings.gui_state.get('test-gui', {})
        self.assertTrue('foo' in state)
        self.assertEqual(state['foo'], 'bar')

    def test_bookmarks_save_restore(self):
        """Test the bookmark save/restore feature"""

        # We automatically purge missing entries so we mock-out
        # git.is_git_worktree() so that this bookmark is kept.

        bookmark = { 'path': '/tmp/python/thinks/this/exists', 'name' : 'exists' }

        def mock_verify(path):
            return path == bookmark['path']

        settings = self.new_settings()
        settings.add_bookmark(bookmark['path'],bookmark['name'])
        settings.save()

        settings = self.new_settings(verify=mock_verify)

        bookmarks = settings.bookmarks
        self.assertEqual(len(settings.bookmarks), 1)
        self.assertTrue(bookmark in bookmarks)

        settings.remove_bookmark(bookmark['path'],bookmark['name'])
        bookmarks = settings.bookmarks
        self.assertEqual(len(bookmarks), 0)
        self.assertFalse(bookmark in bookmarks)

    def test_bookmarks_removes_missing_entries(self):
        """Test that missing entries are removed after a reload"""
        bookmark = { 'path': '/tmp/this/does/not/exist', 'name' : 'notexist' }
        settings = self.new_settings()
        settings.add_bookmark(bookmark['path'],bookmark['name'])
        settings.save()

        settings = self.new_settings()
        bookmarks = settings.bookmarks
        self.assertEqual(len(settings.bookmarks), 0)
        self.assertFalse(bookmark in bookmarks)


if __name__ == '__main__':
    unittest.main()
