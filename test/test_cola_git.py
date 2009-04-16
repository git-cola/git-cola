#!/usr/bin/env python
"""Tests various operations using the cola.git module
"""

import os
import time
import signal
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
        # Write to stdout only
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);')
        status, out = git.Git.execute(['python', '-c', code],
                                      with_status=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)

    def test_stderr_empty(self):
        """Test that stderr is ignored by execute() without with_stderr"""
        # Write to stderr but ignore it
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);')
        status, out = git.Git.execute(['python', '-c', code],
                                      with_status=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 0)

    def test_stderr_nonempty_with_stderr(self):
        """Test that with_stderr makes execute() see stderr"""
        # Write to stderr and capture it
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);')
        status, out = git.Git.execute(['python', '-c', code],
                                      with_status=True,
                                      with_stderr=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)

    def test_stdout_and_stderr_ignores_stderr(self):
        """Test ignoring stderr when stdout+stderr are provided"""
        # Write to stdout only
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);')
        status, out = git.Git.execute(['python', '-c', code],
                                      with_status=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)

    def test_stdout_and_stderr_ignores_stderr_v2(self):
        """Test ignoring stderr when stdout+stderr are provided (v2)"""
        # Write to stdout and stderr but only capture stdout
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);'
                'sys.stderr.write(s);')
        status, out = git.Git.execute(['python', '-c', code],
                                      with_status=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)

    def test_stdout_and_stderr_sees_stderr(self):
        """Test seeing both stderr and stdout when both are available"""
        # Write to stdout and stderr and capture both
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);'
                'sys.stderr.write(s);')
        status, out = git.Git.execute(['python', '-c', code],
                                      with_status=True,
                                      with_stderr=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 * 2 + 2)

    def test_stdout_and_stderr_sees_stderr_v2(self):
        """Test seeing both stderr and stdout when both are available (v2)."""
        # Write to stderr and stdout (swapped) and capture both
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);'
                'sys.stdout.write(s);')
        status, out = git.Git.execute(['python', '-c', code],
                                      # otherwise, same as above
                                      with_status=True,
                                      with_stderr=True,
                                      with_raw_output=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 * 2 + 2)

    def test_it_doesnt_deadlock(self):
        """Test that we don't deadlock with both stderr and stdout"""
        # 16k+1 bytes to exhaust any output buffers
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);'
                'sys.stdout.write(s);')
        out = git.Git.execute(['python', '-c', code])
        self.assertEqual(out, '\0' * (1024 * 16 + 1))

    def test_it_handles_interrupted_syscalls(self):
        """Test that we handle interrupted system calls"""
        # send ourselves a signal that causes EINTR
        prev_handler = signal.signal(signal.SIGALRM, lambda x,y: 1)
        signal.alarm(1)
        time.sleep(0.5)

        status, output = git.Git.execute(['sleep', '1'],
                                         with_status=True)
        self.assertEqual(status, 0)

        signal.signal(signal.SIGALRM, prev_handler)

if __name__ == '__main__':
    unittest.main()
