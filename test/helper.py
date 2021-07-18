from __future__ import absolute_import, division, unicode_literals
import os
import shutil
import stat
import unittest
import tempfile

import pytest
try:
    from unittest.mock import Mock, patch  # noqa pylint: disable=unused-import
except ImportError:
    from mock import Mock, patch  # noqa pylint: disable=unused-import

from cola import core
from cola import git
from cola import gitcfg
from cola import gitcmds
from cola.models import main


def tmp_path(*paths):
    """Returns a path relative to the test/tmp directory"""
    dirname = core.decode(os.path.dirname(__file__))
    return os.path.join(dirname, 'tmp', *paths)


def fixture(*paths):
    dirname = core.decode(os.path.dirname(__file__))
    return os.path.join(dirname, 'fixtures', *paths)


# shutil.rmtree() can't remove read-only files on Windows.  This onerror
# handler, adapted from <http://stackoverflow.com/a/1889686/357338>, works
# around this by changing such files to be writable and then re-trying.
def remove_readonly(func, path, _exc_info):
    if func is os.remove and not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise AssertionError('Should not happen')


@pytest.fixture
def run_in_tmpdir():
    """Run tests in a temporary directory and yield the tmp directory"""
    tmp_directory = tempfile.mkdtemp('-cola-test')
    current_directory = os.getcwd()
    os.chdir(tmp_directory)

    yield tmp_directory

    os.chdir(current_directory)
    shutil.rmtree(tmp_directory, onerror=remove_readonly)


def touch(*paths):
    """Open and close a file to either create it or update its mtime"""
    for path in paths:
        open(path, 'a').close()


def write_file(path, content):
    """Write content to the specified file path"""
    with open(path, 'w') as f:
        f.write(content)


def append_file(path, content):
    """Open a file in append mode and write content to it"""
    with open(path, 'a') as f:
        f.write(content)


class TmpPathTestCase(unittest.TestCase):
    """Run operations in a temporary directory"""

    def setUp(self):
        self._testdir = tempfile.mkdtemp('_cola_test')
        os.chdir(self._testdir)

    def tearDown(self):
        """Remove the test directory and return to the tmp root."""
        path = self._testdir
        os.chdir(tmp_path())
        shutil.rmtree(path, onerror=remove_readonly)

    def test_path(self, *paths):
        return os.path.join(self._testdir, *paths)

    append_file = staticmethod(append_file)

    touch = staticmethod(touch)

    write_file = staticmethod(write_file)


def run_git(*args):
    """Run git with the specified arguments"""
    status, out, _ = core.run_command(['git'] + list(args))
    assert status == 0
    return out


def commit_files():
    """Commit the current state as the initial commit"""
    run_git('commit', '-m', 'initial commit')


def initialize_repo():
    """Initialize a git repository in the current directory"""
    run_git('init')
    run_git('symbolic-ref', 'HEAD', 'refs/heads/main')
    run_git('config', '--local', 'user.name', 'Your Name')
    run_git('config', '--local', 'user.email', 'you@example.com')
    run_git('config', '--local', 'commit.gpgsign', 'false')
    run_git('config', '--local', 'tag.gpgsign', 'false')
    touch('A', 'B')
    run_git('add', 'A', 'B')


@pytest.fixture
def app_context(run_in_tmpdir):  # pylint: disable=redefined-outer-name,unused-argument
    """Create a repository in a temporary directory and return its ApplicationContext"""
    initialize_repo()
    context = Mock()
    context.git = git.create()
    context.git.set_worktree(core.getcwd())
    context.cfg = gitcfg.create(context)
    context.model = main.create(context)

    context.cfg.reset()
    gitcmds.reset()
    return context


class GitRepositoryTestCase(TmpPathTestCase):
    """Tests that operate on temporary git repositories."""

    def setUp(self):
        TmpPathTestCase.setUp(self)
        initialize_repo()
        self.context = context = mock.Mock()
        context.git = git.create()
        context.git.set_worktree(core.getcwd())
        context.cfg = gitcfg.create(context)
        context.model = self.model = main.create(self.context)
        self.git = context.git
        self.cfg = context.cfg
        self.cfg.reset()
        gitcmds.reset()

    commit_files = staticmethod(commit_files)

    run_git = staticmethod(run_git)
