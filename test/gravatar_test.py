from cola import gravatar
from cola.compat import ustr


def test_url_for_email_():
    email = 'email@example.com'
    # Gravatar prefers the SHA256 digest of the trimmed, lower-cased email.
    expect = (
        'https://gravatar.com/avatar/'
        '2a539d6520266b56c3b0c525b9e6128858baeccb5ee9b694a2906e123c8d6dd3?s=64'
        + r'&d=https%3A%2F%2Fgit-cola.github.io%2Fimages%2Fgit-64x64.jpg'
    )
    actual = gravatar.Gravatar.url_for_email(email, 64)
    assert expect == actual
    assert isinstance(actual, ustr)


def test_url_for_email_normalizes_case_and_whitespace():
    """Trimming and lower-casing yield the same URL as the canonical form."""
    canonical = gravatar.Gravatar.url_for_email('email@example.com', 64)
    assert gravatar.Gravatar.url_for_email('  Email@Example.COM  ', 64) == canonical
