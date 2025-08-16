from functools import partial
import errno
import os
from os.path import join
import subprocess
import threading
import time

from . import core
from .compat import int_types
from .compat import ustr
from .compat import WIN32
from .decorators import memoize
from .interaction import Interaction


GIT_COLA_TRACE = core.getenv('GIT_COLA_TRACE', '')
GIT = core.getenv('GIT_COLA_GIT', 'git')
STATUS = 0
STDOUT = 1
STDERR = 2

# Git's empty tree is a built-in constant object name.
# These two constants correspond to `git hash-object -t tree /dev/null`
# for sha256 and sha1 repositories.
EMPTY_TREE_SHA1 = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
EMPTY_TREE_SHA256 = '6ef19b41225c5369f1c104d45d8d85efa9b057b53b14b4b9b939dd74decc5321'

# Git's diff machinery returns zeroes for modified files whose content exists
# in the worktree only.
MISSING_BLOB_SHA1 = '0000000000000000000000000000000000000000'
MISSING_BLOB_SHA256 = '0000000000000000000000000000000000000000000000000000000000000000'

# Git's SHA-1 object IDs are 40 characters long (20 bytes).
# Git's SHA-256 object IDs are 64 characters long (32 bytes).
OID_LENGTH_SHA1 = 40
OID_LENGTH_SHA256 = 64

_index_lock = threading.Lock()


def dashify(value):
    return value.replace('_', '-')


def is_git_dir(git_dir):
    """From git's setup.c:is_git_directory()."""
    result = False
    if git_dir:
        headref = join(git_dir, 'HEAD')

        if (
            core.isdir(git_dir)
            and (
                core.isdir(join(git_dir, 'objects'))
                and core.isdir(join(git_dir, 'refs'))
            )
            or (
                core.isfile(join(git_dir, 'gitdir'))
                and core.isfile(join(git_dir, 'commondir'))
            )
        ):
            result = core.isfile(headref) or (
                core.islink(headref) and core.readlink(headref).startswith('refs/')
            )
        else:
            result = is_git_file(git_dir)

    return result


def is_git_file(filename):
    return core.isfile(filename) and os.path.basename(filename) == '.git'


def is_git_worktree(dirname):
    return is_git_dir(join(dirname, '.git'))


def is_git_repository(path):
    return is_git_worktree(path) or is_git_dir(path)


def read_git_file(path):
    """Read the path from a .git-file

    `None` is returned when <path> is not a .git-file.

    """
    result = None
    if path and is_git_file(path):
        header = 'gitdir: '
        data = core.read(path).strip()
        if data.startswith(header):
            result = data[len(header) :]
            if result and not os.path.isabs(result):
                path_folder = os.path.dirname(path)
                repo_relative = join(path_folder, result)
                result = os.path.normpath(repo_relative)
    return result


class Paths:
    """Git repository paths of interest"""

    def __init__(self, git_dir=None, git_file=None, worktree=None, common_dir=None):
        if git_dir and not is_git_dir(git_dir):
            git_dir = None
        self.git_dir = git_dir
        self.git_file = git_file
        self.worktree = worktree
        self.common_dir = common_dir

    def get(self, path):
        """Search for git worktrees and bare repositories"""
        if not self.git_dir or not self.worktree:
            ceiling_dirs = set()
            ceiling = core.getenv('GIT_CEILING_DIRECTORIES')
            if ceiling:
                ceiling_dirs.update([x for x in ceiling.split(os.pathsep) if x])
            if path:
                path = core.abspath(path)
            self._search_for_git(path, ceiling_dirs)

        if self.git_dir:
            git_dir_path = read_git_file(self.git_dir)
            if git_dir_path:
                self.git_file = self.git_dir
                self.git_dir = git_dir_path

                commondir_file = join(git_dir_path, 'commondir')
                if core.exists(commondir_file):
                    common_path = core.read(commondir_file).strip()
                    if common_path:
                        if os.path.isabs(common_path):
                            common_dir = common_path
                        else:
                            common_dir = join(git_dir_path, common_path)
                            common_dir = os.path.normpath(common_dir)
                        self.common_dir = common_dir
        # usage: Paths().get()
        return self

    def _search_for_git(self, path, ceiling_dirs):
        """Search for git repositories located at path or above"""
        while path:
            if path in ceiling_dirs:
                break
            if is_git_dir(path):
                if not self.git_dir:
                    self.git_dir = path
                basename = os.path.basename(path)
                if not self.worktree and basename == '.git':
                    self.worktree = os.path.dirname(path)
            # We are either in a bare repository, or someone set GIT_DIR
            # but did not set GIT_WORK_TREE.
            if self.git_dir:
                if not self.worktree:
                    basename = os.path.basename(self.git_dir)
                    if basename == '.git':
                        self.worktree = os.path.dirname(self.git_dir)
                    elif path and not is_git_dir(path):
                        self.worktree = path
                break
            gitpath = join(path, '.git')
            if is_git_dir(gitpath):
                if not self.git_dir:
                    self.git_dir = gitpath
                if not self.worktree:
                    self.worktree = path
                break
            path, dummy = os.path.split(path)
            if not dummy:
                break


