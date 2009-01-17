#!/usr/bin/env python
import os
import unittest

from cola import git

import helper

class GitCommandTest(unittest.TestCase):
    def setUp(self):
        self.git = git.Git()

    def test_version(self):
        version = self.git.version()
        self.failUnless(version.startswith('git version'))

    def test_tag(self):
        tags = self.git.tag().splitlines()
        self.failUnless( 'v1.0.0' in tags )

    def test_show(self):
        sha = '1b9742bda5d26a4f250fa64657f66ed20624a084'
        contents = self.git.show(sha).splitlines()
        self.failUnless(contents[0] == '/build')

    def test_stdout(self):
        status, out = git.Git.execute([helper.fixture('stdout.py'), '65536'],
                                      with_extended_output=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536)

    def test_stderr_empty(self):
        """Test that stderr is ignored by Git.execute() without the with_stderr option."""
        status, out = git.Git.execute([helper.fixture('stderr.py'), '65536'],
                                      with_extended_output=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 0)

    def test_stderr_nonempty_with_stderr(self):
        """Test that with_stderr makes Git.execute() see stderr."""
        status, out = git.Git.execute([helper.fixture('stderr.py'), '65536'],
                                      with_extended_output=True,
                                      with_stderr=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536)

    def test_stdout_and_stderr_ignores_stderr(self):
        """Test ignoring stderr when both are provided."""
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '65536',
                                       'stdout'], # otherwise, same as below
                                      with_extended_output=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536)

    def test_stdout_and_stderr_ignores_stderr_v2(self):
        """Test ignoring stderr when both are provided. (v2)"""
        # stdout_and_stderr.py swaps the order of the stdout, stderr write()
        # calls when argv[1] == 'stderr'.
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '65536',
                                       'stderr'], # otherwise, same as above
                                      with_extended_output=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536)

    def test_stdout_and_stderr_sees_stderr(self):
        """Test seeing both stderr and stdout when both are available."""
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '65536',
                                       'stdout'], # otherwise, same as below
                                      with_extended_output=True,
                                      with_stderr=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536 * 2)

    def test_stdout_and_stderr_sees_stderr_v2(self):
        """Test seeing both stderr and stdout when both are available (v2)."""
        # stdout_and_stderr.py swaps the order of the stdout, stderr write()
        # calls when argv[1] == 'stderr'.
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '65536',
                                       'stderr'], # otherwise, same as above
                                      with_extended_output=True,
                                      with_stderr=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536 * 2)

if __name__ == '__main__':
    unittest.main()
