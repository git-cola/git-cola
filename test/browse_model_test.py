"""Covers interfaces used by the classic view."""
from __future__ import unicode_literals

import os

import helper
from cola import gitcmds
from cola.models.main import MainModel


class ClassicModelTestCase(helper.GitRepositoryTestCase):
    """Tests interfaces used by the classic view."""

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self, commit=False)
        self.model = MainModel(cwd=os.getcwd())

    def test_everything(self):
        """Test the MainModel.everything() method."""
        self.shell('touch other-file')
        everything = self.model.everything()

        self.assertTrue('A' in everything)
        self.assertTrue('B' in everything)
        self.assertTrue('other-file' in everything)

    def test_stage_paths_untracked(self):
        """Test stage_paths() with an untracked file."""
        self.shell("""
            mkdir -p foo/bar &&
            touch foo/bar/baz
        """)
        self.model.stage_paths(['foo'])

        self.assertTrue('foo/bar/baz' in self.model.staged)
        self.assertTrue('foo/bar/baz' not in self.model.modified)
        self.assertTrue('foo/bar/baz' not in self.model.untracked)

    def test_unstage_paths(self):
        """Test a simple usage of unstage_paths()."""
        self.shell("""
            git commit -m'initial commit' > /dev/null
            echo change > A &&
            git add A
        """)
        gitcmds.unstage_paths(['A'])
        self.model.update_status()

        self.assertTrue('A' not in self.model.staged)
        self.assertTrue('A' in self.model.modified)

    def test_unstage_paths_init(self):
        """Test unstage_paths() on the root commit."""
        gitcmds.unstage_paths(['A'])
        self.model.update_status()

        self.assertTrue('A' not in self.model.staged)
        self.assertTrue('A' in self.model.untracked)

    def test_unstage_paths_subdir(self):
        """Test unstage_paths() in a subdirectory."""
        self.shell("git commit -m'initial commit' > /dev/null")
        self.shell("""
            mkdir -p foo/bar &&
            touch foo/bar/baz &&
            git add foo/bar/baz
        """)
        gitcmds.unstage_paths(['foo'])
        self.model.update_status()

        self.assertTrue('foo/bar/baz' in self.model.untracked)
        self.assertTrue('foo/bar/baz' not in self.model.staged)
