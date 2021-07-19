from __future__ import absolute_import, division, print_function, unicode_literals

from cola import resources

from . import helper
from .helper import patch


@patch('cola.resources.compat')
@patch('cola.resources.get_prefix')
def test_command_unix(mock_prefix, mock_compat):
    """Test the behavior of resources.command() on unix platforms"""
    mock_compat.WIN32 = False
    mock_prefix.return_value = helper.fixture()

    expect = helper.fixture('bin', 'bare-cmd')
    actual = resources.command('bare-cmd')
    assert expect == actual

    expect = helper.fixture('bin', 'exe-cmd')
    actual = resources.command('exe-cmd')
    assert expect == actual


@patch('cola.resources.compat')
@patch('cola.resources.get_prefix')
def test_command_win32(mock_prefix, mock_compat):
    """Test the behavior of resources.command() on unix platforms"""
    mock_compat.WIN32 = True
    mock_prefix.return_value = helper.fixture()

    expect = helper.fixture('bin', 'bare-cmd')
    actual = resources.command('bare-cmd')
    assert expect == actual

    # Windows will return exe-cmd.exe because the path exists.
    expect = helper.fixture('bin', 'exe-cmd.exe')
    actual = resources.command('exe-cmd')
    assert expect == actual
