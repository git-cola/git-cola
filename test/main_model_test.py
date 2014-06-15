from __future__ import unicode_literals

import os
import unittest

import helper
from cola import core
from cola.models.main import MainModel


class MainModelTestCase(helper.GitRepositoryTestCase):
    """Tests the MainModel class."""

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)
        self.model = MainModel(cwd=core.getcwd())

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

        self.shell("""
                git remote add origin .
                git fetch origin > /dev/null 2>&1
        """)
        self.model.update_status()
        self.assertEqual(self.model.remote_branches, ['origin/master'])

    def test_modified(self):
        """Test the 'modified' attribute."""
        self.shell('echo change > A')
        self.model.update_status()
        self.assertEqual(self.model.modified, ['A'])

    def test_unstaged(self):
        """Test the 'unstaged' attribute."""
        self.shell('echo change > A')
        self.shell('echo C > C')
        self.model.update_status()
        self.assertEqual(self.model.unstaged, ['A', 'C'])

    def test_untracked(self):
        """Test the 'untracked' attribute."""
        self.shell('echo C > C')
        self.model.update_status()
        self.assertEqual(self.model.untracked, ['C'])

    def test_remotes(self):
        """Test the 'remote' attribute."""
        self.shell('git remote add origin .')
        self.model.update_status()
        self.assertEqual(self.model.remotes, ['origin'])

    def test_currentbranch(self):
        """Test the 'currentbranch' attribute."""
        self.shell('git checkout -b test > /dev/null 2>&1')
        self.model.update_status()
        self.assertEqual(self.model.currentbranch, 'test')

    def test_tags(self):
        """Test the 'tags' attribute."""
        self.shell('git tag test')
        self.model.update_status()
        self.assertEqual(self.model.tags, ['test'])


if __name__ == '__main__':
    unittest.main()
