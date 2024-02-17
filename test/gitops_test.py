"""Tests basic git operations: commit, log, config"""
from . import helper
from .helper import app_context


# Prevent unused imports lint errors.
assert app_context is not None


def test_git_commit(app_context):
    """Test running 'git commit' via cola.git"""
    helper.write_file('A', 'A')
    helper.write_file('B', 'B')
    helper.run_git('add', 'A', 'B')

    app_context.git.commit(m='initial commit')
    log = helper.run_git('-c', 'log.showsignature=false', 'log', '--pretty=oneline')

    expect = 1
    actual = len(log.splitlines())
    assert expect == actual


def test_git_config(app_context):
    """Test cola.git.config()"""
    helper.run_git('config', 'section.key', 'value')
    expect = (0, 'value', '')
    actual = app_context.git.config('section.key', get=True)
    assert expect == actual
