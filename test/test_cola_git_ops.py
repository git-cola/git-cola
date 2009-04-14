#!/usr/bin/env python
"""Tests basic git operations: commit, log, config"""
import os
import unittest

import helper
from cola import models

class ColaBasicGitTestCase(helper.TestCase):

    def test_git_commit(self):
        """Test running 'git commit' via cola.git"""
        self.shell("""
            echo A > A
            echo B > B
            git init 2>&1 > /dev/null
            git add A B
            """)

        model = models.Model()
        model.git.commit(m="commit test")
        log = helper.pipe('git log --pretty=oneline | wc -l')

        self.failUnless('1' == log)

    def test_git_config(self):
        """Test cola.git.config()"""
        self.shell("""
            git init 2>&1 >/dev/null
            git config section.key value
        """)
        model = models.Model()
        value = model.git.config('section.key', get=True)

        self.failUnless(value == 'value')

        #  Test config_set
        model.config_set('section.bool', True)
        value = model.git.config('section.bool', get=True)

        self.failUnless(value == 'true')
        model.config_set('section.bool', False)

        # Test config_dict
        config_dict = model.config_dict(local=True)

        self.failUnless(config_dict['section_key'] == 'value')
        self.failUnless(config_dict['section_bool'] == False)

        # Test config_dict --global
        global_dict = model.config_dict(local=False)

        self.failUnless(type(global_dict) is dict)

if __name__ == '__main__':
    unittest.main()
