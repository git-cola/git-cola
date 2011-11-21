from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola.prefs import diff_font
from cola.qt import DiffSyntaxHighlighter
from cola.widgets import defs

class SelectCommitsView(QtGui.QDialog):
    def __init__(self,
                 parent=None,
                 title=None,
                 multiselect=True,
                 syntax=True):
        QtGui.QDialog.__init__(self, parent)
        if title:
            self.setWindowTitle(title)

        # Allow disabling multi-select
        self.resize(700, 420)
        self.setObjectName('commit')

        self.vboxlayout = QtGui.QVBoxLayout(self)
        self.vboxlayout.setObjectName('vboxlayout')

        self.splitter = QtGui.QSplitter(self)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(defs.handle_width)
        self.splitter.setObjectName('splitter')

        self.commit_list = QtGui.QListWidget(self.splitter)
        self.commit_list.setObjectName('commit_list')
        self.commit_list.setAlternatingRowColors(True)
        if multiselect:
            mode = QtGui.QAbstractItemView.ExtendedSelection
        else:
            mode = QtGui.QAbstractItemView.SingleSelection
        self.commit_list.setSelectionMode(mode)

        self.commit_text = QtGui.QTextEdit(self.splitter)
        self.commit_text.setMinimumSize(QtCore.QSize(0, 40))
        self.commit_text.setTabChangesFocus(True)
        self.commit_text.setUndoRedoEnabled(False)
        self.commit_text.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.commit_text.setReadOnly(True)
        self.commit_text.setObjectName('commit_text')

        self.vboxlayout.addWidget(self.splitter)
        self.hboxlayout = QtGui.QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")

        self.label = QtGui.QLabel(self)
        self.label.setObjectName('label')
        self.label.setText(self.tr('Revision Expression:'))

        self.hboxlayout.addWidget(self.label)

        self.revision = QtGui.QLineEdit(self)
        self.revision.setObjectName('revision')

        self.hboxlayout.addWidget(self.revision)
        self.vboxlayout.addLayout(self.hboxlayout)

        self.button_box = QtGui.QDialogButtonBox(self)
        self.button_box.setStandardButtons(QtGui.QDialogButtonBox.Cancel |
                                           QtGui.QDialogButtonBox.Ok)
        self.button_box.setObjectName('button_box')
        self.vboxlayout.addWidget(self.button_box)

        self.connect(self.button_box, SIGNAL('accepted()'), self.accept)
        self.connect(self.button_box, SIGNAL('rejected()'), self.reject)

        self.setTabOrder(self.button_box, self.commit_list)
        self.setTabOrder(self.commit_list, self.revision)
        self.setTabOrder(self.revision, self.commit_text)

        # Make the list widget slighty larger
        self.splitter.setSizes([100, 150])
        self.syntax = DiffSyntaxHighlighter(self.commit_text.document(),
                                            whitespace=False)

        # Set the console font
        if syntax:
            self.commit_text.setFont(diff_font())
