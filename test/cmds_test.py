#!/usr/bin/env python
"""Test the cmds module"""
from __future__ import absolute_import, division, unicode_literals
try:
    from unittest import mock
except ImportError:
    import mock

import pytest

from cola import cmds
from cola.compat import uchr


def test_Commit_strip_comments():
    """Ensure that commit messages are stripped of comments"""

    msg = 'subject\n\n#comment\nbody'
    expect = 'subject\n\nbody\n'
    actual = cmds.Commit.strip_comments(msg)
    assert expect == actual


def test_commit_strip_comments_unicode():
    """Ensure that unicode is preserved in stripped commit messages"""

    msg = uchr(0x1234) + '\n\n#comment\nbody'
    expect = uchr(0x1234) + '\n\nbody\n'
    actual = cmds.Commit.strip_comments(msg)
    assert expect == actual


def test_unix_path_win32():
    path = r'Z:\Program Files\git-cola\bin\git-dag'
    expect = '/Z/Program Files/git-cola/bin/git-dag'
    actual = cmds.unix_path(path, is_win32=lambda: True)
    assert expect == actual


def test_unix_path_network_win32():
    path = r'\\Z\Program Files\git-cola\bin\git-dag'
    expect = '//Z/Program Files/git-cola/bin/git-dag'
    actual = cmds.unix_path(path, is_win32=lambda: True)
    assert expect == actual


def test_unix_path_is_a_noop_on_sane_platforms():
    path = r'/:we/don\t/need/no/stinking/badgers!'
    expect = path
    actual = cmds.unix_path(path, is_win32=lambda: False)
    assert expect == actual


def test_context_edit_command():
    context = mock.Mock()
    model = context.model

    cmd = cmds.EditModel(context)
    cmd.new_diff_text = 'test_diff_text'
    cmd.new_diff_type = 'test_diff_type'
    cmd.new_mode = 'test_mode'
    cmd.new_filename = 'test_filename'
    cmd.do()

    model.set_diff_text.assert_called_once_with('test_diff_text')
    model.set_diff_type.assert_called_once_with('test_diff_type')
    model.set_mode.assert_called_once_with('test_mode')
    model.set_filename.assert_called_once_with('test_filename')
    assert model.set_filename.call_count == 1


if __name__ == '__main__':
    pytest.main([__file__])
