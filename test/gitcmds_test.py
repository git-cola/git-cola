from __future__ import absolute_import, division, unicode_literals

import os
import unittest

from cola import gitcmds
from cola import gitcfg

from test import helper


class GitCmdsTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.gitcmds module."""
    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)
        self.config = gitcfg.GitConfig()

    def test_currentbranch(self):
        """Test current_branch()."""
        self.assertEqual(gitcmds.current_branch(), 'master')

    def test_branch_list_local(self):
        """Test branch_list(remote=False)."""
        self.assertEqual(gitcmds.branch_list(remote=False), ['master'])

    def test_branch_list_remote(self):
        """Test branch_list(remote=False)."""
        self.assertEqual(gitcmds.branch_list(remote=True), [])
        self.git('remote', 'add', 'origin', '.')
        self.git('fetch', 'origin')
        self.assertEqual(gitcmds.branch_list(remote=True), ['origin/master'])
        self.git('remote', 'rm', 'origin')
        self.assertEqual(gitcmds.branch_list(remote=True), [])

    def test_default_remote(self):
        """Test default_remote()."""
        self.assertEqual(gitcmds.default_remote(config=self.config), None)
        self.git('config', 'branch.master.remote', 'test')
        self.config.reset()
        self.assertEqual(gitcmds.default_remote(config=self.config), 'test')

    def test_tracked_branch(self):
        """Test tracked_branch()."""
        self.assertEqual(gitcmds.tracked_branch(config=self.config), None)
        self.git('config', 'branch.master.remote', 'test')
        self.git('config', 'branch.master.merge', 'refs/heads/master')
        self.config.reset()
        self.assertEqual(gitcmds.tracked_branch(config=self.config),
                         'test/master')

    def test_tracked_branch_other(self):
        """Test tracked_branch('other')."""
        self.assertEqual(gitcmds.tracked_branch('other', config=self.config),
                         None)
        self.git('config', 'branch.other.remote', 'test')
        self.git('config', 'branch.other.merge', 'refs/heads/other/branch')
        self.config.reset()
        self.assertEqual(gitcmds.tracked_branch('other', config=self.config),
                         'test/other/branch')

    def test_untracked_files(self):
        """Test untracked_files()."""
        self.touch('C', 'D', 'E')
        self.assertEqual(gitcmds.untracked_files(), ['C', 'D', 'E'])

    def test_all_files(self):
        self.touch('other-file')
        all_files = gitcmds.all_files()

        self.assertTrue('A' in all_files)
        self.assertTrue('B' in all_files)
        self.assertTrue('other-file' in all_files)

    def test_tag_list(self):
        """Test tag_list()."""
        self.git('tag', 'a')
        self.git('tag', 'b')
        self.git('tag', 'c')
        self.assertEqual(gitcmds.tag_list(), ['c', 'b', 'a'])

    def test_merge_message_path(self):
        """Test merge_message_path()."""
        self.touch('.git/SQUASH_MSG')
        self.assertEqual(gitcmds.merge_message_path(),
                         os.path.abspath('.git/SQUASH_MSG'))
        self.touch('.git/MERGE_MSG')
        self.assertEqual(gitcmds.merge_message_path(),
                         os.path.abspath('.git/MERGE_MSG'))
        os.unlink(gitcmds.merge_message_path())
        self.assertEqual(gitcmds.merge_message_path(),
                         os.path.abspath('.git/SQUASH_MSG'))
        os.unlink(gitcmds.merge_message_path())
        self.assertEqual(gitcmds.merge_message_path(), None)

    def test_all_refs(self):
        self.git('branch', 'a')
        self.git('branch', 'b')
        self.git('branch', 'c')
        self.git('tag', 'd')
        self.git('tag', 'e')
        self.git('tag', 'f')
        self.git('remote', 'add', 'origin', '.')
        self.git('fetch', 'origin')
        refs = gitcmds.all_refs()
        self.assertEqual(refs,
                         ['a', 'b', 'c', 'master',
                          'origin/a', 'origin/b', 'origin/c', 'origin/master',
                          'd', 'e', 'f'])

    def test_all_refs_split(self):
        self.git('branch', 'a')
        self.git('branch', 'b')
        self.git('branch', 'c')
        self.git('tag', 'd')
        self.git('tag', 'e')
        self.git('tag', 'f')
        self.git('remote', 'add', 'origin', '.')
        self.git('fetch', 'origin')
        local, remote, tags = gitcmds.all_refs(split=True)
        self.assertEqual(local, ['a', 'b', 'c', 'master'])
        self.assertEqual(remote, ['origin/a', 'origin/b', 'origin/c', 'origin/master'])
        self.assertEqual(tags, ['d', 'e', 'f'])


if __name__ == '__main__':
    unittest.main()
