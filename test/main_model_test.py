# pylint: disable=redefined-outer-name
from __future__ import absolute_import, division, print_function, unicode_literals
import os

import pytest

from cola import core
from cola import git
from cola.models import main

from . import helper
from .helper import app_context
from .helper import Mock


# These assertions make flake8 happy. It considers them unused imports otherwise.
assert app_context is not None

REMOTE = 'server'
LOCAL_BRANCH = 'local'
REMOTE_BRANCH = 'remote'


@pytest.fixture
def mock_context():
    """Return a Mock context for testing"""
    context = Mock()
    context.git = git.create()
    return context


def test_project(app_context):
    """Test the 'project' attribute."""
    project = os.path.basename(core.getcwd())
    app_context.model.set_worktree(core.getcwd())
    assert app_context.model.project == project


def test_local_branches(app_context):
    """Test the 'local_branches' attribute."""
    helper.commit_files()
    app_context.model.update_status()
    assert app_context.model.local_branches == ['main']


def test_remote_branches(app_context):
    """Test the 'remote_branches' attribute."""
    app_context.model.update_status()
    assert app_context.model.remote_branches == []

    helper.commit_files()
    helper.run_git('remote', 'add', 'origin', '.')
    helper.run_git('fetch', 'origin')
    app_context.model.update_status()
    assert app_context.model.remote_branches == ['origin/main']


def test_modified(app_context):
    """Test the 'modified' attribute."""
    helper.write_file('A', 'change')
    app_context.model.update_status()
    assert app_context.model.modified == ['A']


def test_unstaged(app_context):
    """Test the 'unstaged' attribute."""
    helper.write_file('A', 'change')
    helper.write_file('C', 'C')
    app_context.model.update_status()
    assert app_context.model.unstaged == ['A', 'C']


def test_untracked(app_context):
    """Test the 'untracked' attribute."""
    helper.write_file('C', 'C')
    app_context.model.update_status()
    assert app_context.model.untracked == ['C']


def test_remotes(app_context):
    """Test the 'remote' attribute."""
    helper.run_git('remote', 'add', 'origin', '.')
    app_context.model.update_status()
    assert app_context.model.remotes == ['origin']


def test_currentbranch(app_context):
    """Test the 'currentbranch' attribute."""
    helper.run_git('checkout', '-b', 'test')
    app_context.model.update_status()
    assert app_context.model.currentbranch == 'test'


def test_tags(app_context):
    """Test the 'tags' attribute."""
    helper.commit_files()
    helper.run_git('tag', 'test')
    app_context.model.update_status()
    assert app_context.model.tags == ['test']


def test_remote_args_fetch(mock_context):
    # Fetch
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        local_branch=LOCAL_BRANCH,
        remote_branch=REMOTE_BRANCH,
    )

    assert args == [REMOTE, 'remote:local']
    assert kwargs['verbose']
    assert 'tags' not in kwargs
    assert 'rebase' not in kwargs


def test_remote_args_fetch_tags(mock_context):
    # Fetch tags
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        tags=True,
        local_branch=LOCAL_BRANCH,
        remote_branch=REMOTE_BRANCH,
    )

    assert args == [REMOTE, 'remote:local']
    assert kwargs['verbose']
    assert kwargs['tags']
    assert 'rebase' not in kwargs


def test_remote_args_pull(mock_context):
    # Pull
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        pull=True,
        local_branch='',
        remote_branch=REMOTE_BRANCH,
    )

    assert args == [REMOTE, 'remote']
    assert kwargs['verbose']
    assert 'rebase' not in kwargs
    assert 'tags' not in kwargs


def test_remote_args_pull_rebase(mock_context):
    # Rebasing pull
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        pull=True,
        rebase=True,
        local_branch='',
        remote_branch=REMOTE_BRANCH,
    )

    assert args == [REMOTE, 'remote']
    assert kwargs['verbose']
    assert kwargs['rebase']
    assert 'tags' not in kwargs


def test_remote_args_push(mock_context):
    # Push, swap local and remote
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        local_branch=REMOTE_BRANCH,
        remote_branch=LOCAL_BRANCH,
    )

    assert args == [REMOTE, 'local:remote']
    assert kwargs['verbose']
    assert 'tags' not in kwargs
    assert 'rebase' not in kwargs


def test_remote_args_push_tags(mock_context):
    # Push, swap local and remote
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        tags=True,
        local_branch=REMOTE_BRANCH,
        remote_branch=LOCAL_BRANCH,
    )

    assert args == [REMOTE, 'local:remote']
    assert kwargs['verbose']
    assert kwargs['tags']
    assert 'rebase' not in kwargs


def test_remote_args_push_same_remote_and_local(mock_context):
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        tags=True,
        local_branch=LOCAL_BRANCH,
        remote_branch=LOCAL_BRANCH,
        push=True,
    )

    assert args == [REMOTE, 'local']
    assert kwargs['verbose']
    assert kwargs['tags']
    assert 'rebase' not in kwargs


def test_remote_args_push_set_upstream(mock_context):
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        tags=True,
        local_branch=LOCAL_BRANCH,
        remote_branch=LOCAL_BRANCH,
        push=True,
        set_upstream=True,
    )

    assert args == [REMOTE, 'local']
    assert kwargs['verbose']
    assert kwargs['tags']
    assert kwargs['set_upstream']
    assert 'rebase' not in kwargs


def test_remote_args_rebase_only(mock_context):
    (_, kwargs) = main.remote_args(
        mock_context, REMOTE, pull=True, rebase=True, ff_only=True
    )
    assert kwargs['rebase']
    assert 'ff_only' not in kwargs


def test_run_remote_action(mock_context):

    def passthrough(*args, **kwargs):
        return (args, kwargs)

    (args, kwargs) = main.run_remote_action(
        mock_context,
        passthrough,
        REMOTE,
        local_branch=LOCAL_BRANCH,
        remote_branch=REMOTE_BRANCH,
    )

    assert args == (REMOTE, 'remote:local')
    assert kwargs['verbose']
    assert 'tags' not in kwargs
    assert 'rebase' not in kwargs
