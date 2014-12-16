from __future__ import division, absolute_import, unicode_literals

import time

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtNetwork
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import qtutils
from cola import core
from cola.compat import ustr, urllib
import hashlib


class Gravatar(object):
    @staticmethod
    def url_for_email(email, imgsize):
        email_hash = hashlib.md5(core.encode(email)).hexdigest()
        default_url = b'https://git-cola.github.io/images/git-64x64.jpg'
        encoded_url = urllib.quote(default_url, b'')
        query = '?s=%d&d=%s' % (imgsize, encoded_url)
        url = 'https://gravatar.com/avatar/' + email_hash + query
        return url


class GravatarLabel(QtGui.QLabel):
    def __init__(self, parent=None):
        QtGui.QLabel.__init__(self, parent)

        self.email = None
        self.response = None
        self.timeout = 0
        self.imgsize = 48
        self.pixmaps = {}

        self.network = QtNetwork.QNetworkAccessManager()
        self.connect(self.network,
                     SIGNAL('finished(QNetworkReply*)'),
                     self.network_finished)

    def set_email(self, email):
        if email in self.pixmaps:
            self.setPixmap(self.pixmaps[email])
            return
        if (self.timeout > 0 and
                (int(time.time()) - self.timeout) < (5 * 60)):
            self.set_pixmap_from_response()
            return
        if email == self.email and self.response is not None:
            self.set_pixmap_from_response()
            return
        self.email = email
        self.request(email)

    def request(self, email):
        url = Gravatar.url_for_email(email, self.imgsize)
        self.network.get(QtNetwork.QNetworkRequest(QtCore.QUrl(url)))

    def default_pixmap_as_bytes(self):
        xres = self.imgsize
        pixmap = qtutils.git_icon().pixmap(xres)
        byte_array = QtCore.QByteArray()
        buf = QtCore.QBuffer(byte_array)
        buf.open(QtCore.QIODevice.WriteOnly)
        pixmap.save(buf, 'PNG')
        buf.close()
        return byte_array

    def network_finished(self, reply):
        email = self.email

        header = QtCore.QByteArray('Location')
        raw_header = reply.rawHeader(header)
        if raw_header:
            location = ustr(QtCore.QString(raw_header)).strip()
            request_location = ustr(
                    Gravatar.url_for_email(self.email, self.imgsize))
            relocated = location != request_location
        else:
            relocated = False

        if reply.error() == QtNetwork.QNetworkReply.NoError:
            if relocated:
                # We could do get_url(urllib.unquote(location)) to
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
        # we may add cache entries for thee wrong email address.
        url = Gravatar.url_for_email(email, self.imgsize)
        if url == ustr(reply.url().toString()):
            self.pixmaps[email] = pixmap

    def set_pixmap_from_response(self):
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(self.response)
        self.setPixmap(pixmap)
        return pixmap
