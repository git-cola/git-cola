"""Covers interfaces used by the browser (git cola browse)"""
from __future__ import absolute_import, division, unicode_literals

from test import helper

from cola import core
from cola import gitcmds
from cola.models.main import MainModel


class ClassicModelTestCase(helper.GitRepositoryTestCase):
    """Tests interfaces used by the browser (git cola browse)"""

    def setUp(self, commit=False):
        helper.GitRepositoryTestCase.setUp(self, commit=commit)
        self.model = MainModel(self.context, cwd=core.getcwd())

    def test_stage_paths_untracked(self):
        """Test stage_paths() with an untracked file."""
        core.makedirs('foo/bar')
        self.touch('foo/bar/baz')
        gitcmds.add(self.context, ['foo'])
        self.model.update_file_status()

        self.assertTrue('foo/bar/baz' in self.model.staged)
        self.assertTrue('foo/bar/baz' not in self.model.modified)
        self.assertTrue('foo/bar/baz' not in self.model.untracked)

    def test_unstage_paths(self):
        """Test a simple usage of unstage_paths()."""
        self.commit_files()
        self.write_file('A', 'change')
        self.git('add', 'A')
        gitcmds.unstage_paths(self.context, ['A'])
        self.model.update_status()

        self.assertTrue('A' not in self.model.staged)
        self.assertTrue('A' in self.model.modified)

    def test_unstage_paths_init(self):
        """Test unstage_paths() on the root commit."""
        gitcmds.unstage_paths(self.context, ['A'])
        self.model.update_status()

        self.assertTrue('A' not in self.model.staged)
        self.assertTrue('A' in self.model.untracked)

    def test_unstage_paths_subdir(self):
        """Test unstage_paths() in a subdirectory."""
        self.git('commit', '-m', 'initial commit')
        core.makedirs('foo/bar')
        self.touch('foo/bar/baz')
        self.git('add', 'foo/bar/baz')
        gitcmds.unstage_paths(self.context, ['foo'])
        self.model.update_status()

        self.assertTrue('foo/bar/baz' in self.model.untracked)
        self.assertTrue('foo/bar/baz' not in self.model.staged)
