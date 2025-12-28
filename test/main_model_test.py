import os

import pytest

from cola import core
from cola import git
from cola.models import main
from cola.models.main import FETCH, FETCH_HEAD, PULL, PUSH

from . import helper
from .helper import app_context
from .helper import Mock


# prevent unused imports lint errors.
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


def test_stageable(app_context):
    """Test the 'stageable' attribute."""
    assert not app_context.model.is_stageable()


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
    """FETCH swaps arguments vs. PUSH and PULL"""
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        FETCH,
        local_branch=LOCAL_BRANCH,
        remote_branch=REMOTE_BRANCH,
    )
    assert args == [REMOTE, 'remote:local']
    assert kwargs['verbose']
    assert 'tags' not in kwargs
    assert 'rebase' not in kwargs


def test_remote_args_fetch_head(mock_context):
    """Fetch handles the implicit FETCH_HEAD ref"""
    # When FETCH_HEAD is used then we should not specify a tracking branch target.
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        FETCH,
        local_branch=FETCH_HEAD,
        remote_branch=REMOTE_BRANCH,
    )
    assert args == [REMOTE, 'remote']


def test_remote_args_fetch_tags(mock_context):
    # Fetch tags
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        FETCH,
        tags=True,
        local_branch=LOCAL_BRANCH,
        remote_branch=REMOTE_BRANCH,
    )
    assert args == [REMOTE, 'remote:local']
    assert kwargs['verbose']
    assert kwargs['tags']
    assert 'rebase' not in kwargs


def test_remote_args_fetch_into_tracking_branch(mock_context):
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        FETCH,
        remote_branch=REMOTE_BRANCH,
    )
    assert args == [REMOTE, 'remote:refs/remotes/server/remote']


def test_remote_args_pull(mock_context):
    # Pull
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        PULL,
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
        PULL,
        rebase=True,
        local_branch='',
        remote_branch=REMOTE_BRANCH,
    )
    assert args == [REMOTE, 'remote']
    assert kwargs['verbose']
    assert kwargs['rebase']
    assert 'tags' not in kwargs


def test_remote_args_push(mock_context):
    """PUSH swaps local and remote branches"""
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        PUSH,
        local_branch=LOCAL_BRANCH,
        remote_branch=REMOTE_BRANCH,
    )
    assert args == [REMOTE, 'local:remote']
    assert kwargs['verbose']
    assert 'tags' not in kwargs
    assert 'rebase' not in kwargs


def test_remote_args_push_tags(mock_context):
    """Pushing tags uses --tags"""
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        PUSH,
        tags=True,
        local_branch=LOCAL_BRANCH,
        remote_branch=REMOTE_BRANCH,
    )
    assert args == [REMOTE, 'local:remote']
    assert kwargs['verbose']
    assert kwargs['tags']
    assert 'rebase' not in kwargs


def test_remote_args_push_same_remote_and_local(mock_context):
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        PUSH,
        tags=True,
        local_branch=LOCAL_BRANCH,
        remote_branch=LOCAL_BRANCH,
    )
    assert args == [REMOTE, 'local']
    assert kwargs['verbose']
    assert kwargs['tags']
    assert 'rebase' not in kwargs


def test_remote_args_push_set_upstream(mock_context):
    (args, kwargs) = main.remote_args(
        mock_context,
        REMOTE,
        PUSH,
        tags=True,
        local_branch=LOCAL_BRANCH,
        remote_branch=LOCAL_BRANCH,
        set_upstream=True,
    )
    assert args == [REMOTE, 'local']
    assert kwargs['verbose']
    assert kwargs['tags']
    assert kwargs['set_upstream']
    assert 'rebase' not in kwargs


def test_remote_args_rebase_only(mock_context):
    (_, kwargs) = main.remote_args(
        mock_context, REMOTE, PULL, rebase=True, ff_only=True
    )
    assert kwargs['rebase']
    assert 'ff_only' not in kwargs


def test_run_remote_action(mock_context):
    """Test running a remote action"""
    mock_context.cfg.get = Mock(return_value=True)
    (args, kwargs) = main.run_remote_action(
        mock_context,
        lambda *args, **kwargs: (args, kwargs),
        REMOTE,
        FETCH,
        local_branch=LOCAL_BRANCH,
        remote_branch=REMOTE_BRANCH,
    )
    assert args == (REMOTE, 'remote:local')
    assert kwargs['verbose']
    assert 'tags' not in kwargs
    assert 'rebase' not in kwargs
