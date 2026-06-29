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
    def __init__(self, context: ApplicationContext, parent: Any = None) -> None:
        QtWidgets.QLabel.__init__(self, parent)

        self.context = context
        self.email: str | None = None
        self.response: bytes | None = None
        self.timeout = 0
        self.imgsize = defs.medium_icon
        self.pixmaps = {}
        self._default_pixmap_bytes = None

        self.network = QtNetwork.QNetworkAccessManager()
        self.network.finished.connect(self.network_finished)

    def set_email(self, email: str) -> None:
        """Update the author icon based on the specified email"""
        pixmap = self.pixmaps.get(email, None)
        if pixmap is not None:
            self.setPixmap(pixmap)
            return
        if self.timeout > 0 and (int(time.time()) - self.timeout) < (5 * 60):
            self.set_pixmap_from_response()
            return
        if email == self.email and self.response is not None:
            self.set_pixmap_from_response()
            return
        self.email = email
        self.request(email)

    def request(self, email) -> None:
        if prefs.enable_gravatar(self.context):
            url = Gravatar.url_for_email(email, self.imgsize)
            self.network.get(QtNetwork.QNetworkRequest(QtCore.QUrl(url)))
        else:
            self.pixmaps[email] = self.set_pixmap_from_response()

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
        email = self.email
        location = qtutils.network_reply_header(reply, 'Location')
        if location:
            request_location = Gravatar.url_for_email(self.email, self.imgsize)
            relocated = location != request_location
        else:
            relocated = False
        no_error = qtutils.enum_value(QtNetwork.QNetworkReply.NetworkError.NoError)
        reply_error = qtutils.enum_value(reply.error())
        if reply_error == no_error:
            if relocated:
                # We could do get_url(parse.unquote(location)) to
                # download the default image.
                # Save bandwidth by using a pixmap.
                self.response = self.default_pixmap_as_bytes()
            else:
                self.response = reply.readAll()
            self.timeout = 0
        else:
            self.response = self.default_pixmap_as_bytes()
            self.timeout = int(time.time())

        pixmap = self.set_pixmap_from_response()

        # If the email has not changed (e.g. no other requests)
        # then we know that this pixmap corresponds to this specific
        # email address.  We can't blindly trust self.email else
        # we may add cache entries for the wrong email address.
        url = Gravatar.url_for_email(email, self.imgsize)
        if url == reply.url().toString():
            self.pixmaps[email] = pixmap

        # Schedule reply destruction on the next event-loop tick. Without this,
        # Qt eventually tears the SSL socket down while the QNetworkReply is
        # still attached, producing a "QIODevice::read (QSslSocket): device
        # not open" warning. Qt docs explicitly say not to delete the reply
        # inside the finished slot -- use deleteLater() instead.
        # https://doc.qt.io/qt-6/qnetworkaccessmanager.html#finished
        reply.deleteLater()

    def set_pixmap_from_response(self) -> QPixmap:
        if self.response is None:
            self.response = self.default_pixmap_as_bytes()
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(self.response)
        self.setPixmap(pixmap)
        return pixmap
