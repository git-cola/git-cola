import os

import pytest

from cola import core
from cola import git
from cola.models import main
from cola.models.main import FETCH
from cola.models.main import FETCH_HEAD
from cola.models.main import PULL
from cola.models.main import PUSH

from . import helper
from .helper import Mock
from .helper import app_context

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


def test_cola_msg_updated_when_not_manually_edited(app_context):
    """GIT_COLA_MSG is loaded into the commit message on refresh

    GIT_COLA_MSG update is applied when the user has not edited the message.
    """
    msg_path = app_context.git.git_path('GIT_COLA_MSG')
    helper.write_file(msg_path, 'first message\n')
    app_context.model._update_commitmsg()
    assert app_context.model.commitmsg == 'first message\n'
    helper.write_file(msg_path, 'updated message\n')
    os.utime(msg_path, (os.path.getmtime(msg_path) + 1,) * 2)  # ensure mtime differs on coarse-grained filesystems
    app_context.model._update_commitmsg()
    assert app_context.model.commitmsg == 'updated message\n'


def test_cola_msg_not_overwritten_when_user_edited(app_context):
    """User's manual edits are preserved when GIT_COLA_MSG is updated externally"""
    msg_path = app_context.git.git_path('GIT_COLA_MSG')
    helper.write_file(msg_path, 'first message\n')
    app_context.model._update_commitmsg()
    app_context.model.commitmsg = 'user message'
    helper.write_file(msg_path, 'second message\n')
    os.utime(msg_path, (os.path.getmtime(msg_path) + 1,) * 2)  # ensure mtime differs on coarse-grained filesystems
    app_context.model._update_commitmsg()
    assert app_context.model.commitmsg == 'user message'


def test_cola_msg_suppressed_during_merge(app_context):
    """GIT_COLA_MSG is not loaded while a merge message is active"""
    msg_path = app_context.git.git_path('GIT_COLA_MSG')
    merge_path = app_context.git.git_path('MERGE_MSG')
    helper.write_file(msg_path, 'agent message\n')
    helper.write_file(merge_path, 'merge commit message\n')
    app_context.model._update_commitmsg()
    assert app_context.model.commitmsg == 'merge commit message'
    os.unlink(merge_path)


def test_cola_msg_loaded_after_merge_clears(app_context):
    """GIT_COLA_MSG is loaded once the merge auto-message cycle completes

    Sequence:
      - merge sets auto-msg
      - merge file removed
      - _prev_commitmsg (empty) restored
      - next refresh loads GIT_COLA_MSG replacing empty commitmsg.
    """
    msg_path = app_context.git.git_path('GIT_COLA_MSG')
    merge_path = app_context.git.git_path('MERGE_MSG')
    helper.write_file(msg_path, 'agent message\n')
    helper.write_file(merge_path, 'merge commit message\n')
    # First refresh: merge msg is picked up, GIT_COLA_MSG ignored
    app_context.model._update_commitmsg()
    assert app_context.model.commitmsg == 'merge commit message'
    # Merge completes: MERGE_MSG file disappears
    os.unlink(merge_path)
    # Second refresh: clears _auto_commitmsg and restore _prev_commitmsg ('')
    app_context.model._update_commitmsg()
    # Third refresh: GIT_COLA_MSG is now loaded because commitmsg is empty
    app_context.model._update_commitmsg()
    assert app_context.model.commitmsg == 'agent message\n'


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
