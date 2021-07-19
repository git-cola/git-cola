"""Test the cola.gitcmds module"""
# pylint: disable=redefined-outer-name
from __future__ import absolute_import, division, print_function, unicode_literals
import os

from cola import gitcmds
from cola.widgets.remote import get_default_remote

from . import helper
from .helper import app_context


# These assertions make flake8 happy. It considers them unused imports otherwise.
assert app_context is not None


def test_currentbranch(app_context):
    """Test current_branch()."""
    assert gitcmds.current_branch(app_context) == 'main'


def test_branch_list_local(app_context):
    """Test branch_list(remote=False)."""
    helper.commit_files()
    expect = ['main']
    actual = gitcmds.branch_list(app_context, remote=False)
    assert expect == actual


def test_branch_list_remote(app_context):
    """Test branch_list(remote=False)."""
    expect = []
    actual = gitcmds.branch_list(app_context, remote=True)
    assert expect == actual

    helper.commit_files()
    helper.run_git('remote', 'add', 'origin', '.')
    helper.run_git('fetch', 'origin')

    expect = ['origin/main']
    actual = gitcmds.branch_list(app_context, remote=True)
    assert expect == actual

    helper.run_git('remote', 'rm', 'origin')
    expect = []
    actual = gitcmds.branch_list(app_context, remote=True)
    assert expect == actual


def test_upstream_remote(app_context):
    """Test getting the configured upstream remote"""
    assert gitcmds.upstream_remote(app_context) is None
    helper.run_git('config', 'branch.main.remote', 'test')
    app_context.cfg.reset()
    assert gitcmds.upstream_remote(app_context) == 'test'


def test_default_push(app_context):
    """Test getting what default branch to push to"""
    # no default push, no remote branch configured
    assert get_default_remote(app_context) == 'origin'

    # default push set, no remote branch configured
    helper.run_git('config', 'remote.pushDefault', 'test')
    app_context.cfg.reset()
    assert get_default_remote(app_context) == 'test'

    # default push set, default remote branch configured
    helper.run_git('config', 'branch.main.remote', 'test2')
    app_context.cfg.reset()
    assert get_default_remote(app_context) == 'test2'

    # default push set, default remote branch configured, on different branch
    helper.run_git('checkout', '-b', 'other-branch')
    assert get_default_remote(app_context) == 'test'


def test_tracked_branch(app_context):
    """Test tracked_branch()."""
    assert gitcmds.tracked_branch(app_context) is None
    helper.run_git('config', 'branch.main.remote', 'test')
    helper.run_git('config', 'branch.main.merge', 'refs/heads/main')
    app_context.cfg.reset()
    assert gitcmds.tracked_branch(app_context) == 'test/main'


def test_tracked_branch_other(app_context):
    """Test tracked_branch('other')"""
    assert gitcmds.tracked_branch(app_context, 'other') is None
    helper.run_git('config', 'branch.other.remote', 'test')
    helper.run_git('config', 'branch.other.merge', 'refs/heads/other/branch')
    app_context.cfg.reset()
    assert gitcmds.tracked_branch(app_context, 'other') == 'test/other/branch'


def test_untracked_files(app_context):
    """Test untracked_files()."""
    helper.touch('C', 'D', 'E')
    assert gitcmds.untracked_files(app_context) == ['C', 'D', 'E']


def test_all_files(app_context):
    helper.touch('other-file')
    all_files = gitcmds.all_files(app_context)

    assert 'A' in all_files
    assert 'B' in all_files
    assert 'other-file' in all_files


def test_tag_list(app_context):
    """Test tag_list()"""
    helper.commit_files()
    helper.run_git('tag', 'a')
    helper.run_git('tag', 'b')
    helper.run_git('tag', 'c')
    assert gitcmds.tag_list(app_context) == ['c', 'b', 'a']


