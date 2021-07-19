# encoding: utf-8
"""Tests the cola.core module's unicode handling"""
from __future__ import absolute_import, division, print_function, unicode_literals

from cola import core

from . import helper


def test_core_decode():
    """Test the core.decode function"""
    filename = helper.fixture('unicode.txt')
    expect = core.decode(core.encode('unicøde'))
    actual = core.read(filename).strip()
    assert expect == actual


def test_core_encode():
    """Test the core.encode function"""
    filename = helper.fixture('unicode.txt')
    expect = core.encode('unicøde')
    actual = core.encode(core.read(filename).strip())
    assert expect == actual


def test_decode_None():
    """Ensure that decode(None) returns None"""
    expect = None
    actual = core.decode(None)
    assert expect == actual


def test_decode_utf8():
    filename = helper.fixture('cyrillic-utf-8.txt')
    actual = core.read(filename)
    assert actual.encoding == 'utf-8'


def test_decode_non_utf8():
    filename = helper.fixture('cyrillic-cp1251.txt')
    actual = core.read(filename)
    assert actual.encoding == 'iso-8859-15'


def test_decode_non_utf8_string():
    filename = helper.fixture('cyrillic-cp1251.txt')
    with open(filename, 'rb') as f:
        content = f.read()
    actual = core.decode(content)
    assert actual.encoding == 'iso-8859-15'


def test_guess_mimetype():
    value = '字龍.txt'
    expect = 'text/plain'
    actual = core.guess_mimetype(value)
    assert expect == actual
    # This function is robust to bytes vs. unicode
    actual = core.guess_mimetype(core.encode(value))
    assert expect == actual
