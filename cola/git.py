from __future__ import division, absolute_import, unicode_literals

import functools
import errno
import os
import sys
import subprocess
import threading
from os.path import join

from cola import core
from cola.compat import int_types
from cola.compat import ustr
from cola.decorators import memoize
from cola.interaction import Interaction


INDEX_LOCK = threading.Lock()
GIT_COLA_TRACE = core.getenv('GIT_COLA_TRACE', '')
STATUS = 0
STDOUT = 1
STDERR = 2


def dashify(s):
    return s.replace('_', '-')


def is_git_dir(git_dir):
    """From git's setup.c:is_git_directory()."""
    result = False
    if git_dir:
        headref = join(git_dir, 'HEAD')

        if (core.isdir(git_dir) and
                core.isdir(join(git_dir, 'objects')) and
                core.isdir(join(git_dir, 'refs'))):

            result = (core.isfile(headref) or
                      (core.islink(headref) and
                        core.readlink(headref).startswith('refs/')))
        else:
            result = is_git_file(git_dir)

    return result


def is_git_file(f):
    return core.isfile(f) and '.git' == os.path.basename(f)


def is_git_worktree(d):
    return is_git_dir(join(d, '.git'))


def read_git_file(path):
    """Read the path from a .git-file

    `None` is returned when <path> is not a .git-file.

    """
    result = None
    if path and is_git_file(path):
        header = 'gitdir: '
        data = core.read(path).strip()
        if data.startswith(header):
            result = data[len(header):]
    return result


class Paths(object):
    """Git repository paths of interest"""

    def __init__(self, git_dir=None, git_file=None, worktree=None):
        self.git_dir = git_dir
        self.git_file = git_file
        self.worktree = worktree


def find_git_directory(curpath):
    """Perform Git repository discovery

    """
    paths = Paths(git_dir=core.getenv('GIT_DIR'),
                  worktree=core.getenv('GIT_WORKTREE'),
                  git_file=None)

    ceiling_dirs = set()
    ceiling = core.getenv('GIT_CEILING_DIRECTORIES')
    if ceiling:
        ceiling_dirs.update([x for x in ceiling.split(':') if x])

    if not paths.git_dir or not paths.worktree:
        if curpath:
            curpath = core.abspath(curpath)

        # Search for a .git directory
        while curpath:
            if curpath in ceiling_dirs:
                break
            if is_git_dir(curpath):
                paths.git_dir = curpath
                if os.path.basename(curpath) == '.git':
                    paths.worktree = os.path.dirname(curpath)
                break
            gitpath = join(curpath, '.git')
            if is_git_dir(gitpath):
                paths.git_dir = gitpath
                paths.worktree = curpath
                break
            curpath, dummy = os.path.split(curpath)
            if not dummy:
                break

        git_dir_path = read_git_file(paths.git_dir)
        if git_dir_path:
            paths.git_file = paths.git_dir
            paths.git_dir = git_dir_path

    return paths


