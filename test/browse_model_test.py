"""Test interfaces used by the browser (git cola browse)"""
# pylint: disable=redefined-outer-name
from __future__ import absolute_import, division, print_function, unicode_literals

from cola import core
from cola import gitcmds

from . import helper
from .helper import app_context


# These assertions make flake8 happy. It considers them unused imports otherwise.
assert app_context is not None


def test_stage_paths_untracked(app_context):
    """Test stage_paths() with an untracked file."""
    model = app_context.model
    core.makedirs('foo/bar')
    helper.touch('foo/bar/baz')
    gitcmds.add(app_context, ['foo'])
    app_context.model.update_file_status()

    assert 'foo/bar/baz' in model.staged
    assert 'foo/bar/baz' not in model.modified
    assert 'foo/bar/baz' not in model.untracked


def test_unstage_paths(app_context):
    """Test a simple usage of unstage_paths()."""
    helper.commit_files()
    helper.write_file('A', 'change')
    helper.run_git('add', 'A')
    model = app_context.model

    gitcmds.unstage_paths(app_context, ['A'])
    model.update_status()

    assert 'A' not in model.staged
    assert 'A' in model.modified


def test_unstage_paths_init(app_context):
    """Test unstage_paths() on the root commit."""
    model = app_context.model
    gitcmds.unstage_paths(app_context, ['A'])
    model.update_status()

    assert 'A' not in model.staged
    assert 'A' in model.untracked


def test_unstage_paths_subdir(app_context):
    """Test unstage_paths() in a subdirectory."""
    helper.run_git('commit', '-m', 'initial commit')
    core.makedirs('foo/bar')
    helper.touch('foo/bar/baz')
    helper.run_git('add', 'foo/bar/baz')
    model = app_context.model

    gitcmds.unstage_paths(app_context, ['foo'])
    model.update_status()

    assert 'foo/bar/baz' in model.untracked
    assert 'foo/bar/baz' not in model.staged
