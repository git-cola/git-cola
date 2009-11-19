import os
import sys
import shutil
import unittest
from os.path import join
from os.path import dirname
from os.path import basename

from cola import core


DEBUG_MODE = os.getenv('COLA_TEST_DEBUG','')

TEST_SCRIPT_DIR = dirname(__file__)
ROOT_TMP_DIR = join(TEST_SCRIPT_DIR, 'tmp')
TEST_TMP_DIR = join(ROOT_TMP_DIR, basename(sys.argv[0]))

LAST_IDX = 0


def tmp_path(*paths):
    """Returns a path relative to the test/tmp directory"""
    return join(TEST_SCRIPT_DIR, 'tmp', *paths)

def fixture(*paths):
    return join(TEST_SCRIPT_DIR, 'fixtures', *paths)

def setup_dir(dir):
    newdir = dir
    parentdir = dirname(newdir)
    if not os.path.isdir(parentdir):
        os.mkdir(parentdir)
    if not os.path.isdir(newdir):
        os.mkdir(newdir)

def get_dir():
    global LAST_IDX
    return '%s-%d.%04d' % (TEST_TMP_DIR, os.getpid(), LAST_IDX)

def create_dir():
    global LAST_IDX
    LAST_IDX += 1
    newdir = get_dir()
    setup_dir(newdir)
    os.chdir(newdir)
    return newdir

def rmdir(path):
    if not DEBUG_MODE:
        os.chdir(ROOT_TMP_DIR)
        shutil.rmtree(path)

def remove_dir():
    global LAST_IDX
    testdir = get_dir()
    rmdir(testdir)
    LAST_IDX -= 1

def shell(cmd):
    return os.system(cmd)

def pipe(cmd):
    p = os.popen(cmd)
    out = core.read_nointr(p).strip()
    p.close()
    return out


class TestCase(unittest.TestCase):
    """Tests that operate on temporary git repositories."""
    def setUp(self):
        create_dir()

    def tearDown(self):
        remove_dir()

    def shell(self, cmd):
        result = shell(cmd)
        self.failIf(result != 0)

    def get_dir(self):
        return get_dir()
