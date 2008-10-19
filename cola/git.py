# cmd.py
# Copyright (C) 2008 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

import os
import sys
import subprocess
from cola import utils
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

    def execute(self, command,
                istream=None,
                with_keep_cwd=False,
                with_extended_output=False,
                with_exceptions=True,
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
        if with_keep_cwd or not self._git_cwd:
          cwd = os.getcwd()
        else:
          cwd=self._git_cwd

        # Start the process
        if sys.platform == 'win32':
            command = utils.shell_quote(*command)

        proc = subprocess.Popen(command,
                                cwd=cwd,
                                shell=sys.platform == 'win32',
                                stdin=istream,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        # Wait for the process to return
        stdout_value, stderr_value = proc.communicate()
        if not stdout_value:
            stdout_value = ''
        if not stderr_value:
            stderr_value = ''
        status = proc.returncode

        # Strip off trailing whitespace by default
        if not with_raw_output:
            stdout_value = stdout_value.rstrip()
            stderr_value = stderr_value.rstrip()

        if with_exceptions and status:
            raise GitCommandError(command, status, stderr_value)

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
        _kwargs = {}
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

        return self.execute(call, **_kwargs)
