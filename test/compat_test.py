"""Tests the compat module"""
# encoding: utf-8
from __future__ import absolute_import, division, unicode_literals
import os

from cola import compat


def test_setenv():
    """Test the core.decode function"""
    key = 'COLA_UNICODE_TEST'
    value = '字龍'
    compat.setenv(key, value)
    assert key in os.environ
    assert os.getenv(key)

    compat.unsetenv(key)
    assert key not in os.environ
    assert not os.getenv(key)
