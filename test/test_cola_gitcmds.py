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

    def test_branch_list_remote(self):
        """Test branch_list(remote=False)."""
        self.assertEqual(gitcmds.branch_list(remote=True), [])
        self.shell("""
            git remote add origin .
            git fetch origin > /dev/null 2>&1
        """)
        self.assertEqual(gitcmds.branch_list(remote=True), ['origin/master'])
        self.shell('git remote rm origin')
        self.assertEqual(gitcmds.branch_list(remote=True), [])

    def test_default_remote(self):
        """Test default_remote()."""
        self.assertEqual(gitcmds.default_remote(), None)
        self.shell('git config branch.master.remote test')
        self.assertEqual(gitcmds.default_remote(), 'test')


if __name__ == '__main__':
    unittest.main()
