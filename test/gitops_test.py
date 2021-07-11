#!/usr/bin/env python
"""Tests basic git operations: commit, log, config"""
from __future__ import absolute_import, division, unicode_literals
import unittest

from . import helper


class ColaBasicGitTestCase(helper.GitRepositoryTestCase):
    def test_git_commit(self):
        """Test running 'git commit' via cola.git"""
        self.write_file('A', 'A')
        self.write_file('B', 'B')
        self.run_git('add', 'A', 'B')

        self.git.commit(m='initial commit')
        log = self.run_git('-c', 'log.showsignature=false', 'log', '--pretty=oneline')

        self.assertEqual(len(log.splitlines()), 1)

    def test_git_config(self):
        """Test cola.git.config()"""
        self.run_git('config', 'section.key', 'value')
        value = self.git.config('section.key', get=True)
        self.assertEqual(value, (0, 'value', ''))


if __name__ == '__main__':
    unittest.main()
