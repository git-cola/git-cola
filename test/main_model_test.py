from __future__ import absolute_import, division, unicode_literals

import os
import unittest

import mock

from cola import core
from cola import git
from cola.models import main

from . import helper


class MainModelTestCase(helper.GitRepositoryTestCase):
    """Tests the MainModel class."""

    def test_project(self):
        """Test the 'project' attribute."""
        project = os.path.basename(self.test_path())
        self.model.set_worktree(core.getcwd())
        self.assertEqual(self.model.project, project)

    def test_local_branches(self):
        """Test the 'local_branches' attribute."""
        self.commit_files()
        self.model.update_status()
        self.assertEqual(self.model.local_branches, ['master'])

    def test_remote_branches(self):
        """Test the 'remote_branches' attribute."""
        self.model.update_status()
        self.assertEqual(self.model.remote_branches, [])

        self.commit_files()
        self.run_git('remote', 'add', 'origin', '.')
        self.run_git('fetch', 'origin')
        self.model.update_status()
        self.assertEqual(self.model.remote_branches, ['origin/master'])

    def test_modified(self):
        """Test the 'modified' attribute."""
        self.write_file('A', 'change')
        self.model.update_status()
        self.assertEqual(self.model.modified, ['A'])

    def test_unstaged(self):
        """Test the 'unstaged' attribute."""
        self.write_file('A', 'change')
        self.write_file('C', 'C')
        self.model.update_status()
        self.assertEqual(self.model.unstaged, ['A', 'C'])

    def test_untracked(self):
        """Test the 'untracked' attribute."""
        self.write_file('C', 'C')
        self.model.update_status()
        self.assertEqual(self.model.untracked, ['C'])

    def test_remotes(self):
        """Test the 'remote' attribute."""
        self.run_git('remote', 'add', 'origin', '.')
        self.model.update_status()
        self.assertEqual(self.model.remotes, ['origin'])

    def test_currentbranch(self):
        """Test the 'currentbranch' attribute."""
        self.run_git('checkout', '-b', 'test')
        self.model.update_status()
        self.assertEqual(self.model.currentbranch, 'test')

    def test_tags(self):
        """Test the 'tags' attribute."""
        self.commit_files()
        self.run_git('tag', 'test')
        self.model.update_status()
        self.assertEqual(self.model.tags, ['test'])


class RemoteArgsTestCase(unittest.TestCase):
    def setUp(self):
        self.context = context = mock.Mock()
        context.git = git.create()
        self.remote = 'server'
        self.local_branch = 'local'
        self.remote_branch = 'remote'

    def test_remote_args_fetch(self):
        # Fetch
        (args, kwargs) = main.remote_args(
            self.context,
            self.remote,
            local_branch=self.local_branch,
            remote_branch=self.remote_branch,
        )

        self.assertEqual(args, [self.remote, 'remote:local'])
        self.assertTrue(kwargs['verbose'])
        self.assertFalse('tags' in kwargs)
        self.assertFalse('rebase' in kwargs)

    def test_remote_args_fetch_tags(self):
        # Fetch tags
        (args, kwargs) = main.remote_args(
            self.context,
            self.remote,
            tags=True,
            local_branch=self.local_branch,
            remote_branch=self.remote_branch,
        )

        self.assertEqual(args, [self.remote, 'remote:local'])
        self.assertTrue(kwargs['verbose'])
        self.assertTrue(kwargs['tags'])
        self.assertFalse('rebase' in kwargs)

    def test_remote_args_pull(self):
        # Pull
        (args, kwargs) = main.remote_args(
            self.context,
            self.remote,
            pull=True,
            local_branch='',
            remote_branch=self.remote_branch,
        )

        self.assertEqual(args, [self.remote, 'remote'])
        self.assertTrue(kwargs['verbose'])
        self.assertFalse('rebase' in kwargs)
        self.assertFalse('tags' in kwargs)

    def test_remote_args_pull_rebase(self):
        # Rebasing pull
        (args, kwargs) = main.remote_args(
            self.context,
            self.remote,
            pull=True,
            rebase=True,
            local_branch='',
            remote_branch=self.remote_branch,
        )

        self.assertEqual(args, [self.remote, 'remote'])
        self.assertTrue(kwargs['verbose'])
        self.assertTrue(kwargs['rebase'])
        self.assertFalse('tags' in kwargs)

    def test_remote_args_push(self):
        # Push, swap local and remote
        (args, kwargs) = main.remote_args(
            self.context,
            self.remote,
            local_branch=self.remote_branch,
            remote_branch=self.local_branch,
        )

        self.assertEqual(args, [self.remote, 'local:remote'])
        self.assertTrue(kwargs['verbose'])
        self.assertFalse('tags' in kwargs)
        self.assertFalse('rebase' in kwargs)

    def test_remote_args_push_tags(self):
        # Push, swap local and remote
        (args, kwargs) = main.remote_args(
            self.context,
            self.remote,
            tags=True,
            local_branch=self.remote_branch,
            remote_branch=self.local_branch,
        )

        self.assertEqual(args, [self.remote, 'local:remote'])
        self.assertTrue(kwargs['verbose'])
        self.assertTrue(kwargs['tags'])
        self.assertFalse('rebase' in kwargs)

    def test_remote_args_push_same_remote_and_local(self):
        (args, kwargs) = main.remote_args(
            self.context,
            self.remote,
            tags=True,
            local_branch=self.local_branch,
            remote_branch=self.local_branch,
            push=True,
        )

        self.assertEqual(args, [self.remote, 'local'])
        self.assertTrue(kwargs['verbose'])
        self.assertTrue(kwargs['tags'])
        self.assertFalse('rebase' in kwargs)

    def test_remote_args_push_set_upstream(self):
        (args, kwargs) = main.remote_args(
            self.context,
            self.remote,
            tags=True,
            local_branch=self.local_branch,
            remote_branch=self.local_branch,
            push=True,
            set_upstream=True,
        )

        self.assertEqual(args, [self.remote, 'local'])
        self.assertTrue(kwargs['verbose'])
        self.assertTrue(kwargs['tags'])
        self.assertTrue(kwargs['set_upstream'])
        self.assertFalse('rebase' in kwargs)

    def test_remote_args_rebase_only(self):
        (_, kwargs) = main.remote_args(
            self.context, self.remote, pull=True, rebase=True, ff_only=True
        )
        self.assertTrue(kwargs['rebase'])
        self.assertFalse('ff_only' in kwargs)

    def test_run_remote_action(self):
        def passthrough(*args, **kwargs):
            return (args, kwargs)

        (args, kwargs) = main.run_remote_action(
            self.context,
            passthrough,
            self.remote,
            local_branch=self.local_branch,
            remote_branch=self.remote_branch,
        )

        self.assertEqual(args, (self.remote, 'remote:local'))
        self.assertTrue(kwargs['verbose'])
        self.assertFalse('tags' in kwargs)
        self.assertFalse('rebase' in kwargs)


if __name__ == '__main__':
    unittest.main()
