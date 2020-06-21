from __future__ import absolute_import, division, unicode_literals
import os
import shutil
import stat
import unittest
import tempfile

import mock

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


def run_unittest(suite):
    return unittest.TextTestRunner(verbosity=2).run(suite)


# shutil.rmtree() can't remove read-only files on Windows.  This onerror
# handler, adapted from <http://stackoverflow.com/a/1889686/357338>, works
# around this by changing such files to be writable and then re-trying.
def remove_readonly(func, path, _exc_info):
    if func is os.remove and not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise AssertionError('Should not happen')


class TmpPathTestCase(unittest.TestCase):
    def setUp(self):
        self._testdir = tempfile.mkdtemp('_cola_test')
        os.chdir(self._testdir)

    def tearDown(self):
        """Remove the test directory and return to the tmp root."""
        path = self._testdir
        os.chdir(tmp_path())
        shutil.rmtree(path, onerror=remove_readonly)

    @staticmethod
    def touch(*paths):
        for path in paths:
            open(path, 'a').close()

    @staticmethod
    def write_file(path, content):
        with open(path, 'w') as f:
            f.write(content)

    @staticmethod
    def append_file(path, content):
        with open(path, 'a') as f:
            f.write(content)

    def test_path(self, *paths):
        return os.path.join(self._testdir, *paths)


class GitRepositoryTestCase(TmpPathTestCase):
    """Tests that operate on temporary git repositories."""

    def setUp(self):
        TmpPathTestCase.setUp(self)
        self.initialize_repo()
        self.context = context = mock.Mock()
        context.git = git.create()
        context.git.set_worktree(core.getcwd())
        context.cfg = gitcfg.create(context)
        context.model = self.model = main.create(self.context)
        self.git = context.git
        self.cfg = context.cfg
        self.cfg.reset()
        gitcmds.reset()

    def run_git(self, *args):
        status, out, _ = core.run_command(['git'] + list(args))
        self.assertEqual(status, 0)
        return out

    def initialize_repo(self):
        self.run_git('init')
        self.run_git('symbolic-ref', 'HEAD', 'refs/heads/main')
        self.run_git('config', '--local', 'user.name', 'Your Name')
        self.run_git('config', '--local', 'user.email', 'you@example.com')
        self.touch('A', 'B')
        self.run_git('add', 'A', 'B')

    def commit_files(self):
        self.run_git('commit', '-m', 'initial commit')
