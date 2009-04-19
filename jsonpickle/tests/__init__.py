# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 John Paulett (john -at- 7oars.com)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import unittest

import jsonpickle.tests.util_tests
import jsonpickle.tests.jsonpickle_test

def suite():
    suite = unittest.TestSuite()    
    suite.addTest(jsonpickle.tests.util_tests.suite())
    suite.addTest(jsonpickle.tests.jsonpickle_test.suite())
    return suite

def main():
    #unittest.main(defaultTest='suite')
    unittest.TextTestRunner(verbosity=2).run(suite())
    
if __name__ == '__main__':
    main()
