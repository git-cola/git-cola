from __future__ import absolute_import, division, print_function, unicode_literals

from cola import compat
from cola import spellcheck

from . import helper


def test_spellcheck_generator():
    check = spellcheck.NorvigSpellCheck()
    assert_spellcheck(check)


def test_spellcheck_unicode():
    path = helper.fixture('unicode.txt')
    check = spellcheck.NorvigSpellCheck(cracklib=path)
    assert_spellcheck(check)


def assert_spellcheck(check):
    for word in check.read():
        assert word is not None
        assert isinstance(word, compat.ustr)
