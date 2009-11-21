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

    def test_tracked_branch(self):
        """Test tracked_branch()."""
        self.assertEqual(gitcmds.tracked_branch(), None)
        self.shell("""
            git config branch.master.remote test
            git config branch.master.merge refs/heads/master
        """)
        self.assertEqual(gitcmds.tracked_branch(), 'test/master')

    def test_tracked_branch_other(self):
        """Test tracked_branch('other')."""
        self.assertEqual(gitcmds.tracked_branch('other'), None)
        self.shell("""
            git config branch.other.remote test
            git config branch.other.merge refs/heads/other/branch
        """)
        self.assertEqual(gitcmds.tracked_branch('other'), 'test/other/branch')

    def test_untracked_files(self):
        """Test untracked_files()."""
        self.shell('touch C D E')
        self.assertEqual(gitcmds.untracked_files(), ['C', 'D', 'E'])


if __name__ == '__main__':
    unittest.main()
