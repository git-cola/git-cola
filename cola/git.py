# cmd.py
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

import re
import os
import sys
import errno
import subprocess

from cola import core
from cola import errors


def dashify(string):
    return string.replace('_', '-')

# Enables debugging of GitPython's git commands
GIT_PYTHON_TRACE = os.environ.get("GIT_PYTHON_TRACE", False)

execute_kwargs = ('cwd',
                  'istream',
                  'with_exceptions',
                  'with_raw_output',
                  'with_status',
                  'with_stderr')

extra = {}
if sys.platform == 'win32':
    extra = {'shell': True}

class Git(object):
    """
    The Git class manages communication with the Git binary
    """
    def __init__(self):
        self._git_cwd = None #: The working directory used by execute()

    def set_cwd(self, path):
        """Sets the current directory."""
        self._git_cwd = path

    def __getattr__(self, name):
        if name[:1] == '_':
            raise AttributeError(name)
        return lambda *args, **kwargs: self._call_process(name, *args, **kwargs)

    @staticmethod
    def execute(command,
                cwd=None,
                istream=None,
                with_exceptions=False,
                with_raw_output=False,
                with_status=False,
                with_stderr=False):
        """
        Execute a command and returns its output

        ``command``
            The command argument list to execute

        ``istream``
            Readable filehandle passed to subprocess.Popen.

        ``cwd``
            The working directory when running commands.
            Default: os.getcwd()

        ``with_status``
            Whether to return a (status, unicode(output)) tuple.

        ``with_stderr``
            Whether to include stderr in the output stream

        ``with_exceptions``
            Whether to raise an exception when git returns a non-zero status.

        ``with_raw_output``
            Whether to avoid stripping off trailing whitespace.

        Returns
            unicode(stdout)                     # Default
            unicode(stdout+stderr)              # with_stderr=True
            tuple(int(status), unicode(output)) # with_status=True

        """

        if GIT_PYTHON_TRACE and not GIT_PYTHON_TRACE == 'full':
            print ' '.join(command)

        # Allow the user to have the command executed in their working dir.
        if not cwd:
            cwd = os.getcwd()

        if with_stderr:
            stderr = subprocess.STDOUT
        else:
            stderr = None

        if sys.platform == 'win32':
            command = map(replace_carot, command)

        # Start the process
        while True:
            try:
                proc = subprocess.Popen(command,
                                        cwd=cwd,
                                        stdin=istream,
                                        stderr=stderr,
                                        stdout=subprocess.PIPE,
                                        **extra)
                break
            except OSError, e:
                # Some systems interrupt system calls and throw OSError
                if e.errno == errno.EINTR:
                    continue
                raise e

        # Wait for the process to return
        output = core.read_nointr(proc.stdout)
        proc.stdout.close()
        status = core.wait_nointr(proc)

        if with_exceptions and status != 0:
            raise errors.GitCommandError(command, status, output)

        if not with_raw_output:
            output = output.rstrip()

        if GIT_PYTHON_TRACE == 'full':
            if output:
                print "%s -> %d: '%s'" % (command, status, output)
            else:
                print "%s -> %d" % (command, status)

        # Allow access to the command's status code
        if with_status:
            return (status, output)
        else:
            return output

    def transform_kwargs(self, **kwargs):
        """
        Transforms Python style kwargs into git command line options.
        """
        args = []
        for k, v in kwargs.items():
            if len(k) == 1:
                if v is True:
                    args.append("-%s" % k)
                elif type(v) is not bool:
                    args.append("-%s%s" % (k, v))
            else:
                if v is True:
                    args.append("--%s" % dashify(k))
                elif type(v) is not bool:
                    args.append("--%s=%s" % (dashify(k), v))
        return args

    def _call_process(self, method, *args, **kwargs):
        """
        Run the given git command with the specified arguments and return
        the result as a String

        ``method``
            is the command

        ``args``
            is the list of arguments

        ``kwargs``
            is a dict of keyword arguments.
            This function accepts the same optional keyword arguments
            as execute().

        Examples
            git.rev_list('master', max_count=10, header=True)

        Returns
            Same as execute()
        """

        # Handle optional arguments prior to calling transform_kwargs
        # otherwise they'll end up in args, which is bad.
        _kwargs = dict(cwd=self._git_cwd)
        for kwarg in execute_kwargs:
            if kwarg in kwargs:
                _kwargs[kwarg] = kwargs.pop(kwarg)

        # Prepare the argument list
        opt_args = self.transform_kwargs(**kwargs)
        ext_args = map(core.encode, args)
        args = opt_args + ext_args

        call = ['git', dashify(method)]
        call.extend(args)

        return self.execute(call, **_kwargs)


def replace_carot(cmd_arg):
    """
    Guard against the windows command shell.

    In the Windows shell, a carat character (^) may be used for
    line continuation.  To guard against this, escape the carat
    by using two of them.

    http://technet.microsoft.com/en-us/library/cc723564.aspx

    """
    return cmd_arg.replace('^', '^^')


def shell_quote(*strings):
    """
    Quote strings so that they can be suitably martialled
    off to the shell.  This method supports POSIX sh syntax.
    This is crucial to properly handle command line arguments
    with spaces, quotes, double-quotes, etc. on darwin/win32...
    """

    regex = re.compile('[^\w!%+,\-./:@^]')
    quote_regex = re.compile("((?:'\\''){2,})")

    ret = []
    for s in strings:
        if not s:
            continue

        if '\x00' in s:
            raise ValueError('No way to quote strings '
                             'containing null(\\000) bytes')

        # = does need quoting else in command position it's a
        # program-local environment setting
        match = regex.search(s)
        if match and '=' not in s:
            # ' -> '\''
            s = s.replace("'", "'\\''")

            # make multiple ' in a row look simpler
            # '\'''\'''\'' -> '"'''"'
            quote_match = quote_regex.match(s)
            if quote_match:
                quotes = match.group(1)
                s.replace(quotes, ("'" *(len(quotes)/4)) + "\"'")

            s = "'%s'" % s
            if s.startswith("''"):
                s = s[2:]

            if s.endswith("''"):
                s = s[:-2]
        ret.append(s)
    return ' '.join(ret)
