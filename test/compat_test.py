"""Tests the compat module"""
import os

from cola import compat
from cola import operations


def test_setenv():
    """Test the core.decode function"""
    key = 'COLA_UNICODE_TEST'
    value = '字龍'
    ops = operations.LocalOperations()
    compat.setenv(ops, key, value)
    assert key in os.environ
    assert os.getenv(key)

    compat.unsetenv(ops, key)
    assert key not in os.environ
    assert not os.getenv(key)
