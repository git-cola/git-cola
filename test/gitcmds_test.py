from __future__ import absolute_import, division, unicode_literals
import os

from cola import gitcmds
from cola.widgets.remote import get_default_remote

from . import helper


class GitCmdsTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.gitcmds module."""

    def test_currentbranch(self):
        """Test current_branch()."""
        assert gitcmds.current_branch(self.context) == 'main'

    def test_branch_list_local(self):
        """Test branch_list(remote=False)."""
        context = self.context
        self.commit_files()
        expect = ['main']
        actual = gitcmds.branch_list(context, remote=False)
        assert expect == actual

    def test_branch_list_remote(self):
        """Test branch_list(remote=False)."""
        context = self.context
        expect = []
        actual = gitcmds.branch_list(context, remote=True)
        assert expect == actual

        self.commit_files()
        self.run_git('remote', 'add', 'origin', '.')
        self.run_git('fetch', 'origin')
        expect = ['origin/main']
        actual = gitcmds.branch_list(context, remote=True)
        assert expect == actual

        self.run_git('remote', 'rm', 'origin')
        expect = []
        actual = gitcmds.branch_list(context, remote=True)
        assert expect == actual

    def test_upstream_remote(self):
        """Test getting the configured upstream remote"""
        context = self.context
        assert gitcmds.upstream_remote(context) is None
        self.run_git('config', 'branch.main.remote', 'test')
        self.cfg.reset()
        assert gitcmds.upstream_remote(context) == 'test'

    def test_default_push(self):
        """Test getting what default branch to push to"""
        context = self.context

        # no default push, no remote branch configured
        assert get_default_remote(context) == 'origin'

        # default push set, no remote branch configured
        self.run_git('config', 'remote.pushDefault', 'test')
        self.cfg.reset()
        assert get_default_remote(context) == 'test'

        # default push set, default remote branch configured
        self.run_git('config', 'branch.main.remote', 'test2')
        self.cfg.reset()
        assert get_default_remote(context) == 'test2'

        # default push set, default remote branch configured, on different branch
        self.run_git('checkout', '-b', 'other-branch')
        assert get_default_remote(context) == 'test'

    def test_tracked_branch(self):
        """Test tracked_branch()."""
        context = self.context
        assert gitcmds.tracked_branch(context) is None
        self.run_git('config', 'branch.main.remote', 'test')
        self.run_git('config', 'branch.main.merge', 'refs/heads/main')
        self.cfg.reset()
        assert gitcmds.tracked_branch(context) == 'test/main'

    def test_tracked_branch_other(self):
        """Test tracked_branch('other')."""
        context = self.context
        assert gitcmds.tracked_branch(context, 'other') is None
        self.run_git('config', 'branch.other.remote', 'test')
        self.run_git('config', 'branch.other.merge', 'refs/heads/other/branch')
        self.cfg.reset()
        assert gitcmds.tracked_branch(context, 'other') == 'test/other/branch'

    def test_untracked_files(self):
        """Test untracked_files()."""
        context = self.context
        self.touch('C', 'D', 'E')
        assert gitcmds.untracked_files(context) == ['C', 'D', 'E']

    def test_all_files(self):
        context = self.context
        self.touch('other-file')
        all_files = gitcmds.all_files(context)

        assert 'A' in all_files
        assert 'B' in all_files
        assert 'other-file' in all_files

    def test_tag_list(self):
        """Test tag_list()."""
        context = self.context
        self.commit_files()
        self.run_git('tag', 'a')
        self.run_git('tag', 'b')
        self.run_git('tag', 'c')
        assert gitcmds.tag_list(context) == ['c', 'b', 'a']

    def test_merge_message_path(self):
        """Test merge_message_path()."""
        context = self.context
        self.touch('.git/SQUASH_MSG')
        assert gitcmds.merge_message_path(context) == os.path.abspath('.git/SQUASH_MSG')
        self.touch('.git/MERGE_MSG')
        assert gitcmds.merge_message_path(context) == os.path.abspath('.git/MERGE_MSG')
        os.unlink(gitcmds.merge_message_path(context))
        assert gitcmds.merge_message_path(context) == os.path.abspath('.git/SQUASH_MSG')
        os.unlink(gitcmds.merge_message_path(context))
        assert gitcmds.merge_message_path(context) is None

    def test_all_refs(self):
        self.commit_files()
        self.run_git('branch', 'a')
        self.run_git('branch', 'b')
        self.run_git('branch', 'c')
        self.run_git('tag', 'd')
        self.run_git('tag', 'e')
        self.run_git('tag', 'f')
        self.run_git('remote', 'add', 'origin', '.')
        self.run_git('fetch', 'origin')
        refs = gitcmds.all_refs(self.context)
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

    def test_all_refs_split(self):
        self.commit_files()
        self.run_git('branch', 'a')
        self.run_git('branch', 'b')
        self.run_git('branch', 'c')
        self.run_git('tag', 'd')
        self.run_git('tag', 'e')
        self.run_git('tag', 'f')
        self.run_git('remote', 'add', 'origin', '.')
        self.run_git('fetch', 'origin')
        local, remote, tags = gitcmds.all_refs(self.context, split=True)
        assert local == ['a', 'b', 'c', 'main']
        assert remote == ['origin/a', 'origin/b', 'origin/c', 'origin/main']
        assert tags == ['f', 'e', 'd']

    def test_binary_files(self):
        # Create a binary file and ensure that it's detected as binary.
        with open('binary-file.txt', 'wb') as f:
            f.write(b'hello\0world\n')
        assert gitcmds.is_binary(self.context, 'binary-file.txt')

        # Create a text file and ensure that it's not detected as binary.
        with open('text-file.txt', 'w') as f:
            f.write('hello world\n')
        assert not gitcmds.is_binary(self.context, 'text-file.txt')

        # Create a .gitattributes file and mark text-file.txt as binary.
        self.cfg.reset()
        with open('.gitattributes', 'w') as f:
            f.write('text-file.txt binary\n')
        assert gitcmds.is_binary(self.context, 'text-file.txt')

        # Remove the "binary" attribute using "-binary" from binary-file.txt.
        # Ensure that we do not flag this file as binary.
        with open('.gitattributes', 'w') as f:
            f.write('binary-file.txt -binary\n')
        assert not gitcmds.is_binary(self.context, 'binary-file.txt')

    def test_is_valid_ref(self):
        """Verify the behavior of is_valid_ref()"""
        # We are initially in a "git init" state. HEAD must be invalid.
        assert not gitcmds.is_valid_ref(self.context, 'HEAD')
        # Create the first commit onto the "test" branch.
        self.context.git.symbolic_ref('HEAD', 'refs/heads/test')
        self.git.commit(m='initial commit')
        assert gitcmds.is_valid_ref(self.context, 'HEAD')
        assert gitcmds.is_valid_ref(self.context, 'test')
        assert gitcmds.is_valid_ref(self.context, 'refs/heads/test')

    def test_diff_helper(self):
        self.commit_files()
        with open('A', 'w') as f:
            f.write('A change\n')
        self.run_git('add', 'A')
        actual = gitcmds.diff_helper(self.context, ref='HEAD', cached=True)
        assert '+A change\n' in actual
