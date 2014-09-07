from __future__ import unicode_literals

import os
import shutil
import stat
import unittest
import subprocess
import tempfile

from cola import core
from cola import git
from cola import gitcfg
from cola import gitcmds


def tmp_path(*paths):
    """Returns a path relative to the test/tmp directory"""
    return os.path.join(os.path.dirname(__file__), 'tmp', *paths)


def fixture(*paths):
    return os.path.join(os.path.dirname(__file__), 'fixtures', *paths)


def run_unittest(suite):
    return unittest.TextTestRunner(verbosity=2).run(suite)


# shutil.rmtree() can't remove read-only files on Windows.  This onerror
# handler, adapted from <http://stackoverflow.com/a/1889686/357338>, works
# around this by changing such files to be writable and then re-trying.
def remove_readonly(func, path, exc_info):
    if func == os.remove and not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise


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
    def setUp(self, commit=True):
        TmpPathTestCase.setUp(self)
        self.initialize_repo()
        if commit:
            self.commit_files()
        git.current().set_worktree(core.getcwd())
        gitcfg.current().reset()
        gitcmds.reset()

    def git(self, *args):
        p = subprocess.Popen(['git'] + list(args), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        output, error = p.communicate()
        self.failIf(p.returncode != 0)
        return output.strip()

    def initialize_repo(self):
        self.git('init')
        self.touch('A', 'B')
        self.git('add', 'A', 'B')

    def commit_files(self):
        self.git('commit', '-m', 'intitial commit')
