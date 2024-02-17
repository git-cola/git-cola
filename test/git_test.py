"""Test the cola.git module"""
import os
import pathlib

from cola import git
from cola.git import STDOUT

from .helper import patch


# 16k+1 bytes to exhaust any output buffers.
BUFFER_SIZE = (16 * 1024) + 1


@patch('cola.git.is_git_dir')
def test_find_git_dir_None(is_git_dir):
    paths = git.find_git_directory(None)

    assert not is_git_dir.called
    assert paths.git_dir is None
    assert paths.git_file is None
    assert paths.worktree is None


@patch('cola.git.is_git_dir')
def test_find_git_dir_empty_string(is_git_dir):
    paths = git.find_git_directory('')

    assert not is_git_dir.called
    assert paths.git_dir is None
    assert paths.git_file is None
    assert paths.worktree is None


@patch('cola.git.is_git_dir')
def test_find_git_dir_never_found(is_git_dir):
    is_git_dir.return_value = False

    paths = git.find_git_directory(str(pathlib.Path('/does/not/exist').resolve()))

    assert is_git_dir.called
    assert paths.git_dir is None
    assert paths.git_file is None
    assert paths.worktree is None

    expect = 8
    actual = is_git_dir.call_count
    assert expect == actual
    is_git_dir.assert_has_calls([
        ((str(pathlib.Path('/does/not/exist').resolve()),), {}),
        ((str(pathlib.Path('/does/not/exist/.git').resolve()),), {}),
        ((str(pathlib.Path('/does/not').resolve()),), {}),
        ((str(pathlib.Path('/does/not/.git').resolve()),), {}),
        ((str(pathlib.Path('/does').resolve()),), {}),
        ((str(pathlib.Path('/does/.git').resolve()),), {}),
        ((str(pathlib.Path('/').resolve()),), {}),
        ((str(pathlib.Path('/.git').resolve()),), {}),
    ])


@patch('cola.git.is_git_dir')
def test_find_git_dir_found_right_away(is_git_dir):
    git_dir = str(pathlib.Path('/seems/to/exist/.git').resolve())
    worktree = str(pathlib.Path('/seems/to/exist').resolve())
    is_git_dir.return_value = True

    paths = git.find_git_directory(git_dir)

    assert is_git_dir.called
    assert git_dir == paths.git_dir
    assert paths.git_file is None
    assert worktree == paths.worktree


@patch('cola.git.is_git_dir')
def test_find_git_does_discovery(is_git_dir):
    git_dir = str(pathlib.Path('/the/root/.git').resolve())
    worktree = str(pathlib.Path('/the/root').resolve())
    is_git_dir.side_effect = lambda x: x == git_dir

    paths = git.find_git_directory('/the/root/sub/dir')

    assert git_dir == paths.git_dir
    assert paths.git_file is None
    assert worktree == paths.worktree


@patch('cola.git.read_git_file')
@patch('cola.git.is_git_file')
@patch('cola.git.is_git_dir')
def test_find_git_honors_git_files(is_git_dir, is_git_file, read_git_file):
    git_file = str(pathlib.Path('/the/root/.git').resolve())
    worktree = str(pathlib.Path('/the/root').resolve())
    git_dir = str(pathlib.Path('/super/module/.git/modules/root').resolve())

    is_git_dir.side_effect = lambda x: x == git_file
    is_git_file.side_effect = lambda x: x == git_file
    read_git_file.return_value = git_dir

    paths = git.find_git_directory(str(pathlib.Path('/the/root/sub/dir').resolve()))

    assert git_dir == paths.git_dir
    assert git_file == paths.git_file
    assert worktree == paths.worktree

    expect = 6
    actual = is_git_dir.call_count
    assert expect == actual
    is_git_dir.assert_has_calls([
        ((str(pathlib.Path('/the/root/sub/dir').resolve()),), {}),
        ((str(pathlib.Path('/the/root/sub/dir/.git').resolve()),), {}),
        ((str(pathlib.Path('/the/root/sub').resolve()),), {}),
        ((str(pathlib.Path('/the/root/sub/.git').resolve()),), {}),
        ((str(pathlib.Path('/the/root').resolve()),), {}),
        ((str(pathlib.Path('/the/root/.git').resolve()),), {}),
    ])
    read_git_file.assert_called_once_with(git_file)


