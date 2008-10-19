#!/usr/bin/env python
import os
import unittest

from cola import git

class GitCommandTest(unittest.TestCase):
    def setUp(self):
        self.git = git.Git()

    def testGitVersion(self):
        version = self.git.version()
        self.failUnless(version.startswith('git version'))

    def testGitTag(self):
        tags = self.git.tag().splitlines()
        self.failUnless( 'v1.0.0' in tags )

    def testGitShow(self):
        id = '1b9742bda5d26a4f250fa64657f66ed20624a084'
        contents = self.git.show(id).splitlines()
        self.failUnless(contents[0] == '/build')

if __name__ == '__main__':
    unittest.main()
