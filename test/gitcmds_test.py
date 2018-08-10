from __future__ import absolute_import, division, unicode_literals
import os
import unittest

from cola import gitcmds

from . import helper


class GitCmdsTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.gitcmds module."""

    def test_currentbranch(self):
        """Test current_branch()."""
        self.assertEqual(gitcmds.current_branch(self.context), 'master')

    def test_branch_list_local(self):
        """Test branch_list(remote=False)."""
        context = self.context
        self.commit_files()
        expect = ['master']
        actual = gitcmds.branch_list(context, remote=False)
        self.assertEqual(expect, actual)

    def test_branch_list_remote(self):
        """Test branch_list(remote=False)."""
        context = self.context
        expect = []
        actual = gitcmds.branch_list(context, remote=True)
        self.assertEqual(expect, actual)

        self.commit_files()
        self.run_git('remote', 'add', 'origin', '.')
        self.run_git('fetch', 'origin')
        expect = ['origin/master']
        actual = gitcmds.branch_list(context, remote=True)
        self.assertEqual(expect, actual)

        self.run_git('remote', 'rm', 'origin')
        expect = []
        actual = gitcmds.branch_list(context, remote=True)
        self.assertEqual(expect, actual)

    def test_upstream_remote(self):
        """Test getting the configured upstream remote"""
        context = self.context
        self.assertEqual(gitcmds.upstream_remote(context), None)
        self.run_git('config', 'branch.master.remote', 'test')
        self.cfg.reset()
        self.assertEqual(gitcmds.upstream_remote(context), 'test')

    def test_tracked_branch(self):
        """Test tracked_branch()."""
        context = self.context
        self.assertEqual(gitcmds.tracked_branch(context), None)
        self.run_git('config', 'branch.master.remote', 'test')
        self.run_git('config', 'branch.master.merge', 'refs/heads/master')
        self.cfg.reset()
        self.assertEqual(gitcmds.tracked_branch(context), 'test/master')

    def test_tracked_branch_other(self):
        """Test tracked_branch('other')."""
        context = self.context
        self.assertEqual(gitcmds.tracked_branch(context, 'other'), None)
        self.run_git('config', 'branch.other.remote', 'test')
        self.run_git('config', 'branch.other.merge', 'refs/heads/other/branch')
        self.cfg.reset()
        self.assertEqual(gitcmds.tracked_branch(context, 'other'),
                         'test/other/branch')

    def test_untracked_files(self):
        """Test untracked_files()."""
        context = self.context
        self.touch('C', 'D', 'E')
        self.assertEqual(gitcmds.untracked_files(context), ['C', 'D', 'E'])

    def test_all_files(self):
        context = self.context
        self.touch('other-file')
        all_files = gitcmds.all_files(context)

        self.assertTrue('A' in all_files)
        self.assertTrue('B' in all_files)
        self.assertTrue('other-file' in all_files)

    def test_tag_list(self):
        """Test tag_list()."""
        context = self.context
        self.commit_files()
        self.run_git('tag', 'a')
        self.run_git('tag', 'b')
        self.run_git('tag', 'c')
        self.assertEqual(gitcmds.tag_list(context), ['c', 'b', 'a'])

    def test_merge_message_path(self):
        """Test merge_message_path()."""
        context = self.context
        self.touch('.git/SQUASH_MSG')
        self.assertEqual(gitcmds.merge_message_path(context),
                         os.path.abspath('.git/SQUASH_MSG'))
        self.touch('.git/MERGE_MSG')
        self.assertEqual(gitcmds.merge_message_path(context),
                         os.path.abspath('.git/MERGE_MSG'))
        os.unlink(gitcmds.merge_message_path(context))
        self.assertEqual(gitcmds.merge_message_path(context),
                         os.path.abspath('.git/SQUASH_MSG'))
        os.unlink(gitcmds.merge_message_path(context))
        self.assertEqual(gitcmds.merge_message_path(context), None)

    def test_all_refs(self):
        self.commit_files()
        self.run_git('branch', 'a')
        self.run_git('branch', 'b')
        self.run_git('branch', 'c')
        self.run_git('tag', 'd')
        self.run_git('tag', 'e')
        self.run_git('tag', 'f')
        self.run_git('remote', 'add', 'origin', '.')
        self.run_git('fetch', 'origin')
        refs = gitcmds.all_refs(self.context)
        self.assertEqual(refs,
                         ['a', 'b', 'c', 'master',
                          'origin/a', 'origin/b', 'origin/c', 'origin/master',
                          'f', 'e', 'd'])

    def test_all_refs_split(self):
        self.commit_files()
        self.run_git('branch', 'a')
        self.run_git('branch', 'b')
        self.run_git('branch', 'c')
        self.run_git('tag', 'd')
        self.run_git('tag', 'e')
        self.run_git('tag', 'f')
        self.run_git('remote', 'add', 'origin', '.')
        self.run_git('fetch', 'origin')
        local, remote, tags = gitcmds.all_refs(self.context, split=True)
        self.assertEqual(local, ['a', 'b', 'c', 'master'])
        self.assertEqual(remote,
                         ['origin/a', 'origin/b', 'origin/c', 'origin/master'])
        self.assertEqual(tags, ['f', 'e', 'd'])


if __name__ == '__main__':
    unittest.main()
