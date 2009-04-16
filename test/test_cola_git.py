#!/usr/bin/env python
"""Tests various operations using the cola.git module
"""

import os
import unittest

import helper

from cola import git


class GitCommandTest(unittest.TestCase):
    """Runs tests using a git.Git instance"""

    def setUp(self):
        """Creates a git.Git instance for later use"""
        self.git = git.Git()

    def test_version(self):
        """Test running 'git version'"""
        version = self.git.version()
        self.failUnless(version.startswith('git version'))

    def test_tag(self):
        """Test running 'git tag'"""
        tags = self.git.tag().splitlines()
        self.failUnless( 'v1.0.0' in tags )

    def test_show(self):
        """Test running 'git show'"""
        sha = '1b9742bda5d26a4f250fa64657f66ed20624a084'
        contents = self.git.show(sha).splitlines()
        self.failUnless(contents[0] == '/build')

    def test_stdout(self):
        """Test overflowing the stdout buffer"""
        status, out = git.Git.execute([helper.fixture('stdout.py'), '8192'],
                                      with_status=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 8192)

    def test_stderr_empty(self):
        """Test that stderr is ignored by execute() without with_stderr"""
        status, out = git.Git.execute([helper.fixture('stderr.py'), '8192'],
                                      with_status=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 0)

    def test_stderr_nonempty_with_stderr(self):
        """Test that with_stderr makes execute() see stderr"""
        status, out = git.Git.execute([helper.fixture('stderr.py'), '8192'],
                                      with_status=True,
                                      with_stderr=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 8192)

    def test_stdout_and_stderr_ignores_stderr(self):
        """Test ignoring stderr when stdout+stderr are provided"""
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '8192',
                                       'stdout'], # otherwise, same as below
                                      with_status=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 8192)

    def test_stdout_and_stderr_ignores_stderr_v2(self):
        """Test ignoring stderr when stdout+stderr are provided (v2)"""
        # stdout_and_stderr.py swaps the order of the stdout, stderr write()
        # calls when argv[1] == 'stderr'.
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '8192',
                                       'stderr'], # otherwise, same as above
                                      with_status=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 8192)

    def test_stdout_and_stderr_sees_stderr(self):
        """Test seeing both stderr and stdout when both are available"""
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '8192',
                                       'stdout'], # otherwise, same as below
                                      with_status=True,
                                      with_stderr=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 8192 * 2)

    def test_stdout_and_stderr_sees_stderr_v2(self):
        """Test seeing both stderr and stdout when both are available (v2)."""
        # stdout_and_stderr.py swaps the order of the stdout, stderr write()
        # calls when argv[1] == 'stderr'.
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '8192',
                                       'stderr'], # otherwise, same as above
                                      with_status=True,
                                      with_stderr=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 8192 * 2)

if __name__ == '__main__':
    unittest.main()
