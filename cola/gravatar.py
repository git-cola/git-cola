from __future__ import division, absolute_import, unicode_literals
import time
import hashlib

from cola import sipcompat
sipcompat.initialize()

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtNetwork
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import icons
from cola.compat import ustr, parse
from cola.widgets import defs


class Gravatar(object):

    @staticmethod
    def url_for_email(email, imgsize):
        email_hash = core.decode(hashlib.md5(core.encode(email)).hexdigest())
        # Python2.6 requires byte strings for urllib2.quote() so we have
        # to force
        default_url = 'https://git-cola.github.io/images/git-64x64.jpg'
        encoded_url = parse.quote(core.encode(default_url), core.encode(''))
        query = '?s=%d&d=%s' % (imgsize, core.decode(encoded_url))
        url = 'https://gravatar.com/avatar/' + email_hash + query
        return url


class GravatarLabel(QtGui.QLabel):

    def __init__(self, parent=None):
        QtGui.QLabel.__init__(self, parent)

        self.email = None
        self.response = None
        self.timeout = 0
        self.imgsize = defs.medium_icon
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
        pixmap = icons.cola().pixmap(xres)
        byte_array = QtCore.QByteArray()
        buf = QtCore.QBuffer(byte_array)
        buf.open(QtCore.QIODevice.WriteOnly)
        pixmap.save(buf, 'PNG')
        buf.close()
        return byte_array

    def network_finished(self, reply):
        email = self.email

        header = QtCore.QByteArray('Location')
        location = ustr(reply.rawHeader(header)).strip()
        if location:
            request_location = Gravatar.url_for_email(self.email, self.imgsize)
            relocated = location != request_location
        else:
            relocated = False

        if reply.error() == QtNetwork.QNetworkReply.NoError:
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
        # we may add cache entries for thee wrong email address.
        url = Gravatar.url_for_email(email, self.imgsize)
        if url == reply.url().toString():
            self.pixmaps[email] = pixmap

    def set_pixmap_from_response(self):
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(self.response)
        self.setPixmap(pixmap)
        return pixmap
