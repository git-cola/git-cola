#!/usr/bin/env python
"""Tests basic git operations: commit, log, config"""
import os
import unittest

import helper
from cola.models import main

class ColaBasicGitTestCase(helper.GitRepositoryTestCase):

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)

    def test_git_commit(self):
        """Test running 'git commit' via cola.git"""
        self.shell("""
            echo A > A
            echo B > B
            git add A B
            """)

        model = main.MainModel(cwd=os.getcwd())
        model.git.commit(m='commit test')
        log = helper.pipe('git log --pretty=oneline | wc -l')

        self.assertEqual(log.strip(), '1')

    def test_git_config(self):
        """Test cola.git.config()"""
        self.shell('git config section.key value')
        model = main.MainModel(cwd=os.getcwd())
        value = model.git.config('section.key', get=True)

        self.assertEqual(value, 'value')

        #  Test config_set
        model.config_set('section.bool', True)
        value = model.git.config('section.bool', get=True)

        self.assertEqual(value, 'true')
        model.config_set('section.bool', False)

        # Test config_dict
        config_dict = model.config_dict(local=True)

        self.assertEqual(config_dict['section_key'], 'value')
        self.assertEqual(config_dict['section_bool'], False)

        # Test config_dict --global
        global_dict = model.config_dict(local=False)

        self.assertEqual(type(global_dict), dict)


if __name__ == '__main__':
    unittest.main()
