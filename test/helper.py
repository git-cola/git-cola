from __future__ import unicode_literals

import os
import shutil
import stat
import unittest
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


def shell(cmd):
    return os.system(cmd)


def pipe(cmd):
    p = os.popen(cmd)
    out = core.fread(p).strip()
    p.close()
    return out


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
        git.instance().set_worktree(core.getcwd())
        gitcfg.instance().reset()
        gitcmds.clear_cache()

    def initialize_repo(self):
        self.shell("""
            git init > /dev/null &&
            touch A B &&
            git add A B
        """)

    def commit_files(self):
        self.shell('git commit -m"Initial commit" > /dev/null')
