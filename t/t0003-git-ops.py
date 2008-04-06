#!/usr/bin/env python
import os
import unittest

import testutils
from testutils import pipe

from ugit import git

class CommitTest(testutils.TestCase):
	def testCommit(self):
		self.shell("""
			echo A > A
			echo B > B
			git init 2>&1 >/dev/null
			git add A B
			""")
		git.commit(m="commit test")
		log = pipe("git log --pretty=oneline | wc -l")

		self.failUnless( '1' == log )

if __name__ == '__main__':
	unittest.main()
