import unittest
import os

from cola import serializer
from cola import settings
import helper

class SettingsTestCase(unittest.TestCase):
    """Tests the cola.settings module"""
    def setUp(self):
        self._old_rcfile = settings._rcfile
        self._rcfile = helper.tmp_path('colarc')
        settings._rcfile = self._rcfile

    def tearDown(self):
        if os.path.exists(self._rcfile):
            os.remove(self._rcfile)
        settings._rcfile = self._old_rcfile

    def model(self):
        settings.SettingsManager._settings = None
        return settings.SettingsManager.settings()

    def test_model_helper(self):
        a = self.model()
        b = self.model()
        self.assertTrue(a is not b)

    def test_gui_save_restore(self):
        """Test saving and restoring gui state"""
        model = self.model()
        model.gui_state['test-gui'] = {'foo':'bar'}
        settings.SettingsManager.save()

        model = self.model()
        state = model.gui_state.get('test-gui', {})
        self.assertTrue('foo' in state)
        self.assertEqual(state['foo'], 'bar')

    def test_bookmarks_save_restore(self):
        """Test the bookmark save/restore feature"""
        model = self.model()
        model.add_bookmark('test-bookmark')
        settings.SettingsManager.save()
        model = self.model()
        bookmarks = model.bookmarks
        self.assertEqual(len(bookmarks), 1)
        self.assertTrue('test-bookmark' in bookmarks)

        model.remove_bookmark('test-bookmark')
        bookmarks = model.bookmarks
        self.assertEqual(len(bookmarks), 0)
        self.assertFalse('test-bookmark' in bookmarks)

if __name__ == '__main__':
    unittest.main()