@patch('cola.core.getenv')
@patch('cola.git.is_git_dir')
def test_find_git_honors_ceiling_dirs(is_git_dir, getenv):
    git_dir = str(pathlib.Path('/ceiling/.git').resolve())
    ceiling = os.pathsep.join(
        str(pathlib.Path(path).resolve())
        for path in ('/tmp', '/ceiling', '/other/ceiling')
    )
    is_git_dir.side_effect = lambda x: x == git_dir

    def mock_getenv(k, v=None):
        if k == 'GIT_CEILING_DIRECTORIES':
            return ceiling
        return v

    getenv.side_effect = mock_getenv
    paths = git.find_git_directory(str(pathlib.Path('/ceiling/sub/dir').resolve()))

    assert paths.git_dir is None
    assert paths.git_file is None
    assert paths.worktree is None
    assert is_git_dir.call_count == 4
    is_git_dir.assert_has_calls([
        ((str(pathlib.Path('/ceiling/sub/dir').resolve()),), {}),
        ((str(pathlib.Path('/ceiling/sub/dir/.git').resolve()),), {}),
        ((str(pathlib.Path('/ceiling/sub').resolve()),), {}),
        ((str(pathlib.Path('/ceiling/sub/.git').resolve()),), {}),
    ])


@patch('cola.core.islink')
@patch('cola.core.isdir')
@patch('cola.core.isfile')
def test_is_git_dir_finds_linked_repository(isfile, isdir, islink):
    dirs = {
        str(pathlib.Path(directory).resolve())
        for directory in [
            '/foo',
            '/foo/.git',
            '/foo/.git/refs',
            '/foo/.git/objects',
            '/foo/.git/worktrees',
            '/foo/.git/worktrees/foo',
        ]
    }
    files = {
        str(pathlib.Path(file).resolve())
        for file in [
            '/foo/.git/HEAD',
            '/foo/.git/worktrees/foo/HEAD',
            '/foo/.git/worktrees/foo/index',
            '/foo/.git/worktrees/foo/commondir',
            '/foo/.git/worktrees/foo/gitdir',
        ]
    }
    islink.return_value = False
    isfile.side_effect = lambda x: x in files
    isdir.side_effect = lambda x: x in dirs

    assert git.is_git_dir(str(pathlib.Path('/foo/.git/worktrees/foo').resolve()))
    assert git.is_git_dir(str(pathlib.Path('/foo/.git').resolve()))


@patch('cola.core.getenv')
@patch('cola.git.is_git_dir')
def test_find_git_worktree_from_GIT_DIR(is_git_dir, getenv):
    git_dir = str(pathlib.Path('/repo/.git').resolve())
    worktree = str(pathlib.Path('/repo').resolve())
    is_git_dir.return_value = True
    getenv.side_effect = lambda x: x == 'GIT_DIR' and git_dir or None

    paths = git.find_git_directory(git_dir)
    assert is_git_dir.called
    assert git_dir == paths.git_dir
    assert paths.git_file is None
    assert worktree == paths.worktree


@patch('cola.git.is_git_dir')
def test_finds_no_worktree_from_bare_repo(is_git_dir):
    git_dir = str(pathlib.Path('/repos/bare.git').resolve())
    worktree = None
    is_git_dir.return_value = True

    paths = git.find_git_directory(git_dir)
    assert is_git_dir.called
    assert git_dir == paths.git_dir
    assert paths.git_file is None
    assert worktree == paths.worktree


@patch('cola.core.getenv')
@patch('cola.git.is_git_dir')
def test_find_git_directory_uses_GIT_WORK_TREE(is_git_dir, getenv):
    git_dir = str(pathlib.Path('/repo/worktree/.git').resolve())
    worktree = str(pathlib.Path('/repo/worktree').resolve())

    def is_git_dir_func(path):
        return path == git_dir

    is_git_dir.side_effect = is_git_dir_func

    def getenv_func(name):
        if name == 'GIT_WORK_TREE':
            return worktree
        return None

    getenv.side_effect = getenv_func

    paths = git.find_git_directory(worktree)
    assert is_git_dir.called
    assert git_dir == paths.git_dir
    assert paths.git_file is None
    assert worktree == paths.worktree


