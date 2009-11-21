import unittest

import helper
from cola import gitcfg


class GitConfigTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.gitcmds module."""
    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)
        self.config = gitcfg.instance()

    def test_string(self):
        """Test string values in get()."""
        self.shell('git config test.value test')
        self.assertEqual(self.config.get('test.value'), 'test')

    def test_int(self):
        """Test int values in get()."""
        self.shell('git config test.int 42')
        self.assertEqual(self.config.get('test.int'), 42)


if __name__ == '__main__':
    unittest.main()
