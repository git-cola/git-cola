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


def create_dir():
    newdir = tempfile.mkdtemp('cola_test_XXXXXX')
    os.chdir(newdir)
    return newdir


def remove_dir(path):
    """Remove the test's tmp directory and return to the tmp root."""
    if os.path.isdir(path):
        os.chdir(tmp_path())
        shutil.rmtree(path)


def shell(cmd):
    return os.system(cmd)


def pipe(cmd):
    p = os.popen(cmd)
    out = core.read_nointr(p).strip()
    p.close()
    return out


class TmpPathTestCase(unittest.TestCase):
    def setUp(self):
        self._testdir = create_dir()

    def tearDown(self):
        remove_dir(self._testdir)

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