def find_git_directory(path):
    """Perform Git repository discovery"""
    return Paths(
        git_dir=core.getenv('GIT_DIR'), worktree=core.getenv('GIT_WORK_TREE')
    ).get(path)


class Git:
    """
    The Git class manages communication with the Git binary
    """

    def __init__(self, worktree=None):
        self.paths = Paths()

        self._valid = {}  #: Store the result of is_git_dir() for performance
        self.set_worktree(worktree or core.getcwd())

    def is_git_repository(self, path):
        return is_git_repository(path)

    def getcwd(self):
        """Return the working directory used by git()"""
        return self.paths.worktree or self.paths.git_dir

    def set_worktree(self, path):
        path = core.decode(path)
        self.paths = find_git_directory(path)
        return self.paths.worktree

    def worktree(self):
        if not self.paths.worktree:
            path = core.abspath(core.getcwd())
            self.paths = find_git_directory(path)
        return self.paths.worktree

    def is_valid(self):
        """Is this a valid git repository?

        Cache the result to avoid hitting the filesystem.

        """
        git_dir = self.paths.git_dir
        try:
            valid = bool(git_dir) and self._valid[git_dir]
        except KeyError:
            valid = self._valid[git_dir] = is_git_dir(git_dir)

        return valid

    def git_path(self, *paths):
        result = None
        if self.paths.git_dir:
            result = join(self.paths.git_dir, *paths)
        if result and self.paths.common_dir and not core.exists(result):
            common_result = join(self.paths.common_dir, *paths)
            if core.exists(common_result):
                result = common_result
        return result

    def git_dir(self):
        if not self.paths.git_dir:
            path = core.abspath(core.getcwd())
            self.paths = find_git_directory(path)
        return self.paths.git_dir

    def __getattr__(self, name):
        git_cmd = partial(self.git, name)
        setattr(self, name, git_cmd)
        return git_cmd

    @staticmethod
    def execute(
        command,
        _add_env=None,
        _cwd=None,
        _decode=True,
        _encoding=None,
        _raw=False,
        _stdin=None,
        _stderr=subprocess.PIPE,
        _stdout=subprocess.PIPE,
        _readonly=False,
        _no_win32_startupinfo=False,
    ):
        """
        Execute a command and returns its output

        :param command: argument list to execute.
        :param _cwd: working directory, defaults to the current directory.
        :param _decode: whether to decode output, defaults to True.
        :param _encoding: default encoding, defaults to None (utf-8).
        :param _readonly: avoid taking the index lock. Assume the command is read-only.
        :param _raw: do not strip trailing whitespace.
        :param _stdin: optional stdin filehandle.
        :returns (status, out, err): exit status, stdout, stderr

        """
        # Allow the user to have the command executed in their working dir.
        if not _cwd:
            _cwd = core.getcwd()

        extra = {}

        if hasattr(os, 'setsid'):
            # SSH uses the SSH_ASKPASS variable only if the process is really
            # detached from the TTY (stdin redirection and setting the
            # SSH_ASKPASS environment variable is not enough).  To detach a
            # process from the console it should fork and call os.setsid().
            extra['preexec_fn'] = os.setsid

        start_time = time.time()

        # Start the process
        # Guard against thread-unsafe .git/index.lock files
        if not _readonly:
            _index_lock.acquire()
        try:
            status, out, err = core.run_command(
                command,
                add_env=_add_env,
                cwd=_cwd,
                encoding=_encoding,
                stdin=_stdin,
                stdout=_stdout,
                stderr=_stderr,
                no_win32_startupinfo=_no_win32_startupinfo,
                **extra,
            )
        finally:
            # Let the next thread in
            if not _readonly:
                _index_lock.release()

        end_time = time.time()
        elapsed_time = abs(end_time - start_time)

        if not _raw and out is not None:
            out = core.UStr(out.rstrip('\n'), out.encoding)

        cola_trace = GIT_COLA_TRACE
        if cola_trace == 'trace':
            msg = f'trace: {elapsed_time:.3f}s: {core.list2cmdline(command)}'
            Interaction.log_status(status, msg, '')
        elif cola_trace == 'full':
            if out or err:
                core.print_stderr(
                    "# %.3fs: %s -> %d: '%s' '%s'"
                    % (elapsed_time, ' '.join(command), status, out, err)
                )
            else:
                core.print_stderr(
                    '# %.3fs: %s -> %d' % (elapsed_time, ' '.join(command), status)
                )
        elif cola_trace:
            core.print_stderr('# {:.3f}s: {}'.format(elapsed_time, ' '.join(command)))

        # Allow access to the command's status code
        return (status, out, err)

    def git(self, cmd, *args, **kwargs):
        # Handle optional arguments prior to calling transform_kwargs
        # otherwise they'll end up in args, which is bad.
        _kwargs = {'_cwd': self.getcwd()}
        execute_kwargs = (
            '_add_env',
            '_cwd',
            '_decode',
            '_encoding',
            '_stdin',
            '_stdout',
            '_stderr',
            '_raw',
            '_readonly',
            '_no_win32_startupinfo',
        )

        for kwarg in execute_kwargs:
            if kwarg in kwargs:
                _kwargs[kwarg] = kwargs.pop(kwarg)

        # Prepare the argument list
        git_args = [
            GIT,
            '-c',
            'diff.suppressBlankEmpty=false',
            '-c',
            'diff.autoRefreshIndex=false',
            '-c',
            'log.showSignature=false',
            dashify(cmd),
        ]
        opt_args = transform_kwargs(**kwargs)
        call = git_args + opt_args
        call.extend(args)
        try:
            result = self.execute(call, **_kwargs)
        except OSError as exc:
            if WIN32 and exc.errno == errno.ENOENT:
                # see if git exists at all. On win32 it can fail with ENOENT in
                # case of argv overflow. We should be safe from that but use
                # defensive coding for the worst-case scenario. On UNIX
                # we have ENAMETOOLONG but that doesn't exist on Windows.
                if _git_is_installed():
                    raise exc
                _print_win32_git_hint()
            result = (1, '', "error: unable to execute '%s'" % GIT)
        return result


