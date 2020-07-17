#!/usr/bin/env python
"""Test the cmds module"""
from __future__ import absolute_import, division, unicode_literals
try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

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
    context = Mock()
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


@patch('cola.interaction.Interaction.confirm')
def test_submodule_add(confirm):
    # "git submodule" should not be called if the answer is "no"
    context = Mock()
    url = 'url'
    path = ''
    reference = ''
    branch = ''
    depth = 0
    cmd = cmds.SubmoduleAdd(context, url, path, branch, depth, reference)

    confirm.return_value = False
    cmd.do()
    assert not context.git.submodule.called

    expect = ['--', 'url']
    actual = cmd.get_args()
    assert expect == actual

    cmd.path = 'path'
    expect = ['--', 'url', 'path']
    actual = cmd.get_args()
    assert expect == actual

    cmd.reference = 'ref'
    expect = ['--reference', 'ref', '--', 'url', 'path']
    actual = cmd.get_args()
    assert expect == actual

    cmd.branch = 'branch'
    expect = ['--branch', 'branch', '--reference', 'ref', '--', 'url', 'path']
    actual = cmd.get_args()
    assert expect == actual

    cmd.reference = ''
    cmd.branch = ''
    cmd.depth = 1
    expect = ['--depth', '1', '--', 'url', 'path']
    actual = cmd.get_args()
    assert expect == actual

    # Run the command and assert that "git submodule" was called.
    confirm.return_value = True
    context.git.submodule.return_value = (0, '', '')
    cmd.do()
    context.git.submodule.assert_called_once_with('add', *expect)
    assert context.model.update_file_status.called
    assert context.model.update_submodules_list.called


if __name__ == '__main__':
    pytest.main([__file__])