@patch('cola.core.getenv')
@patch('cola.git.is_git_dir')
def test_uses_cwd_for_worktree_with_GIT_DIR(is_git_dir, getenv):
    git_dir = str(pathlib.Path('/repo/.yadm/repo.git').resolve())
    worktree = str(pathlib.Path('/repo').resolve())

    def getenv_func(name):
        if name == 'GIT_DIR':
            return git_dir
        return None

    getenv.side_effect = getenv_func

    def is_git_dir_func(path):
        return path == git_dir

    is_git_dir.side_effect = is_git_dir_func

    paths = git.find_git_directory(worktree)
    assert is_git_dir.called
    assert getenv.called
    assert git_dir == paths.git_dir
    assert paths.git_file is None
    assert worktree == paths.worktree


def test_transform_kwargs_empty():
    expect = []
    actual = git.transform_kwargs(foo=None, bar=False)
    assert expect == actual


def test_transform_kwargs_single_dash_from_True():
    """Single dash for one-character True"""
    expect = ['-a']
    actual = git.transform_kwargs(a=True)
    assert expect == actual


def test_transform_kwargs_no_single_dash_from_False():
    """No single-dash for False"""
    expect = []
    actual = git.transform_kwargs(a=False)
    assert expect == actual


def test_transform_kwargs_double_dash_from_True():
    """Double-dash for longer True"""
    expect = ['--abc']
    actual = git.transform_kwargs(abc=True)
    assert expect == actual


def test_transform_kwargs_no_double_dash_from_True():
    """No double-dash for False"""
    expect = []
    actual = git.transform_kwargs(abc=False)
    assert expect == actual


def test_transform_kwargs_single_dash_int():
    expect = ['-a1']
    actual = git.transform_kwargs(a=1)
    assert expect == actual


def test_transform_kwargs_double_dash_int():
    expect = ['--abc=1']
    actual = git.transform_kwargs(abc=1)
    assert expect == actual


def test_transform_kwargs_single_dash_float():
    expect = ['-a1.5']
    actual = git.transform_kwargs(a=1.5)
    assert expect == actual


def test_transform_kwargs_double_dash_float():
    expect = ['--abc=1.5']
    actual = git.transform_kwargs(abc=1.5)
    assert expect == actual


def test_transform_kwargs_single_dash_string():
    expect = ['-abc']
    actual = git.transform_kwargs(a='bc')
    assert expect == actual


def test_transform_double_single_dash_string():
    expect = ['--abc=def']
    actual = git.transform_kwargs(abc='def')
    assert expect == actual


def test_version():
    """Test running 'git version'"""
    gitcmd = git.Git()
    version = gitcmd.version()[STDOUT]
    assert version.startswith('git version')


def test_stdout():
    """Test overflowing the stdout buffer"""
    # Write to stdout only
    code = r'import sys; value = "\0" * %d; sys.stdout.write(value);' % BUFFER_SIZE
    status, out, err = git.Git.execute(['python', '-c', code], _raw=True)

    assert status == 0
    expect = BUFFER_SIZE
    actual = len(out)
    assert expect == actual

    expect = 0
    actual = len(err)
    assert expect == actual


def test_stderr():
    """Test that stderr is seen"""
    # Write to stderr and capture it
    code = (
        r'import sys;' r'value = "\0" * %d;' r'sys.stderr.write(value);'
    ) % BUFFER_SIZE

    status, out, err = git.Git.execute(['python', '-c', code], _raw=True)

    expect = 0
    actual = status
    assert expect == actual

    expect = 0
    actual = len(out)
    assert expect == actual

    expect = BUFFER_SIZE
    actual = len(err)
    assert expect == actual


def test_stdout_and_stderr():
    """Test ignoring stderr when stdout+stderr are provided (v2)"""
    # Write to stdout and stderr but only capture stdout
    code = (
        r'import sys;'
        r'value = "\0" * %d;'
        r'sys.stdout.write(value);'
        r'sys.stderr.write(value);'
    ) % BUFFER_SIZE

    status, out, err = git.Git.execute(['python', '-c', code], _raw=True)

    expect = 0
    actual = status
    assert expect == actual

    expect = BUFFER_SIZE
    actual = len(out)
    assert expect == actual

    actual = len(err)
    assert expect == actual


def test_it_doesnt_deadlock():
    """Test that we don't deadlock with both stderr and stdout"""
    code = (
        r'import sys;'
        r'value = "\0" * %d;'
        r'sys.stderr.write(value);'
        r'sys.stdout.write(value);'
    ) % BUFFER_SIZE

    status, out, err = git.Git.execute(['python', '-c', code], _raw=True)

    expect = 0
    actual = status
    assert expect == actual

    expect = '\0' * BUFFER_SIZE
    actual = out
    assert expect == actual

    actual = err
    assert expect == actual
