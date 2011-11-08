import unittest
import os

from cola import settings
import helper

class SettingsTestCase(unittest.TestCase):
    """Tests the cola.settings module"""
    def setUp(self):
        settings.Settings._file = self._file = helper.tmp_path('settings')
        settings.Settings.load_dot_cola = lambda x, y: None

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
        model = self.model()
        model.add_bookmark('test-bookmark')
        model.save()

        model = self.model()
        bookmarks = model.bookmarks
        self.assertEqual(len(model.bookmarks), 1)
        self.assertTrue('test-bookmark' in bookmarks)

        model.remove_bookmark('test-bookmark')
        bookmarks = model.bookmarks
        self.assertEqual(len(bookmarks), 0)
        self.assertFalse('test-bookmark' in bookmarks)


if __name__ == '__main__':
    unittest.main()
