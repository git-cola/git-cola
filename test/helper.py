import os
import sys
import shutil
import unittest

from cola import core


DEBUG_MODE = os.getenv('COLA_TEST_DEBUG','')
CUR_TEST = 0


def tmp_root():
    return os.path.join(os.path.dirname(__file__), 'tmp')


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


def get_dir():
    cur_tmpdir = os.path.join(tmp_root(), os.path.basename(sys.argv[0]))
    return '%s-%d.%04d' % (cur_tmpdir, os.getpid(), CUR_TEST)


def create_dir():
    global CUR_TEST
    CUR_TEST += 1
    newdir = get_dir()
    setup_dir(newdir)
    os.chdir(newdir)
    return newdir


def rmdir(path):
    if not DEBUG_MODE:
        os.chdir(tmp_root())
        shutil.rmtree(path)


def remove_dir():
    global CUR_TEST
    testdir = get_dir()
    rmdir(testdir)
    CUR_TEST -= 1


def shell(cmd):
    return os.system(cmd)


def pipe(cmd):
    p = os.popen(cmd)
    out = core.read_nointr(p).strip()
    p.close()
    return out


class GitRepositoryTestCase(unittest.TestCase):
    """Tests that operate on temporary git repositories."""
    def setUp(self, commit=False):
        create_dir()
        self.initialize_repo()
        if commit:
            self.commit_files()

    def initialize_repo(self):
        self.shell("""
            git init > /dev/null
            touch A B
            git add A B
        """)

    def commit_files(self):
        self.shell('git commit -m"Initial commit" > /dev/null')

    def tearDown(self):
        remove_dir()

    def shell(self, cmd):
        result = shell(cmd)
        self.failIf(result != 0)

    def get_dir(self):
        return get_dir()
