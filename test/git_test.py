#!/usr/bin/env python
"""Tests various operations using the cola.git module
"""
from __future__ import unicode_literals

import time
import signal
import unittest

from cola import git
from cola.compat import WIN32
from cola.git import STDOUT


class GitCommandTest(unittest.TestCase):
    """Runs tests using a git.Git instance"""

    def setUp(self):
        """Creates a git.Git instance for later use"""
        self.git = git.Git()

    def test_version(self):
        """Test running 'git version'"""
        version = self.git.version()[STDOUT]
        self.failUnless(version.startswith('git version'))

    def test_tag(self):
        """Test running 'git tag'"""
        tags = self.git.tag()[STDOUT].splitlines()
        self.failUnless( 'v1.0.0' in tags )

    def test_show(self):
        """Test running 'git show'"""
        sha = '1b9742bda5d26a4f250fa64657f66ed20624a084'
        contents = self.git.show(sha)[STDOUT].splitlines()
        self.failUnless(contents[0] == '/build')

    def test_stdout(self):
        """Test overflowing the stdout buffer"""
        # Write to stdout only
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)
        self.assertEqual(len(err), 0)

    def test_stderr(self):
        """Test that stderr is seen"""
        # Write to stderr and capture it
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 0)
        self.assertEqual(len(err), 1024 * 16 + 1)

    def test_stdout_and_stderr(self):
        """Test ignoring stderr when stdout+stderr are provided (v2)"""
        # Write to stdout and stderr but only capture stdout
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);'
                'sys.stderr.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)
        self.assertEqual(len(err), 1024 * 16 + 1)

    def test_it_doesnt_deadlock(self):
        """Test that we don't deadlock with both stderr and stdout"""
        # 16k+1 bytes to exhaust any output buffers
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);'
                'sys.stdout.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(out, '\0' * (1024 * 16 + 1))
        self.assertEqual(err, '\0' * (1024 * 16 + 1))

    def test_it_handles_interrupted_syscalls(self):
        """Test that we handle interrupted system calls"""
        # send ourselves a signal that causes EINTR
        if WIN32:
            # SIGALRM not supported on Windows
            return
        prev_handler = signal.signal(signal.SIGALRM, lambda x, y: 1)
        signal.alarm(1)
        time.sleep(0.1)
        status, out, err = git.Git.execute(['sleep', '1'])
        self.assertEqual(status, 0)

        signal.signal(signal.SIGALRM, prev_handler)


if __name__ == '__main__':
    unittest.main()
