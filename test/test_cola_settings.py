import unittest
import os

from cola import settings
import helper

_tmp_path = helper.tmp_path('colarc')
settings.SettingsModel.path = lambda *args: _tmp_path

class SettingsTestCase(unittest.TestCase):
    """Tests the cola.settings module"""
    def tearDown(self):
        if os.path.exists(_tmp_path):
            os.remove(_tmp_path)

    def model(self):
        return settings.SettingsModel()

    def test_path(self):
        """Test the test path() helper above"""
        model = self.model()
        self.assertEqual(model.path(), helper.tmp_path('colarc'))

    def test_gui_save_restore(self):
        """Test saving and restoring gui state"""
        model = self.model()
        model.set_gui_state('test-gui', {'foo':'bar'})
        model.save()
        model = self.model()
        state = model.get_gui_state('test-gui')
        self.assertTrue('foo' in state)
        self.assertEqual(state['foo'], 'bar')

    def test_bookmarks_save_restore(self):
        """Test the bookmark save/restore feature"""
        model = self.model()
        model.add_bookmark('test-bookmark')
        model.save()
        model = self.model()
        bookmarks = model.get_bookmarks()
        self.assertEqual(len(bookmarks), 1)
        self.assertTrue('test-bookmark' in bookmarks)

        model.remove_bookmark('test-bookmark')
        bookmarks = model.get_bookmarks()
        self.assertEqual(len(bookmarks), 0)
        self.assertFalse('test-bookmark' in bookmarks)

if __name__ == '__main__':
    unittest.main()
