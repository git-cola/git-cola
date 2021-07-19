from __future__ import absolute_import, division, print_function, unicode_literals
import os
import shutil
import stat
import tempfile

import pytest
try:
    from unittest.mock import Mock, patch  # noqa pylint: disable=unused-import
except ImportError:
    from mock import Mock, patch  # noqa pylint: disable=unused-import

from cola import core
from cola import git
from cola import gitcfg
from cola import gitcmds
from cola.models import main


def tmp_path(*paths):
    """Returns a path relative to the test/tmp directory"""
    dirname = core.decode(os.path.dirname(__file__))
    return os.path.join(dirname, 'tmp', *paths)


def fixture(*paths):
    dirname = core.decode(os.path.dirname(__file__))
    return os.path.join(dirname, 'fixtures', *paths)


# shutil.rmtree() can't remove read-only files on Windows.  This onerror
# handler, adapted from <http://stackoverflow.com/a/1889686/357338>, works
# around this by changing such files to be writable and then re-trying.
def remove_readonly(func, path, _exc_info):
    if func is os.remove and not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise AssertionError('Should not happen')


def touch(*paths):
    """Open and close a file to either create it or update its mtime"""
    for path in paths:
        open(path, 'a').close()


def write_file(path, content):
    """Write content to the specified file path"""
    with open(path, 'w') as f:
        f.write(content)


def append_file(path, content):
    """Open a file in append mode and write content to it"""
    with open(path, 'a') as f:
        f.write(content)


def run_git(*args):
    """Run git with the specified arguments"""
    status, out, _ = core.run_command(['git'] + list(args))
    assert status == 0
    return out


def commit_files():
    """Commit the current state as the initial commit"""
    run_git('commit', '-m', 'initial commit')


def initialize_repo():
    """Initialize a git repository in the current directory"""
    run_git('init')
    run_git('symbolic-ref', 'HEAD', 'refs/heads/main')
    run_git('config', '--local', 'user.name', 'Your Name')
    run_git('config', '--local', 'user.email', 'you@example.com')
    run_git('config', '--local', 'commit.gpgsign', 'false')
    run_git('config', '--local', 'tag.gpgsign', 'false')
    touch('A', 'B')
    run_git('add', 'A', 'B')


@pytest.fixture
def app_context():
    """Create a repository in a temporary directory and return its ApplicationContext"""
    tmp_directory = tempfile.mkdtemp('-cola-test')
    current_directory = os.getcwd()
    os.chdir(tmp_directory)

    initialize_repo()
    context = Mock()
    context.git = git.create()
    context.git.set_worktree(core.getcwd())
    context.cfg = gitcfg.create(context)
    context.model = main.create(context)

    context.cfg.reset()
    gitcmds.reset()

    yield context

    os.chdir(current_directory)
    shutil.rmtree(tmp_directory, onerror=remove_readonly)
