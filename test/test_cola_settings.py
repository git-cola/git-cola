import unittest
import os

from cola import settings
import helper

class SettingsTestCase(unittest.TestCase):
    """Tests the cola.settings module"""
    def setUp(self):
        settings.Settings._file = self._file = helper.tmp_path('settings')
        settings.Settings.load_dot_cola = lambda x, y: {}

    def tearDown(self):
        if os.path.exists(self._file):
            os.remove(self._file)

    def model(self):
        return settings.Settings()

    def test_gui_save_restore(self):
        """Test saving and restoring gui state"""
        model = self.model()
        model.gui_state['test-gui'] = {'foo':'bar'}
        model.save()

        model = self.model()
        state = model.gui_state.get('test-gui', {})
        self.assertTrue('foo' in state)
        self.assertEqual(state['foo'], 'bar')

    def test_bookmarks_save_restore(self):
        """Test the bookmark save/restore feature"""

        # We automatically purge missing entries so we mock-out
        # os.path.exists so that this bookmark is kept.

        bookmark = '/tmp/python/thinks/this/exists'
        os_path_exists = os.path.exists

        def mock_exists(path):
            return path == bookmark or os_path_exists(path)

        os.path.exists = mock_exists

        model = self.model()
        model.add_bookmark(bookmark)
        model.save()

        model = self.model()
        os.path.exists = os_path_exists # undo mock

        bookmarks = model.bookmarks
        self.assertEqual(len(model.bookmarks), 1)
        self.assertTrue(bookmark in bookmarks)

        model.remove_bookmark(bookmark)
        bookmarks = model.bookmarks
        self.assertEqual(len(bookmarks), 0)
        self.assertFalse(bookmark in bookmarks)

    def test_bookmarks_removes_missing_entries(self):
        """Test that missing entries are removed after a reload"""
        bookmark = '/tmp/this/does/not/exist'
        model = self.model()
        model.add_bookmark(bookmark)
        model.save()

        model = self.model()
        bookmarks = model.bookmarks
        self.assertEqual(len(model.bookmarks), 0)
        self.assertFalse(bookmark in bookmarks)



if __name__ == '__main__':
    unittest.main()
