import os
import sys
import shutil
import unittest

from cola import core
from cola import gitcmd
from cola import gitcfg

CUR_TEST = 0


def tmp_path(*paths):
    """Returns a path relative to the test/tmp directory"""
    return os.path.join(os.path.dirname(__file__), 'tmp', *paths)


def fixture(*paths):
    return os.path.join(os.path.dirname(__file__), 'fixtures', *paths)


def setup_dir(dir):
    newdir = dir
    parentdir = os.path.dirname(newdir)
    if not os.path.isdir(parentdir):
        os.mkdir(parentdir)
    if not os.path.isdir(newdir):
        os.mkdir(newdir)


def test_path(*paths):
    cur_tmpdir = os.path.join(tmp_path(), os.path.basename(sys.argv[0]))
    root = '%s-%d.%04d' % (cur_tmpdir, os.getpid(), CUR_TEST)
    return os.path.join(root, *paths)


def create_dir():
    global CUR_TEST
    CUR_TEST += 1
    newdir = test_path()
    setup_dir(newdir)
    os.chdir(newdir)
    return newdir


def remove_dir():
    """Remove the test's tmp directory and return to the tmp root."""
    global CUR_TEST
    path = test_path()
    if os.path.isdir(path):
        os.chdir(tmp_path())
        shutil.rmtree(path)
    CUR_TEST -= 1


def shell(cmd):
    return os.system(cmd)


def pipe(cmd):
    p = os.popen(cmd)
    out = core.read_nointr(p).strip()
    p.close()
    return out


class TmpPathTestCase(unittest.TestCase):
    def setUp(self):
        create_dir()

    def tearDown(self):
        remove_dir()

    def shell(self, cmd):
        result = shell(cmd)
        self.failIf(result != 0)

    def test_path(self, *paths):
        return test_path(*paths)


class GitRepositoryTestCase(TmpPathTestCase):
    """Tests that operate on temporary git repositories."""
    def setUp(self, commit=True):
        TmpPathTestCase.setUp(self)
        self.initialize_repo()
        if commit:
            self.commit_files()
        gitcmd.instance().load_worktree(os.getcwd())
        gitcfg.instance().reset()

    def initialize_repo(self):
        self.shell("""
            git init > /dev/null
            touch A B
            git add A B
        """)

    def commit_files(self):
        self.shell('git commit -m"Initial commit" > /dev/null')
