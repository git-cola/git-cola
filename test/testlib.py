#!/usr/bin/env python
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
LAST_IDX = 0
TEST_SCRIPT_DIR = dirname(__file__)
ROOT_TMP_DIR = join( dirname(TEST_SCRIPT_DIR), 'tmp' )
TEST_TMP_DIR = join( ROOT_TMP_DIR, basename(sys.argv[0]) )

def setup_dir(dir):
    newdir = dir
    parentdir = dirname(newdir)
    if not os.path.isdir(parentdir):
        os.mkdir(parentdir)
    if not os.path.isdir(newdir):
        os.mkdir(newdir)

def get_test_dir():
    global LAST_IDX
    return '%s-%d.%04d' % (TEST_TMP_DIR, os.getpid(), LAST_IDX)

def create_test_dir():
    global LAST_IDX
    LAST_IDX += 1
    newdir = get_test_dir()
    setup_dir(newdir)
    os.chdir(newdir)
    return newdir

def remove_dir(dir):
    if not DEBUG_MODE:
        os.chdir(ROOT_TMP_DIR)
        shutil.rmtree(dir)

def remove_test_dir():
    global LAST_IDX
    testdir = get_test_dir()
    remove_dir(testdir)
    LAST_IDX -= 1

def shell(cmd):
    result = os.system(cmd)
    return result

def pipe(cmd):
    p = os.popen(cmd)
    out = p.read().strip()
    p.close()
    return out

# All tests that operate on temporary data derive from testlib.TestCase
class TestCase(unittest.TestCase):
    def setUp(self):
        create_test_dir()
    def tearDown(self):
        remove_test_dir()
    def shell(self, cmd):
        result = shell(cmd)
        self.failIf(result != 0)
    def get_test_dir(self):
        return get_test_dir()

class DuckModel(Model):
    def init(self):
        duck = Model().create(sound='quack',name='ducky')
        goose = Model().create(sound='cluck',name='goose')

        self.create(attribute = 'value',
                    mylist=[duck,duck,goose])
        self.hello = 'world'
        self.set_mylist([duck,duck,goose, 'meow', 'caboose',42])

    def duckMethod(self):
        return 'duck'

class InnerModel(Model):
    def init(self):
        self.create(foo = 'bar')

class NestedModel(Model):
    def init(self):
        self.create(inner = InnerModel(),
                    innerList = [],
                    normaList = [ 1,2,3, [4,5, [6,7,8], 9]])
        self.innerList.append(InnerModel())
        self.innerList.append([InnerModel()])
        self.innerList.append([[InnerModel()]])
        self.innerList.append([[[InnerModel(),InnerModel()]]])
        self.innerList.append({"foo": InnerModel()})