def _git_is_installed():
    """Return True if git is installed"""
    # On win32 Git commands can fail with ENOENT in case of argv overflow. We
    # should be safe from that but use defensive coding for the worst-case
    # scenario. On UNIX we have ENAMETOOLONG but that doesn't exist on
    # Windows.
    try:
        status, _, _ = Git.execute([GIT, '--version'])
        result = status == 0
    except OSError:
        result = False
    return result


def transform_kwargs(**kwargs):
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
    types_to_stringify = (ustr, float, str) + int_types

    for k, value in kwargs.items():
        if len(k) == 1:
            dashes = '-'
            equals = ''
        else:
            dashes = '--'
            equals = '='
        # isinstance(False, int) is True, so we have to check bool first
        if isinstance(value, bool):
            if value:
                args.append(f'{dashes}{dashify(k)}')
            # else: pass  # False is ignored; flag=False inhibits --flag
        elif isinstance(value, types_to_stringify):
            args.append(f'{dashes}{dashify(k)}{equals}{value}')

    return args


def win32_git_error_hint():
    return (
        '\n'
        'NOTE: If you have Git installed in a custom location, e.g.\n'
        'C:\\Tools\\Git, then you can create a file at\n'
        '~/.config/git-cola/git-bindir with following text\n'
        'and git-cola will add the specified location to your $PATH\n'
        'automatically when starting cola:\n'
        '\n'
        r'C:\Tools\Git\bin'
    )


@memoize
def _print_win32_git_hint():
    hint = '\n' + win32_git_error_hint() + '\n'
    core.print_stderr("error: unable to execute 'git'" + hint)


def create():
    """Create Git instances

    >>> git = create()
    >>> status, out, err = git.version()
    >>> 'git' == out[:3].lower()
    True

    """
    return Git()
