from __future__ import absolute_import, division, print_function, unicode_literals

from cola import gravatar
from cola.compat import ustr


def test_url_for_email_():
    email = 'email@example.com'
    expect = (
        r'https://gravatar.com/avatar/'
        r'5658ffccee7f0ebfda2b226238b1eb6e'
        r'?s=64'
        r'&d=https%3A%2F%2Fgit-cola.github.io'
        r'%2Fimages%2Fgit-64x64.jpg'
    )
    actual = gravatar.Gravatar.url_for_email(email, 64)
    assert expect == actual
    assert isinstance(actual, ustr)