def test_merge_message_path(app_context):
    """Test merge_message_path()."""
    helper.touch('.git/SQUASH_MSG')
    assert gitcmds.merge_message_path(app_context) == os.path.abspath('.git/SQUASH_MSG')
    helper.touch('.git/MERGE_MSG')
    assert gitcmds.merge_message_path(app_context) == os.path.abspath('.git/MERGE_MSG')
    os.unlink(gitcmds.merge_message_path(app_context))
    assert gitcmds.merge_message_path(app_context) == os.path.abspath('.git/SQUASH_MSG')
    os.unlink(gitcmds.merge_message_path(app_context))
    assert gitcmds.merge_message_path(app_context) is None


def test_all_refs(app_context):
    helper.commit_files()
    helper.run_git('branch', 'a')
    helper.run_git('branch', 'b')
    helper.run_git('branch', 'c')
    helper.run_git('tag', 'd')
    helper.run_git('tag', 'e')
    helper.run_git('tag', 'f')
    helper.run_git('remote', 'add', 'origin', '.')
    helper.run_git('fetch', 'origin')

    refs = gitcmds.all_refs(app_context)

    assert refs == [
        'a',
        'b',
        'c',
        'main',
        'origin/a',
        'origin/b',
        'origin/c',
        'origin/main',
        'f',
        'e',
        'd',
    ]


def test_all_refs_split(app_context):
    helper.commit_files()
    helper.run_git('branch', 'a')
    helper.run_git('branch', 'b')
    helper.run_git('branch', 'c')
    helper.run_git('tag', 'd')
    helper.run_git('tag', 'e')
    helper.run_git('tag', 'f')
    helper.run_git('remote', 'add', 'origin', '.')
    helper.run_git('fetch', 'origin')

    local, remote, tags = gitcmds.all_refs(app_context, split=True)

    assert local == ['a', 'b', 'c', 'main']
    assert remote == ['origin/a', 'origin/b', 'origin/c', 'origin/main']
    assert tags == ['f', 'e', 'd']


def test_binary_files(app_context):
    # Create a binary file and ensure that it's detected as binary.
    with open('binary-file.txt', 'wb') as f:
        f.write(b'hello\0world\n')
    assert gitcmds.is_binary(app_context, 'binary-file.txt')

    # Create a text file and ensure that it's not detected as binary.
    with open('text-file.txt', 'w') as f:
        f.write('hello world\n')
    assert not gitcmds.is_binary(app_context, 'text-file.txt')

    # Create a .gitattributes file and mark text-file.txt as binary.
    app_context.cfg.reset()
    with open('.gitattributes', 'w') as f:
        f.write('text-file.txt binary\n')
    assert gitcmds.is_binary(app_context, 'text-file.txt')

    # Remove the "binary" attribute using "-binary" from binary-file.txt.
    # Ensure that we do not flag this file as binary.
    with open('.gitattributes', 'w') as f:
        f.write('binary-file.txt -binary\n')
    assert not gitcmds.is_binary(app_context, 'binary-file.txt')


def test_is_valid_ref(app_context):
    """Verify the behavior of is_valid_ref()"""
    # We are initially in a "git init" state. HEAD must be invalid.
    assert not gitcmds.is_valid_ref(app_context, 'HEAD')
    # Create the first commit onto the "test" branch.
    app_context.git.symbolic_ref('HEAD', 'refs/heads/test')
    app_context.git.commit(m='initial commit')
    assert gitcmds.is_valid_ref(app_context, 'HEAD')
    assert gitcmds.is_valid_ref(app_context, 'test')
    assert gitcmds.is_valid_ref(app_context, 'refs/heads/test')


def test_diff_helper(app_context):
    helper.commit_files()
    with open('A', 'w') as f:
        f.write('A change\n')
    helper.run_git('add', 'A')

    expect = '+A change\n'
    actual = gitcmds.diff_helper(app_context, ref='HEAD', cached=True)
    assert expect in actual