class Git(object):
    """
    The Git class manages communication with the Git binary
    """
    def __init__(self):
        self.paths = Paths()

        self._git_cwd = None  #: The working directory used by execute()
        self._valid = {}  #: Store the result of is_git_dir() for performance
        self.set_worktree(core.getcwd())

    def getcwd(self):
        return self._git_cwd

    def _find_git_directory(self, path):
        self._git_cwd = None
        self.paths = find_git_directory(path)

        # Update the current directory for executing commands
        if self.paths.worktree:
            self._git_cwd = self.paths.worktree
        elif self.paths.git_dir:
            self._git_cwd = self.paths.git_dir

    def set_worktree(self, path):
        path = core.decode(path)
        self._find_git_directory(path)
        return self.paths.worktree

    def worktree(self):
        if not self.paths.worktree:
            path = core.abspath(core.getcwd())
            self._find_git_directory(path)
        return self.paths.worktree

    def is_valid(self):
        """Is this a valid git repostiory?

        Cache the result to avoid hitting the filesystem.

        """
        git_dir = self.paths.git_dir
        try:
            valid = bool(git_dir) and self._valid[git_dir]
        except KeyError:
            valid = self._valid[git_dir] = is_git_dir(git_dir)

        return valid

    def git_path(self, *paths):
        if self.paths.git_dir:
            result = join(self.paths.git_dir, *paths)
        else:
            result = None
        return result

    def git_dir(self):
        if not self.paths.git_dir:
            path = core.abspath(core.getcwd())
            self._find_git_directory(path)
        return self.paths.git_dir

    def __getattr__(self, name):
        git_cmd = functools.partial(self.git, name)
        setattr(self, name, git_cmd)
        return git_cmd

    @staticmethod
    def execute(command,
                _cwd=None,
                _decode=True,
                _encoding=None,
                _raw=False,
                _stdin=None,
                _stderr=subprocess.PIPE,
                _stdout=subprocess.PIPE,
                _readonly=False):
        """
        Execute a command and returns its output

        :param command: argument list to execute.
        :param _cwd: working directory, defaults to the current directory.
        :param _decode: whether to decode output, defaults to True.
        :param _encoding: default encoding, defaults to None (utf-8).
        :param _raw: do not strip trailing whitespace.
        :param _stdin: optional stdin filehandle.
        :returns (status, out, err): exit status, stdout, stderr

        """
        # Allow the user to have the command executed in their working dir.
        if not _cwd:
            _cwd = core.getcwd()

        extra = {}
        if sys.platform == 'win32':
            # If git-cola is invoked on Windows using "start pythonw git-cola",
            # a console window will briefly flash on the screen each time
            # git-cola invokes git, which is very annoying.  The code below
            # prevents this by ensuring that any window will be hidden.
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            extra['startupinfo'] = startupinfo

        if hasattr(os, 'setsid'):
            # SSH uses the SSH_ASKPASS variable only if the process is really
            # detached from the TTY (stdin redirection and setting the
            # SSH_ASKPASS environment variable is not enough).  To detach a
            # process from the console it should fork and call os.setsid().
            extra['preexec_fn'] = os.setsid

        # Start the process
        # Guard against thread-unsafe .git/index.lock files
        if not _readonly:
            INDEX_LOCK.acquire()
        status, out, err = core.run_command(command,
                                            cwd=_cwd,
                                            encoding=_encoding,
                                            stdin=_stdin, stdout=_stdout, stderr=_stderr,
                                            **extra)
        # Let the next thread in
        if not _readonly:
            INDEX_LOCK.release()

        if not _raw and out is not None:
            out = out.rstrip('\n')

        cola_trace = GIT_COLA_TRACE
        if cola_trace == 'trace':
            msg = 'trace: ' + core.list2cmdline(command)
            Interaction.log_status(status, msg, '')
        elif cola_trace == 'full':
            if out or err:
                core.stderr("%s -> %d: '%s' '%s'" %
                            (' '.join(command), status, out, err))
            else:
                core.stderr("%s -> %d" % (' '.join(command), status))
        elif cola_trace:
            core.stderr(' '.join(command))

        # Allow access to the command's status code
        return (status, out, err)

    def transform_kwargs(self, **kwargs):
        """Transform kwargs into git command line options

        Callers can assume the following behavior:

        Passing foo=None ignores foo, so that callers can
        use default values of None that are ignored unless
        set explicitly.

        Passing foo=False ignore foo, for the same reason.

        Passing foo={string-or-number} results in ['--foo=<value>']
        in the resulting arguments.

        """
        args = []
        types_to_stringify = set((ustr, float, str) + int_types)

        for k, v in kwargs.items():
            if len(k) == 1:
                dashes = '-'
                join = ''
            else:
                dashes = '--'
                join = '='
            type_of_value = type(v)
            if v is True:
                args.append('%s%s' % (dashes, dashify(k)))
            elif type_of_value in types_to_stringify:
                args.append('%s%s%s%s' % (dashes, dashify(k), join, v))

        return args

    def git(self, cmd, *args, **kwargs):
        # Handle optional arguments prior to calling transform_kwargs
        # otherwise they'll end up in args, which is bad.
        _kwargs = dict(_cwd=self._git_cwd)
        execute_kwargs = (
                '_cwd',
                '_decode',
                '_encoding',
                '_stdin',
                '_stdout',
                '_stderr',
                '_raw',
                '_readonly',
                )
        for kwarg in execute_kwargs:
            if kwarg in kwargs:
                _kwargs[kwarg] = kwargs.pop(kwarg)

        # Prepare the argument list
        git_args = ['git', '-c', 'diff.suppressBlankEmpty=false', dashify(cmd)]
        opt_args = self.transform_kwargs(**kwargs)
        call = git_args + opt_args
        call.extend(args)
        try:
            return self.execute(call, **_kwargs)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise e
            core.stderr("error: unable to execute 'git'\n"
                        "error: please ensure that 'git' is in your $PATH")
            if sys.platform == 'win32':
                hint = ('\n'
                        'hint: If you have Git installed in a custom location, e.g.\n'
                        'hint: C:\\Tools\\Git, then you can create a file at\n'
                        'hint: ~/.config/git-cola/git-bindir with the following text\n'
                        'hint: and git-cola will add the specified location to your $PATH\n'
                        'hint: automatically when starting cola:\n'
                        'hint:\n'
                        'hint: C:\\Tools\\Git\\bin\n')
                core.stderr(hint)
            sys.exit(1)


@memoize
def current():
    """Return the Git singleton"""
    return Git()


git = current()
"""
Git command singleton

>>> from cola.git import git
>>> from cola.git import STDOUT
>>> 'git' == git.version()[STDOUT][:3].lower()
True

"""
