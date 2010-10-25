import os
import sys
import shutil
import unittest
import tempfile

from cola import core
from cola import git
from cola import gitcfg


def tmp_path(*paths):
    """Returns a path relative to the test/tmp directory"""
    return os.path.join(os.path.dirname(__file__), 'tmp', *paths)


def fixture(*paths):
    return os.path.join(os.path.dirname(__file__), 'fixtures', *paths)


def shell(cmd):
    return os.system(cmd)


def pipe(cmd):
    p = os.popen(cmd)
    out = core.read_nointr(p).strip()
    p.close()
    return out


class TmpPathTestCase(unittest.TestCase):
    def setUp(self):
        self._testdir = tempfile.mkdtemp('_cola_test')
        os.chdir(self._testdir)
        print self._testdir

    def tearDown(self):
        """Remove the test directory and return to the tmp root."""
        path = self._testdir
        os.chdir(tmp_path())
        shutil.rmtree(path)

    def shell(self, cmd):
        result = shell(cmd)
        self.failIf(result != 0)

    def test_path(self, *paths):
        return os.path.join(self._testdir, *paths)


class GitRepositoryTestCase(TmpPathTestCase):
    """Tests that operate on temporary git repositories."""
    def setUp(self, commit=True):
        TmpPathTestCase.setUp(self)
        self.initialize_repo()
        if commit:
            self.commit_files()
        git.instance().load_worktree(os.getcwd())
        gitcfg.instance().reset()

    def initialize_repo(self):
        self.shell("""
            git init > /dev/null &&
            touch A B &&
            git add A B
        """)

    def commit_files(self):
        self.shell('git commit -m"Initial commit" > /dev/null')
