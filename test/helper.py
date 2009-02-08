import os
import sys
import shutil
import unittest
from os.path import join
from os.path import dirname
from os.path import basename

import os
from cola.model import Model

DEBUG_MODE = os.getenv('DEBUG','')

TEST_SCRIPT_DIR = dirname(__file__)
ROOT_TMP_DIR = join(dirname(TEST_SCRIPT_DIR), 'tmp')
TEST_TMP_DIR = join(ROOT_TMP_DIR, basename(sys.argv[0]))

LAST_IDX = 0


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

def rmdir(dir):
    if not DEBUG_MODE:
        os.chdir(ROOT_TMP_DIR)
        shutil.rmtree(dir)

def remove_dir():
    global LAST_IDX
    testdir = get_dir()
    rmdir(testdir)
    LAST_IDX -= 1

def shell(cmd):
    return os.system(cmd)

def pipe(cmd):
    p = os.popen(cmd)
    out = p.read().strip()
    p.close()
    return out

# All tests that operate on temporary data derive from helper.TestCase
class TestCase(unittest.TestCase):
    def setUp(self):
        create_dir()
    def tearDown(self):
        remove_dir()
    def shell(self, cmd):
        result = shell(cmd)
        self.failIf(result != 0)
    def get_dir(self):
        return get_dir()

class DuckModel(Model):
    def __init__(self):
        Model.__init__(self)

        duck = Model()
        duck.sound = 'quack'
        duck.name = 'ducky'

        goose = Model()
        goose.sound = 'cluck'
        goose.name = 'goose'

        self.attribute = 'value'
        self.mylist = [duck, duck, goose]
        self.hello = 'world'
        self.set_mylist([duck, duck, goose, 'meow', 'caboose', 42])

    def duckMethod(self):
        return 'duck'

class InnerModel(Model):
    def __init__(self):
        Model.__init__(self)
        self.foo = 'bar'

class NestedModel(Model):
    def __init__(self):
        Model.__init__(self)
        self.inner = InnerModel()
        self.innerlist = []
        self.innerlist.append(InnerModel())
        self.innerlist.append([InnerModel()])
        self.innerlist.append([[InnerModel()]])
        self.innerlist.append([[[InnerModel(),InnerModel()]]])
        self.innerlist.append({"foo": InnerModel()})
