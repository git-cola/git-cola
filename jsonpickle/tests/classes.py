# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 John Paulett (john -at- 7oars.com)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

class Thing(object):
    def __init__(self, name):
        self.name = name
        self.child = None
        
    def __repr__(self):
        return 'jsonpickle.tests.classes.Thing("%s")' % self.name
    
class DictSubclass(dict):
    name = 'Test'
    
class ListSubclass(list): 
    pass

class BrokenReprThing(Thing):
    def __repr__(self):
        raise Exception('%s has a broken repr' % self.name)
    def __str__(self):
        return '<BrokenReprThing "%s">' % self.name
