from __future__ import absolute_import, division, unicode_literals

import os
import unittest

from cola import core
from cola.models import main

from test import helper


class MainModelTestCase(helper.GitRepositoryTestCase):
    """Tests the MainModel class."""

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)
        self.model = main.MainModel(cwd=core.getcwd())

    def test_project(self):
        """Test the 'project' attribute."""
        project = os.path.basename(self.test_path())
        self.assertEqual(self.model.project, project)

    def test_local_branches(self):
        """Test the 'local_branches' attribute."""
        self.model.update_status()
        self.assertEqual(self.model.local_branches, ['master'])

    def test_remote_branches(self):
        """Test the 'remote_branches' attribute."""
        self.model.update_status()
        self.assertEqual(self.model.remote_branches, [])

        self.git('remote', 'add', 'origin', '.')
        self.git('fetch', 'origin')
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
        self.git('remote', 'add', 'origin', '.')
        self.model.update_status()
        self.assertEqual(self.model.remotes, ['origin'])

    def test_currentbranch(self):
        """Test the 'currentbranch' attribute."""
        self.git('checkout', '-b', 'test')
        self.model.update_status()
        self.assertEqual(self.model.currentbranch, 'test')

    def test_tags(self):
        """Test the 'tags' attribute."""
        self.git('tag', 'test')
        self.model.update_status()
        self.assertEqual(self.model.tags, ['test'])


class RemoteArgsTestCase(unittest.TestCase):

    def setUp(self):
        self.remote = 'server'
        self.local_branch = 'local'
        self.remote_branch = 'remote'

    def test_remote_args_fetch(self):
        # Fetch
        (args, kwargs) = \
            main.remote_args(self.remote,
                             local_branch=self.local_branch,
                             remote_branch=self.remote_branch)

        self.assertEqual(args, [self.remote, 'remote:local'])
        self.assertTrue(kwargs['verbose'])
        self.assertFalse(kwargs['tags'])
        self.assertFalse(kwargs['rebase'])

    def test_remote_args_fetch_tags(self):
        # Fetch tags
        (args, kwargs) = \
            main.remote_args(self.remote,
                             tags=True,
                             local_branch=self.local_branch,
                             remote_branch=self.remote_branch)

        self.assertEqual(args, [self.remote, 'remote:local'])
        self.assertTrue(kwargs['verbose'])
        self.assertTrue(kwargs['tags'])
        self.assertFalse(kwargs['rebase'])

    def test_remote_args_pull(self):
        # Pull
        (args, kwargs) = \
            main.remote_args(self.remote,
                             pull=True,
                             local_branch='',
                             remote_branch=self.remote_branch)

        self.assertEqual(args, [self.remote, 'remote'])
        self.assertTrue(kwargs['verbose'])
        self.assertFalse(kwargs['rebase'])
        self.assertFalse(kwargs['tags'])

    def test_remote_args_pull_rebase(self):
        # Rebasing pull
        (args, kwargs) = \
            main.remote_args(self.remote,
                             pull=True,
                             rebase=True,
                             local_branch='',
                             remote_branch=self.remote_branch)

        self.assertEqual(args, [self.remote, 'remote'])
        self.assertTrue(kwargs['verbose'])
        self.assertTrue(kwargs['rebase'])
        self.assertFalse(kwargs['tags'])

    def test_remote_args_push(self):
        # Push, swap local and remote
        (args, kwargs) = \
            main.remote_args(self.remote,
                             local_branch=self.remote_branch,
                             remote_branch=self.local_branch)

        self.assertEqual(args, [self.remote, 'local:remote'])
        self.assertTrue(kwargs['verbose'])
        self.assertFalse(kwargs['tags'])
        self.assertFalse(kwargs['rebase'])

    def test_remote_args_push_tags(self):
        # Push, swap local and remote
        (args, kwargs) = \
            main.remote_args(self.remote,
                             tags=True,
                             local_branch=self.remote_branch,
                             remote_branch=self.local_branch)

        self.assertEqual(args, [self.remote, 'local:remote'])
        self.assertTrue(kwargs['verbose'])
        self.assertTrue(kwargs['tags'])
        self.assertFalse(kwargs['rebase'])

    def test_run_remote_action(self):

        def passthrough(*args, **kwargs):
            return (args, kwargs)

        (args, kwargs) = \
            main.run_remote_action(passthrough,
                                   self.remote,
                                   local_branch=self.local_branch,
                                   remote_branch=self.remote_branch)

        self.assertEqual(args, (self.remote, 'remote:local'))
        self.assertTrue(kwargs['verbose'])
        self.assertFalse(kwargs['tags'])
        self.assertFalse(kwargs['rebase'])


if __name__ == '__main__':
    unittest.main()
