from cola.models.stash import StashModel

from . import helper
from .helper import app_context


# Prevent unused imports lint errors.
assert app_context is not None


def test_stash_info_for_message_without_slash(app_context):
    helper.commit_files()
    helper.write_file('A', 'change')
    helper.run_git('stash', 'save', 'some message')
    assert StashModel(app_context).stash_info()[0] == [
        r'stash@{0}: On main: some message'
    ]


def test_stash_info_for_message_with_slash(app_context):
    helper.commit_files()
    helper.write_file('A', 'change')
    helper.run_git('stash', 'save', 'some message/something')
    model = StashModel(app_context)
    stash_details = model.stash_info()[0]
    assert stash_details == [r'stash@{0}: On main: some message/something']


def test_stash_info_on_branch_with_slash(app_context):
    helper.commit_files()
    helper.run_git('checkout', '-b', 'feature/a')
    helper.write_file('A', 'change')
    helper.run_git('stash', 'save', 'some message')

    model = StashModel(app_context)
    stash_info = model.stash_info()

    stash_details = stash_info[0][0]
    assert stash_details in (
        'stash@{0}: On feature/a: some message',
        # Some versions of Git do not report the full branch name
        'stash@{0}: On a: some message',
    )

    stash_rev = stash_info[1][0]
    assert stash_rev == r'stash@{0}'

    stash_message = stash_info[3][0]
    assert stash_message in (
        'On feature/a: some message',
        'On a: some message',
    )
