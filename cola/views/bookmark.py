"""Provides the BookmarksView dialog."""

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.views import standard


class BookmarkView(standard.StandardDialog):
    def __init__(self, parent=None):
        standard.StandardDialog.__init__(self, parent=parent)

        self.setWindowTitle(self.tr('Bookmarks'))
        self.resize(494, 238)
        self._vboxlayt = QtGui.QVBoxLayout(self)

        # Exposed
        self.bookmarks = QtGui.QListWidget(self)
        self.bookmarks.setAlternatingRowColors(True)
        self.bookmarks.setSelectionMode(QtGui.QAbstractItemView
                                             .ExtendedSelection)

        self._vboxlayt.addWidget(self.bookmarks)
        self._hboxlayt = QtGui.QHBoxLayout()

        # Exposed
        self.button_open = QtGui.QPushButton(self)
        self.button_open.setText(self.tr('Open'))
        self._hboxlayt.addWidget(self.button_open)

        self.button_delete = QtGui.QPushButton(self)
        self.button_delete.setText(self.tr('Delete'))
        self._hboxlayt.addWidget(self.button_delete)

        self._button_spacer = QtGui.QSpacerItem(91, 20,
                                          QtGui.QSizePolicy.Expanding,
                                          QtGui.QSizePolicy.Minimum)
        self._hboxlayt.addItem(self._button_spacer)

        # Exposed
        self.button_save = QtGui.QPushButton(self)
        self.button_save.setText(self.tr('Save'))
        self._hboxlayt.addWidget(self.button_save)

        self.button_cancel = QtGui.QPushButton(self)
        self.button_cancel.setText(self.tr('Cancel'))
        self._hboxlayt.addWidget(self.button_cancel)

        self._vboxlayt.addLayout(self._hboxlayt)

        self.connect(self.button_cancel, SIGNAL('clicked()'),
                     self.reject)


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    bookmark = BookmarkView()
    bookmark.show()
    sys.exit(app.exec_())
