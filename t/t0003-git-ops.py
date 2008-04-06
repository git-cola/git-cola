#!/usr/bin/env python
import os
import unittest

import testutils
from testutils import pipe

from ugit import git

class GitOpsTest(testutils.TestCase):
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
	
	def testConfig(self):
		self.shell("""
			git init 2>&1 >/dev/null
			git config section.key value
		""")
		value = git.config('section.key', get=True)

		self.failUnless( value == 'value' )

		#  Test config_set
		git.config_set('section.bool', True)
		value = git.config('section.bool', get=True)

		self.failUnless( value == 'true' )
		git.config_set('section.bool', False)

		# Test config_dict
		config_dict = git.config_dict(local=True)

		self.failUnless( config_dict['section_key'] == 'value' )
		self.failUnless( config_dict['section_bool'] == False )

		# Test config_dict --global
		global_dict = git.config_dict(local=False)

		self.failUnless( type(global_dict) is dict )

if __name__ == '__main__':
	unittest.main()
