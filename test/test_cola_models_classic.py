"""Covers interfaces used by the classic view."""
import os

import helper
from cola import gitcmds
from cola.models.main import MainModel


class ClassicModelTestCase(helper.TestCase):
    """Tests interfaces used by the classic view."""

    def setup_baseline_repo(self, commit=True):
        """Create a baseline repo for testing."""
        self.shell("""
            git init >/dev/null &&
            touch the-file &&
            git add the-file
        """)
        if commit:
            self.shell("git commit -s -m'Initial commit' >/dev/null")

    def test_everything(self):
        """Test the MainModel.everything() method."""
        self.setup_baseline_repo()
        self.shell('touch other-file')

        model = MainModel(cwd=os.getcwd())
        model.update_status()

        everything = model.everything()
        self.assertTrue('the-file' in everything)
        self.assertTrue('other-file' in everything)

    def test_stage_paths_untracked(self):
        """Test stage_paths() with an untracked file."""
        self.setup_baseline_repo()
        self.shell("""
            mkdir -p foo/bar &&
            touch foo/bar/baz
        """)
        model = MainModel(cwd=os.getcwd())
        model.stage_paths(['foo'])

        self.assertTrue('foo/bar/baz' in model.staged)
        self.assertTrue('foo/bar/baz' not in model.modified)
        self.assertTrue('foo/bar/baz' not in model.untracked)

    def test_unstage_paths(self):
        """Test a simple usage of unstage_paths()."""
        self.setup_baseline_repo()
        self.shell("""
            echo change > the-file &&
            git add the-file
        """)

        model = MainModel(cwd=os.getcwd())
        gitcmds.unstage_paths(['the-file'])
        model.update_status()

        self.assertTrue('the-file' not in model.staged)
        self.assertTrue('the-file' in model.modified)

    def test_unstage_paths_init(self):
        """Test unstage_paths() on the root commit."""
        self.setup_baseline_repo(commit=False)

        model = MainModel(cwd=os.getcwd())
        gitcmds.unstage_paths(['the-file'])
        model.update_status()

        self.assertTrue('the-file' not in model.staged)
        self.assertTrue('the-file' in model.untracked)

    def test_unstage_paths_subdir(self):
        """Test unstage_paths() in a subdirectory."""
        self.setup_baseline_repo()
        self.shell("""
            mkdir -p foo/bar &&
            touch foo/bar/baz &&
            git add foo/bar/baz
        """)
        model = MainModel(cwd=os.getcwd())
        gitcmds.unstage_paths(['foo'])
        model.update_status()

        self.assertTrue('foo/bar/baz' in model.untracked)
        self.assertTrue('foo/bar/baz' not in model.staged)
