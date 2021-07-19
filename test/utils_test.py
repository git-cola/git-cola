"""Tests the cola.utils module."""
from __future__ import absolute_import, division, print_function, unicode_literals
import os

from cola import core
from cola import utils


def test_basename():
    """Test the utils.basename function."""
    assert utils.basename('bar') == 'bar'
    assert utils.basename('/bar') == 'bar'
    assert utils.basename('/bar ') == 'bar '
    assert utils.basename('foo/bar') == 'bar'
    assert utils.basename('/foo/bar') == 'bar'
    assert utils.basename('foo/foo/bar') == 'bar'
    assert utils.basename('/foo/foo/bar') == 'bar'
    assert utils.basename('/foo/foo//bar') == 'bar'
    assert utils.basename('////foo //foo//bar') == 'bar'


def test_dirname():
    """Test the utils.dirname function."""
    assert utils.dirname('bar') == ''
    assert utils.dirname('/bar') == ''
    assert utils.dirname('//bar') == ''
    assert utils.dirname('///bar') == ''
    assert utils.dirname('foo/bar') == 'foo'
    assert utils.dirname('foo//bar') == 'foo'
    assert utils.dirname('foo /bar') == 'foo '
    assert utils.dirname('/foo//bar') == '/foo'
    assert utils.dirname('/foo /bar') == '/foo '
    assert utils.dirname('//foo//bar') == '/foo'
    assert utils.dirname('///foo///bar') == '/foo'


def test_add_parents():
    """Test the utils.add_parents() function."""
    paths = set(['foo///bar///baz'])
    path_set = utils.add_parents(paths)

    assert 'foo/bar/baz' in path_set
    assert 'foo/bar' in path_set
    assert 'foo' in path_set
    assert 'foo///bar///baz' not in path_set

    # Ensure that the original set is unchanged
    expect = set(['foo///bar///baz'])
    assert expect == paths


def test_tmp_filename_gives_good_file():
    first = utils.tmp_filename('test')
    second = utils.tmp_filename('test')

    assert not core.exists(first)
    assert not core.exists(second)
    assert first != second
    assert os.path.basename(first).startswith('git-cola-test')
    assert os.path.basename(second).startswith('git-cola-test')


def test_strip_one_abspath():
    expect = 'bin/git'
    actual = utils.strip_one('/usr/bin/git')
    assert expect == actual


def test_strip_one_relpath():
    expect = 'git'
    actual = utils.strip_one('bin/git')
    assert expect == actual


def test_strip_one_nested_relpath():
    expect = 'bin/git'
    actual = utils.strip_one('local/bin/git')
    assert expect == actual


def test_strip_one_basename():
    expect = 'git'
    actual = utils.strip_one('git')
    assert expect == actual


def test_select_directory():
    filename = utils.tmp_filename('test')
    expect = os.path.dirname(filename)
    actual = utils.select_directory([filename])
    assert expect == actual


def test_select_directory_prefers_directories():
    filename = utils.tmp_filename('test')
    expect = '.'
    actual = utils.select_directory([filename, '.'])
    assert expect == actual
