"""Provides the BranchView dialog."""

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.views import standard


class BranchCompareView(standard.StandardDialog):
    def __init__(self, parent=None):
        standard.StandardDialog.__init__(self, parent=parent)

        self.setWindowTitle(self.tr('Branch Diff Viewer'))
        self.resize(658, 350)

        self._main_layt = QtGui.QVBoxLayout(self)
        self._main_layt.setMargin(3)

        self._splitter = QtGui.QSplitter(self)
        self._splitter.setOrientation(QtCore.Qt.Vertical)
        self._splitter.setHandleWidth(3)

        self._top_widget = QtGui.QWidget(self._splitter)

        self._top_grid_layt = QtGui.QGridLayout(self._top_widget)
        self._top_grid_layt.setMargin(0)

        # Exposed
        self.left_combo = QtGui.QComboBox(self._top_widget)
        self.left_combo.addItem(self.tr('Local'))
        self.left_combo.addItem(self.tr('Remote'))
        self._top_grid_layt.addWidget(self.left_combo, 0, 0, 1, 1)

        # Exposed
        self.right_combo = QtGui.QComboBox(self._top_widget)
        self.right_combo.addItem(self.tr('Local'))
        self.right_combo.addItem(self.tr('Remote'))
        self.right_combo.setCurrentIndex(1)
        self._top_grid_layt.addWidget(self.right_combo, 0, 1, 1, 1)

        # Exposed
        self.left_list = QtGui.QListWidget(self._top_widget)
        self._top_grid_layt.addWidget(self.left_list, 1, 0, 1, 1)

        # Exposed
        self.right_list = QtGui.QListWidget(self._top_widget)
        self._top_grid_layt.addWidget(self.right_list, 1, 1, 1, 1)

        self._bottom_widget = QtGui.QWidget(self._splitter)
        self._bottom_grid_layt = QtGui.QGridLayout(self._bottom_widget)
        self._bottom_grid_layt.setMargin(3)

        self._button_spacer = QtGui.QSpacerItem(1, 1,
                                                QtGui.QSizePolicy.Expanding,
                                                QtGui.QSizePolicy.Minimum)
        self._bottom_grid_layt.addItem(self._button_spacer, 1, 1, 1, 1)

        # Exposed
        self.button_compare = QtGui.QPushButton(self._bottom_widget)
        self.button_compare.setText(self.tr('Compare'))
        self._bottom_grid_layt.addWidget(self.button_compare, 1, 2, 1, 1)

        # Exposed
        self.button_close = QtGui.QPushButton(self._bottom_widget)
        self.button_close.setText(QtGui.QApplication.translate('branchview', 'Close', None, QtGui.QApplication.UnicodeUTF8))
        self._bottom_grid_layt.addWidget(self.button_close, 1, 3, 1, 1)

        # Exposed
        self.diff_files = QtGui.QTreeWidget(self._bottom_widget)
        self.diff_files.headerItem().setText(0, self.tr('File Differences'))

        self._bottom_grid_layt.addWidget(self.diff_files, 0, 0, 1, 4)
        self._main_layt.addWidget(self._splitter)

        self.connect(self.button_close, SIGNAL('clicked()'), self.accept)
