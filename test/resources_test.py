from unittest.mock import patch

from cola import core
from cola import resources

from . import helper


@patch('cola.resources.get_prefix')
def test_command_unix(mock_prefix, monkeypatch):
    """Test the behavior of resources.command() on unix platforms"""
    mock_prefix.return_value = helper.fixture()
    monkeypatch.setattr(core, 'IS_WIN32', False)

    expect = helper.fixture('bin', 'bare-cmd')
    actual = resources.command('bare-cmd')
    assert expect == actual

    expect = helper.fixture('bin', 'exe-cmd')
    actual = resources.command('exe-cmd')
    assert expect == actual


@patch('cola.resources.get_prefix')
def test_command_win32(mock_prefix, monkeypatch):
    """Test the behavior of resources.command() on unix platforms"""
    mock_prefix.return_value = helper.fixture()
    monkeypatch.setattr(core, 'IS_WIN32', False)

    expect = helper.fixture('bin', 'bare-cmd')
    actual = resources.command('bare-cmd')
    assert expect == actual

    # Windows will return exe-cmd.exe because the path exists.
    monkeypatch.setattr(core, 'IS_WIN32', True)
    expect = helper.fixture('bin', 'exe-cmd.exe')
    actual = resources.command('exe-cmd')
    assert expect == actual
