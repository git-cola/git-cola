import time
import hashlib

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import QtNetwork

from . import core
from . import icons
from . import qtutils
from .compat import parse
from .models import prefs
from .widgets import defs


class Gravatar:
    @staticmethod
    def url_for_email(email, imgsize):
        email_hash = md5_hexdigest(email)
        # Python2.6 requires byte strings for urllib2.quote() so we have
        # to force
        default_url = 'https://git-cola.github.io/images/git-64x64.jpg'
        encoded_url = parse.quote(core.encode(default_url), core.encode(''))
        query = '?s=%d&d=%s' % (imgsize, core.decode(encoded_url))
        url = 'https://gravatar.com/avatar/' + email_hash + query
        return url


def md5_hexdigest(value):
    """Return the md5 hexdigest for a value.

    Used for implementing the gravatar API. Not used for security purposes.
    """
    # https://github.com/git-cola/git-cola/issues/1157
    #  ValueError: error:060800A3:
    #   digital envelope routines: EVP_DigestInit_ex: disabled for fips
    #
    # Newer versions of Python, including Centos8's patched Python3.6 and
    # mainline Python 3.9+ have a "usedoforsecurity" parameter which allows us
    # to continue using hashlib.md5().
    encoded_value = core.encode(value)
    result = ''
    try:
        # This could raise ValueError in theory but we always use encoded bytes
        # so that does not happen in practice.
        result = hashlib.md5(encoded_value, usedforsecurity=False).hexdigest()
    except TypeError:
        # Fallback to trying hashlib.md5 directly.
        result = hashlib.md5(encoded_value).hexdigest()
    return core.decode(result)


class GravatarLabel(QtWidgets.QLabel):
    def __init__(self, context, parent=None):
        QtWidgets.QLabel.__init__(self, parent)

        self.context = context
        self.email = None
        self.response = None
        self.timeout = 0
        self.imgsize = defs.medium_icon
        self.pixmaps = {}
        self._default_pixmap_bytes = None

        self.network = QtNetwork.QNetworkAccessManager()
        self.network.finished.connect(self.network_finished)

    def set_email(self, email):
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

    def request(self, email):
        if prefs.enable_gravatar(self.context):
            url = Gravatar.url_for_email(email, self.imgsize)
            self.network.get(QtNetwork.QNetworkRequest(QtCore.QUrl(url)))
        else:
            self.pixmaps[email] = self.set_pixmap_from_response()

    def default_pixmap_as_bytes(self):
        if self._default_pixmap_bytes is None:
            xres = self.imgsize
            pixmap = icons.cola().pixmap(xres)
            byte_array = QtCore.QByteArray()
            buf = QtCore.QBuffer(byte_array)
            buf.open(QtCore.QIODevice.WriteOnly)
            pixmap.save(buf, 'PNG')
            buf.close()
            self._default_pixmap_bytes = byte_array
        else:
            byte_array = self._default_pixmap_bytes
        return byte_array

    def network_finished(self, reply):
        email = self.email

        header = QtCore.QByteArray(b'Location')
        location = core.decode(bytes(reply.rawHeader(header))).strip()
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
        # we may add cache entries for thee wrong email address.
        url = Gravatar.url_for_email(email, self.imgsize)
        if url == reply.url().toString():
            self.pixmaps[email] = pixmap

    def set_pixmap_from_response(self):
        if self.response is None:
            self.response = self.default_pixmap_as_bytes()
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(self.response)
        self.setPixmap(pixmap)
        return pixmap
