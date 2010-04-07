from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import qtutils

class RevisionSelector(QtGui.QWidget):
    def __init__(self, parent=None, revs=None, default_revision=None):
        QtGui.QWidget.__init__(self, parent)

        self._revs = revs
        self._revdict = dict(revs)

        self._layt = QtGui.QVBoxLayout()
        self._layt.setMargin(0)
        self.setLayout(self._layt)

        self._rev_layt = QtGui.QHBoxLayout()
        self._rev_layt.setMargin(0)

        self._rev_label = QtGui.QLabel()
        self._rev_layt.addWidget(self._rev_label)

        self._revision = QtGui.QLineEdit()
        if default_revision:
            self._revision.setText(default_revision)
        self._rev_layt.addWidget(self._revision)

        self._layt.addLayout(self._rev_layt)

        self._radio_layt = QtGui.QHBoxLayout()
        self._radio_btns = {}

        # Create the radio buttons
        for label, rev_list in self._revs:
            radio = QtGui.QRadioButton()
            radio.setText(self.tr(label))
            radio.setObjectName(label)
            self.connect(radio, SIGNAL('clicked()'), self._set_revision_list)
            self._radio_layt.addWidget(radio)
            self._radio_btns[label] = radio

        self._radio_spacer = QtGui.QSpacerItem(1, 1,
                                               QtGui.QSizePolicy.Expanding,
                                               QtGui.QSizePolicy.Minimum)
        self._radio_layt.addItem(self._radio_spacer)

        self._layt.addLayout(self._radio_layt)

        self._rev_list = QtGui.QListWidget()
        self._layt.addWidget(self._rev_list)

        label, rev_list = self._revs[0]
        self._radio_btns[label].setChecked(True)
        qtutils.set_items(self._rev_list, rev_list)

        self.connect(self._rev_list, SIGNAL('itemSelectionChanged()'),
                     self._rev_list_selection_changed)

    def revision(self):
        return self._revision.text()

    def set_revision_label(self, txt):
        self._rev_label.setText(txt)

    def _set_revision_list(self):
        sender = str(self.sender().objectName())
        revs = self._revdict[sender]
        qtutils.set_items(self._rev_list, revs)

    def _rev_list_selection_changed(self):
        items = self._rev_list.selectedItems()
        if not items:
            return
        self._revision.setText(items[0].text())
