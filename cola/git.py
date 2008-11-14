# cmd.py
# Copyright (C) 2008 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php
import re
import os
import sys
import subprocess
import errno
from cola.exception import GitCommandError

def dashify(string):
    return string.replace('_', '-')

# Enables debugging of GitPython's git commands
GIT_PYTHON_TRACE = os.environ.get("GIT_PYTHON_TRACE", False)

execute_kwargs = ('istream', 'with_keep_cwd', 'with_extended_output',
                  'with_exceptions', 'with_raw_output')

class Git(object):
    """
    The Git class manages communication with the Git binary
    """
    def __init__(self):
        self._git_cwd = None

    def set_cwd(self, path):
        self._git_cwd = path

    def __getattr__(self, name):
        if name[0] == '_':
            raise AttributeError(name)
        return lambda *args, **kwargs: self._call_process(name, *args, **kwargs)

    @staticmethod
    def execute(command,
                cwd=None,
                istream=None,
                with_keep_cwd=False,
                with_extended_output=False,
                with_exceptions=False,
                with_raw_output=False):
        """
        Handles executing the command on the shell and consumes and returns
        the returned information (stdout)

        ``command``
            The command argument list to execute

        ``istream``
            Standard input filehandle passed to subprocess.Popen.

        ``with_keep_cwd``
            Whether to use the current working directory from os.getcwd().
            GitPython uses the cwd set by set_cwd() by default.

        ``with_extended_output``
            Whether to return a (status, stdout, stderr) tuple.

        ``with_exceptions``
            Whether to raise an exception when git returns a non-zero status.

        ``with_raw_output``
            Whether to avoid stripping off trailing whitespace.

        Returns
            str(output)                     # extended_output = False (Default)
            tuple(int(status), str(output)) # extended_output = True
        """

        if GIT_PYTHON_TRACE and not GIT_PYTHON_TRACE == 'full':
            print ' '.join(command)

        # Allow the user to have the command executed in their working dir.
        if with_keep_cwd or not cwd:
          cwd = os.getcwd()

        # Start the process
        use_shell = sys.platform in ('win32')
        if use_shell and sys.platform == 'darwin':
            command = shell_quote(*command)
        proc = subprocess.Popen(command,
                                cwd=cwd,
                                shell=use_shell,
                                stdin=istream,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        while True:
            try:
                stdout_value = proc.stdout.read()
                stderr_value = proc.stderr.read()
                status = proc.wait()
                break
            except IOError, e:
                # OSX and others are known to interrupt system calls
                # http://en.wikipedia.org/wiki/PCLSRing
                # http://en.wikipedia.org/wiki/Unix_philosophy#Worse_is_better
                if e.errno == errno.EINTR:
                    continue
                else:
                    stdout_value = None
                    stderr_value = None
                    status = 42
                    break

        if with_exceptions and status:
            raise GitCommandError(command, status, stderr_value)

        if not stdout_value:
            stdout_value = ''
        if not stderr_value:
            stderr_value = ''
        if not with_raw_output:
            stdout_value = stdout_value.strip()
            stderr_value = stderr_value.strip()

        if GIT_PYTHON_TRACE == 'full':
            if stderr_value:
              print "%s -> %d: '%s' !! '%s'" % (command, status, stdout_value, stderr_value)
            elif stdout_value:
              print "%s -> %d: '%s'" % (command, status, stdout_value)
            else:
              print "%s -> %d" % (command, status)

        # Allow access to the command's status code
        if with_extended_output:
            return (status, stdout_value, stderr_value)
        else:
            if stdout_value and stderr_value:
                return stderr_value + '\n' + stdout_value
            elif stdout_value:
                return stdout_value
            else:
                return stderr_value

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
        # otherwise these'll end up in args, which is bad.
        _kwargs = dict(cwd=self._git_cwd)
        for kwarg in execute_kwargs:
            try:
                _kwargs[kwarg] = kwargs.pop(kwarg)
            except KeyError:
                pass

        # Prepare the argument list
        opt_args = self.transform_kwargs(**kwargs)
        ext_args = [a.encode('utf-8') for a in args]
        args = opt_args + ext_args

        call = ['git', dashify(method)]
        call.extend(args)

        return Git.execute(call, **_kwargs)


def shell_quote(*inputs):
    """
    Quote strings so that they can be suitably martialled
    off to the shell.  This method supports POSIX sh syntax.
    This is crucial to properly handle command line arguments
    with spaces, quotes, double-quotes, etc. on darwin/win32...
    """

    regex = re.compile('[^\w!%+,\-./:@^]')
    quote_regex = re.compile("((?:'\\''){2,})")

    ret = []
    for input in inputs:
        if not input:
            continue

        if '\x00' in input:
            raise AssertionError,('No way to quote strings '
                                  'containing null(\\000) bytes')

        # = does need quoting else in command position it's a
        # program-local environment setting
        match = regex.search(input)
        if match and '=' not in input:
            # ' -> '\''
            input = input.replace("'", "'\\''")

            # make multiple ' in a row look simpler
            # '\'''\'''\'' -> '"'''"'
            quote_match = quote_regex.match(input)
            if quote_match:
                quotes = match.group(1)
                input.replace(quotes, ("'" *(len(quotes)/4)) + "\"'")

            input = "'%s'" % input
            if input.startswith("''"):
                input = input[2:]

            if input.endswith("''"):
                input = input[:-2]
        ret.append(input)
    return ' '.join(ret)

