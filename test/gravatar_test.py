from cola import gravatar
from cola.compat import ustr


def test_url_for_email_():
    email = 'email@example.com'
    expect = (
        'https://gravatar.com/avatar/5658ffccee7f0ebfda2b226238b1eb6e?s=64'
        + r'&d=https%3A%2F%2Fgit-cola.github.io%2Fimages%2Fgit-64x64.jpg'
    )
    actual = gravatar.Gravatar.url_for_email(email, 64)
    assert expect == actual
    assert isinstance(actual, ustr)
