# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 John Paulett (john -at- 7oars.com)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import unittest
import doctest
import time
import datetime

import jsonpickle.util
from jsonpickle.util import *
from jsonpickle.tests.classes import Thing, ListSubclass, DictSubclass

class IsPrimitiveTestCase(unittest.TestCase):
    def test_int(self):
        self.assertTrue(is_primitive(0))
        self.assertTrue(is_primitive(3))
        self.assertTrue(is_primitive(-3))

    def test_float(self):
        self.assertTrue(is_primitive(0))
        self.assertTrue(is_primitive(3.5))
        self.assertTrue(is_primitive(-3.5))
        self.assertTrue(is_primitive(float(3)))

    def test_long(self):
        self.assertTrue(is_primitive(long(3)))

    def test_bool(self):
        self.assertTrue(is_primitive(True))
        self.assertTrue(is_primitive(False))

    def test_None(self):
        self.assertTrue(is_primitive(None))

    def test_str(self):
        self.assertTrue(is_primitive('hello'))
        self.assertTrue(is_primitive(''))

    def test_unicode(self):
        self.assertTrue(is_primitive(u'hello'))
        self.assertTrue(is_primitive(u''))
        self.assertTrue(is_primitive(unicode('hello')))

    def test_list(self):
        self.assertFalse(is_primitive([]))
        self.assertFalse(is_primitive([4, 4]))

    def test_dict(self):
        self.assertFalse(is_primitive({'key':'value'}))
        self.assertFalse(is_primitive({}))

    def test_tuple(self):
        self.assertFalse(is_primitive((1, 3)))
        self.assertFalse(is_primitive((1,)))

    def test_set(self):
        self.assertFalse(is_primitive(set([1, 3])))

    def test_object(self):
        self.assertFalse(is_primitive(Thing('test')))

class IsCollection(unittest.TestCase):
    def test_list(self):
        self.assertTrue(is_list([1, 2]))
    
    def test_set(self):
        self.assertTrue(is_set(set([1, 2])))
        
    def test_tuple(self):
        self.assertTrue(is_tuple((1, 2)))
        
    def test_dict(self):
        self.assertFalse(is_list({'key':'value'}))
        self.assertFalse(is_set({'key':'value'}))
        self.assertFalse(is_tuple({'key':'value'}))
    
    def test_other(self):
        self.assertFalse(is_list(1))
        self.assertFalse(is_set(1))
        self.assertFalse(is_tuple(1))

class IsDictionary(unittest.TestCase):
    def test_dict(self):
        self.assertTrue(is_dictionary({'key':'value'}))
    
    def test_list(self):
        self.assertFalse(is_dictionary([1, 2]))

class IsDictionarySubclass(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(is_dictionary_subclass(DictSubclass()))
    
    def test_dict(self):
        self.assertFalse(is_dictionary_subclass({'key':'value'}))

class IsCollectionSubclass(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(is_collection_subclass(ListSubclass()))
    
    def test_list(self):
        self.assertFalse(is_collection_subclass([]))

class IsNonComplex(unittest.TestCase):
    def setUp(self):
        self.time = time.struct_time('123456789')
        
    def test_time_struct(self):
        self.assertTrue(is_noncomplex(self.time))

    def test_other(self):
        self.assertFalse(is_noncomplex('a'))

class IsRepr(unittest.TestCase):
    def setUp(self):
        self.time = datetime.datetime.now()
        
    def test_datetime(self):
        self.assertTrue(is_repr(self.time))
        
    def test_date(self):
        self.assertTrue(is_repr(self.time.date()))
    
    def test_time(self):
        self.assertTrue(is_repr(self.time.time()))
        
    def test_timedelta(self):
        self.assertTrue(is_repr(datetime.timedelta(4)))
        
    def test_object(self):
        self.assertFalse(is_repr(object()))
    
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(IsPrimitiveTestCase))
    suite.addTest(unittest.makeSuite(IsCollection))
    suite.addTest(unittest.makeSuite(IsDictionary))
    suite.addTest(unittest.makeSuite(IsDictionarySubclass))
    suite.addTest(unittest.makeSuite(IsCollectionSubclass))
    suite.addTest(unittest.makeSuite(IsNonComplex))
    suite.addTest(unittest.makeSuite(IsRepr))
    suite.addTest(doctest.DocTestSuite(jsonpickle.util))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
