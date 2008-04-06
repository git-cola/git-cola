#!/usr/bin/env python
import os
import unittest

import testutils
from testmodel import TestModel

from ugit import git

class GitCommandTest(unittest.TestCase):
	def testGitVersion(self):
		version = git.version()
		self.failUnless( version.startswith('git version') )

	def testGitTag(self):
		tags = git.tag().splitlines()
		self.failUnless( 'ugit-0.0' in tags )

	def testGitShowCdUp(self):
		os.chdir(testutils.TEST_SCRIPT_DIR)
		cdup = git.rev_parse(show_cdup=True)
		self.failUnless( cdup == '../' )

	def testGitShow(self):
		id = '1b9742bda5d26a4f250fa64657f66ed20624a084'
		contents = git.show(id).splitlines()
		self.failUnless( contents[0] == '/build' )


if __name__ == '__main__':
	unittest.main()
