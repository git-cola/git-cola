from __future__ import annotations
import hashlib
import time
from typing import TYPE_CHECKING
from typing import Any

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtNetwork
from qtpy import QtWidgets

from . import core
from . import icons
from . import qtutils
from .compat import parse
from .models import prefs
from .widgets import defs

if TYPE_CHECKING:
    from qtpy.QtCore import QByteArray
    from qtpy.QtGui import QPixmap

    from .app import ApplicationContext


class Gravatar:
    @staticmethod
    def url_for_email(email, imgsize) -> str:
        email_hash = sha256_hexdigest(email)
        default_url = 'https://git-cola.github.io/images/git-64x64.jpg'
        encoded_url = parse.quote(core.encode(default_url), core.encode(''))
        query = '?s=%d&d=%s' % (imgsize, core.decode(encoded_url))
        url = 'https://gravatar.com/avatar/' + email_hash + query
        return url


def sha256_hexdigest(value: str) -> core.UStr:
    """Return the SHA256 hexdigest of an email for the Gravatar API.

    Gravatar prefers SHA256 over MD5 and requires the email to be trimmed and
    lower-cased before hashing. https://docs.gravatar.com/rest/hash/

    SHA256 also resolves the FIPS crash that MD5 caused: on FIPS-enabled
    systems hashlib.md5() raises ValueError and aborted git-dag (exit 134) the
    moment a commit was viewed (https://github.com/git-cola/git-cola/issues/1157).
    The old fix passed usedforsecurity=False to MD5, but that only exists on
    Python 3.9+ and still asks OpenSSL to permit a FIPS-disallowed algorithm.
    SHA256 is FIPS-approved, so the workaround is no longer needed. Do not
    revert to MD5.
    """
    normalized = core.encode(value.strip().lower())
    return core.decode(hashlib.sha256(normalized).hexdigest())


class GravatarLabel(QtWidgets.QLabel):
    # Re-request an email whose lookup failed only after this many seconds.
    RETRY_INTERVAL_SECONDS = 5 * 60

    def __init__(self, context: ApplicationContext, parent: Any = None) -> None:
        QtWidgets.QLabel.__init__(self, parent)

        self.context = context
        # The email whose avatar is currently meant to be displayed. Replies
        # for any other email update the cache but must not repaint the label.
        self.email: str | None = None
        self.imgsize = defs.medium_icon
        # Per-email pixmap cache. The single source of truth for what to show;
        # populated for successful, default and missing-avatar lookups alike so
        # an email is never requested twice once resolved.
        self.pixmaps: dict[str, QPixmap] = {}
        # Emails whose lookup failed, mapped to the time of failure. These are
        # not cached as pixmaps so that the default icon is reused, but they
        # are remembered to avoid hammering the network; retried after
        # RETRY_INTERVAL_SECONDS.
        self.failed: dict[str, int] = {}
        # In-flight request URLs mapped back to the email that issued them, so
        # a reply can identify its own email instead of relying on self.email,
        # which may have moved on to a newer selection.
        self.requested: dict[str, str] = {}
        self._default_pixmap_bytes = None

        self.network = QtNetwork.QNetworkAccessManager()
        self.network.finished.connect(self.network_finished)

    def set_email(self, email: str) -> None:
        """Update the author icon based on the specified email"""
        # Normalize as Gravatar does so case/whitespace variants of the same
        # address share a single cache entry, request and reply attribution.
        email = email.strip().lower()
        self.email = email
        pixmap = self.pixmaps.get(email, None)
        if pixmap is not None:
            self.setPixmap(pixmap)
            return
        # A recent failed lookup shows the default icon without re-requesting.
        failed_at = self.failed.get(email)
        if failed_at is not None:
            if (int(time.time()) - failed_at) < self.RETRY_INTERVAL_SECONDS:
                self.set_pixmap_from_default()
                return
            # The retry window has elapsed; allow another attempt.
            del self.failed[email]
        self.set_pixmap_from_default()
        self.request(email)

    def request(self, email) -> None:
        if prefs.enable_gravatar(self.context):
            url = Gravatar.url_for_email(email, self.imgsize)
            # A request for this email is already in flight; don't issue a
            # duplicate. The pending reply will repaint if still current.
            if url in self.requested:
                return
            # Remember which email this URL belongs to so the reply can be
            # attributed correctly even if the selection has since changed.
            self.requested[url] = email
            self.network.get(QtNetwork.QNetworkRequest(QtCore.QUrl(url)))
        else:
            self.pixmaps[email] = self.set_pixmap_from_default()

    def default_pixmap_as_bytes(self) -> QByteArray:
        if self._default_pixmap_bytes is None:
            xres = self.imgsize
            pixmap = icons.cola().pixmap(xres)
            scaled_pixmap = pixmap.scaled(xres, xres)
            byte_array = QtCore.QByteArray()
            buf = QtCore.QBuffer(byte_array)
            buf.open(QtCore.QIODevice.WriteOnly)
            scaled_pixmap.save(buf, 'PNG')
            buf.close()
            self._default_pixmap_bytes = byte_array
        else:
            byte_array = self._default_pixmap_bytes
        return byte_array

    def network_finished(self, reply: Any) -> None:
        # Identify the email from the reply's own request URL rather than
        # self.email, which may have advanced to a newer selection while this
        # request was in flight. Without this, a slow reply could be attributed
        # to (and cached under) the wrong author.
        url = reply.url().toString()
        email = self.requested.pop(url, None)

        location = qtutils.network_reply_header(reply, 'Location')
        if location and email is not None:
            request_location = Gravatar.url_for_email(email, self.imgsize)
            relocated = location != request_location
        else:
            relocated = False
        no_error = qtutils.enum_value(QtNetwork.QNetworkReply.NetworkError.NoError)
        reply_error = qtutils.enum_value(reply.error())

        if reply_error == no_error and not relocated:
            # A real avatar was returned. Cache it permanently for this email.
            response = reply.readAll()
            pixmap = self.pixmap_from_bytes(response)
            if email is not None:
                self.pixmaps[email] = pixmap
                self.failed.pop(email, None)
        else:
            # No avatar exists for this email (relocated to the default, or the
            # request errored). Record the miss so the default icon is reused
            # and the email is not re-requested until the retry window lapses.
            pixmap = self.default_pixmap()
            if email is not None:
                self.failed[email] = int(time.time())

        # Only repaint if this reply is for the email that is currently meant
        # to be displayed. A late reply for a previous author must not clobber
        # the avatar shown for the current one.
        if email is not None and email == self.email:
            self.setPixmap(pixmap)

        # Schedule reply destruction on the next event-loop tick. Without this,
        # Qt eventually tears the SSL socket down while the QNetworkReply is
        # still attached, producing a "QIODevice::read (QSslSocket): device
        # not open" warning. Qt docs explicitly say not to delete the reply
        # inside the finished slot -- use deleteLater() instead.
        # https://doc.qt.io/qt-6/qnetworkaccessmanager.html#finished
        reply.deleteLater()

    def pixmap_from_bytes(self, data: QByteArray) -> QPixmap:
        """Build a QPixmap from raw image bytes"""
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(data)
        return pixmap

    def default_pixmap(self) -> QPixmap:
        """Return the fallback git-cola icon as a QPixmap"""
        return self.pixmap_from_bytes(self.default_pixmap_as_bytes())

    def set_pixmap_from_default(self) -> QPixmap:
        """Display the fallback icon and return it"""
        pixmap = self.default_pixmap()
        self.setPixmap(pixmap)
        return pixmap
