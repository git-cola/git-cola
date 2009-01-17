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
        status, out = git.Git.execute([helper.fixture('stdout.py'),
                                       '65536'],
                                      with_extended_output=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536)

    def test_stderr(self):
        status, out = git.Git.execute([helper.fixture('stderr.py'),
                                       '65536'],
                                      with_extended_output=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536)

    def test_stdout_stderr1(self):
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '65536', 'stdout'],
                                      with_extended_output=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536 * 2)

    def test_stdout_stderr2(self):
        status, out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                                       '65536', 'stderr'],
                                      with_extended_output=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 65536 * 2)

    def test_stdout_stderr3(self):
        out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                               '65536', 'stderr'],
                              with_raw_output=True)
        self.assertEqual(len(out), 65536)

    def test_stdout_stderr4(self):
        out = git.Git.execute([helper.fixture('stdout_and_stderr.py'),
                               '65536', 'stdout'],
                              with_raw_output=True)
        self.assertEqual(len(out), 65536)

if __name__ == '__main__':
    unittest.main()
