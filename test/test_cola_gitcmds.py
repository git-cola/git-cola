import unittest

import helper
from cola import gitcmds


class GitCmdsTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.gitcmds module."""
    def test_currentbranch(self):
        """Test current_branch()."""
        self.assertEqual(gitcmds.current_branch(), 'master')

    def test_branch_list_local(self):
        """Test branch_list(remote=False)."""
        self.assertEqual(gitcmds.branch_list(remote=False), ['master'])


if __name__ == '__main__':
    unittest.main()
