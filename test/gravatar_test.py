import sys
from unittest.mock import MagicMock

import pytest

from cola import gravatar
from cola.compat import ustr
from cola.gravatar import Gravatar
from cola.gravatar import GravatarLabel
from qtpy import QtGui
from qtpy import QtWidgets


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


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


class FakeReply:
    """Minimal stand-in for QNetworkReply used to drive network_finished."""

    def __init__(self, url, *, error=0, location='', data=b'avatar-bytes'):
        self._url = url
        self._error = error
        self._location = location
        self._data = data
        self.deleted = False

    def url(self):
        mock = MagicMock()
        mock.toString.return_value = self._url
        return mock

    def error(self):
        return self._error

    def rawHeader(self, _name):
        return self._location.encode('utf-8')

    def readAll(self):
        return self._data

    def deleteLater(self):
        self.deleted = True


def _make_label(enable_gravatar=True):
    context = MagicMock()
    context.cfg.get.return_value = enable_gravatar
    label = GravatarLabel(context)
    # Avoid real network traffic; capture requested URLs instead.
    label.network = MagicMock()
    return label


def _real_avatar_reply(label, email):
    """A reply that returns an actual avatar (no Location redirect)."""
    url = Gravatar.url_for_email(email, label.imgsize)
    return FakeReply(url, error=0, location='', data=b'\x89PNG real-avatar')


def _missing_avatar_reply(label, email):
    """A reply redirected to the default image (no avatar for this email)."""
    url = Gravatar.url_for_email(email, label.imgsize)
    return FakeReply(url, error=0, location='https://example.com/default.png')


def test_successful_avatar_is_cached(qapp):
    """A fetched avatar is cached and reused without re-requesting."""
    label = _make_label()
    email = 'alice@example.com'

    label.set_email(email)
    assert label.network.get.call_count == 1  # initial request

    label.network_finished(_real_avatar_reply(label, email))
    assert email in label.pixmaps

    # Revisiting the same author hits the cache; no new request.
    label.set_email(email)
    assert label.network.get.call_count == 1


def test_missing_avatar_is_not_re_requested(qapp):
    """An email with no avatar is remembered and not requested again."""
    label = _make_label()
    email = 'noavatar@example.com'

    label.set_email(email)
    assert label.network.get.call_count == 1

    # Reply redirects to the default image -> recorded as a miss.
    label.network_finished(_missing_avatar_reply(label, email))
    assert email in label.failed
    assert email not in label.pixmaps

    # Revisiting must not fire another request within the retry window.
    label.set_email(email)
    assert label.network.get.call_count == 1


def test_missing_avatar_retried_after_window(qapp):
    """A failed lookup is retried once the retry window elapses."""
    label = _make_label()
    email = 'noavatar@example.com'

    label.set_email(email)
    label.network_finished(_missing_avatar_reply(label, email))
    assert label.network.get.call_count == 1

    # Age the failure beyond the retry window.
    label.failed[email] -= label.RETRY_INTERVAL_SECONDS + 1
    label.set_email(email)
    assert label.network.get.call_count == 2


def test_late_reply_for_previous_email_does_not_repaint(qapp):
    """A reply for an old author must not overwrite the current avatar."""
    label = _make_label()
    alice = 'alice@example.com'
    bob = 'bob@example.com'

    # Request alice, then immediately switch to bob before alice resolves.
    label.set_email(alice)
    label.set_email(bob)
    assert label.email == bob

    captured = []
    label.setPixmap = lambda pixmap: captured.append(pixmap)

    # Alice's (stale) reply arrives now.
    label.network_finished(_real_avatar_reply(label, alice))
    # Alice is still cached for later, but the visible label is not repainted.
    assert alice in label.pixmaps
    assert captured == []

    # Bob's reply arrives and does repaint, since bob is current.
    label.network_finished(_real_avatar_reply(label, bob))
    assert bob in label.pixmaps
    assert len(captured) == 1


def test_inflight_request_is_not_duplicated(qapp):
    """Revisiting an email whose request is still pending issues no duplicate."""
    label = _make_label()
    email = 'alice@example.com'

    label.set_email(email)
    assert label.network.get.call_count == 1

    # Switch away and back while the first request is still in flight.
    label.set_email('bob@example.com')
    label.set_email(email)
    # alice's request is still pending, so no second alice request is sent;
    # bob's is the only additional request.
    assert label.network.get.call_count == 2


def test_disabled_gravatar_uses_default_without_network(qapp):
    """With gravatar disabled, the default icon is cached and no request fires."""
    label = _make_label(enable_gravatar=False)
    email = 'alice@example.com'

    label.set_email(email)
    label.network.get.assert_not_called()
    assert email in label.pixmaps
    assert isinstance(label.pixmaps[email], QtGui.QPixmap)


def test_switching_to_uncached_email_shows_default_not_stale_avatar(qapp):
    """Switching authors shows the default while loading, never the old face.

    Regression: holding the previous author's avatar during the fetch made a
    commit whose author has no gravatar display the wrong person's picture.
    """
    label = _make_label()
    alice = 'alice@example.com'
    bob = 'bob@example.com'

    # Resolve alice so the label is showing alice's real avatar.
    label.set_email(alice)
    label.network_finished(_real_avatar_reply(label, alice))
    alice_pixmap = label.pixmaps[alice]

    painted = []
    label.setPixmap = lambda pixmap: painted.append(pixmap)

    # Switching to an uncached author must repaint the default immediately, so
    # alice's face is not shown for bob's commit while bob's avatar loads.
    label.set_email(bob)
    assert len(painted) == 1
    assert painted[0] is not alice_pixmap
    assert painted[0] is label.default_pixmap()
    assert label.network.get.call_count == 2  # bob is requested

    # bob turns out to have no avatar -> the default stays (no stale alice).
    label.network_finished(_missing_avatar_reply(label, bob))
    assert painted[-1] is label.default_pixmap()


def test_revisiting_cached_miss_shows_default_not_stale_avatar(qapp):
    """An author with a known-missing avatar shows the default, not the prior face."""
    label = _make_label()
    alice = 'alice@example.com'
    bob = 'bob@example.com'

    # alice has an avatar; bob is a known miss.
    label.set_email(alice)
    label.network_finished(_real_avatar_reply(label, alice))
    label.set_email(bob)
    label.network_finished(_missing_avatar_reply(label, bob))

    # Show alice again (cached avatar), then bob again (cached miss).
    label.set_email(alice)
    painted = []
    label.setPixmap = lambda pixmap: painted.append(pixmap)
    label.set_email(bob)
    # bob's miss is cached, so no new request and the default is shown.
    assert label.network.get.call_count == 2
    assert painted[-1] is label.default_pixmap()


def test_default_pixmap_decoded_once(qapp):
    """The fallback icon is decoded a single time and reused."""
    label = _make_label()
    first = label.default_pixmap()
    second = label.default_pixmap()
    assert first is second
