# pylint: disable=redefined-outer-name
from cola.models.stash import StashModel

from . import helper
from .helper import app_context


# These assertions make flake8 happy. It considers them unused imports otherwise.
assert app_context is not None


def test_stash_info_for_message_without_slash(app_context):
    helper.commit_files()
    helper.write_file('A', 'change')
    helper.run_git('stash', 'save', 'some message')
    assert StashModel(app_context).stash_info()[0] \
        == [r'stash@{0}: On main: some message']


def test_stash_info_for_message_with_slash(app_context):
    helper.commit_files()
    helper.write_file('A', 'change')
    helper.run_git('stash', 'save', 'some message/something')
    assert StashModel(app_context).stash_info()[0] \
        == [r'stash@{0}: On main: some message/something']


def test_stash_info_on_branch_with_slash(app_context):
    helper.commit_files()
    helper.run_git('checkout', '-b', 'feature/a')
    helper.write_file('A', 'change')
    helper.run_git('stash', 'save', 'some message')
    assert StashModel(app_context).stash_info()[0] \
        == [r'stash@{0}: On feature/a: some message']
