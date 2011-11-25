"""Provides dialogs for comparing branches and commits."""

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.views import standard
from cola.widgets import defs


class CompareView(standard.Dialog):
    def __init__(self, parent=None):
        standard.Dialog.__init__(self, parent=parent)

        self.setWindowTitle(self.tr('Compare Commits'))
        self.resize(649, 372)
        self._main_layt = QtGui.QVBoxLayout(self)

        self._top_layt = QtGui.QHBoxLayout()
        self._top_left_layt = QtGui.QVBoxLayout()
        self._top_left_layt.setMargin(0)
        self._top_left_layt.setSpacing(defs.spacing)

        # Exposed
        self.descriptions_start = QtGui.QTreeWidget(self)
        self.descriptions_start.setRootIsDecorated(False)
        self.descriptions_start.setAllColumnsShowFocus(True)
        self.descriptions_start.headerItem().setText(0,
                self.tr('Start Commit'))
        self._top_left_layt.addWidget(self.descriptions_start)

        # Exposed
        self.revision_start = QtGui.QLineEdit(self)
        self.revision_start.setReadOnly(True)
        self._top_left_layt.addWidget(self.revision_start)
        self._top_layt.addLayout(self._top_left_layt)

        self._top_right_layt = QtGui.QVBoxLayout()
        self._top_right_layt.setMargin(0)
        self._top_right_layt.setSpacing(defs.spacing)

        # Exposed
        self.descriptions_end = QtGui.QTreeWidget(self)
        self.descriptions_end.setRootIsDecorated(False)
        self.descriptions_end.setAllColumnsShowFocus(True)
        self.descriptions_end.headerItem().setText(0, self.tr('End Commit'))
        self._top_right_layt.addWidget(self.descriptions_end)

        # Exposed
        self.revision_end = QtGui.QLineEdit(self)
        self.revision_end.setReadOnly(True)
        self._top_right_layt.addWidget(self.revision_end)

        self._top_layt.addLayout(self._top_right_layt)
        self._main_layt.addLayout(self._top_layt)

        # Exposed
        self.compare_files = QtGui.QTreeWidget(self)
        self.compare_files.setAlternatingRowColors(True)
        self.compare_files.setRootIsDecorated(False)
        self.compare_files.setAllColumnsShowFocus(True)
        self.compare_files.headerItem().setText(0, self.tr('File Differences'))
        self._main_layt.addWidget(self.compare_files)

        self._bottom_layt = QtGui.QHBoxLayout()
        self._bottom_layt.setMargin(0)
        self._bottom_layt.setSpacing(defs.spacing)

        self.show_versions = QtGui.QCheckBox(self)
        self.show_versions.setText(self.tr('Show Versions'))
        self._bottom_layt.addWidget(self.show_versions)

        self._num_results_label = QtGui.QLabel(self)
        self._num_results_label.setText(self.tr('Num Results'))
        self._bottom_layt.addWidget(self._num_results_label)

        # Exposed
        self.num_results = QtGui.QSpinBox(self)
        self.num_results.setMinimum(1)
        self.num_results.setMaximum(9999)
        self.num_results.setProperty('value', QtCore.QVariant(100))
        self._bottom_layt.addWidget(self.num_results)

        self._bottom_spacer = QtGui.QSpacerItem(1, 1,
                                                QtGui.QSizePolicy.Expanding,
                                                QtGui.QSizePolicy.Minimum)
        self._bottom_layt.addItem(self._bottom_spacer)

        self.button_compare = QtGui.QPushButton(self)
        self.button_compare.setText(self.tr('Compare'))
        self._bottom_layt.addWidget(self.button_compare)

        self.button_close = QtGui.QPushButton(self)
        self.button_close.setText(self.tr('Close'))
        self._bottom_layt.addWidget(self.button_close)

        self._main_layt.addLayout(self._bottom_layt)

        self.connect(self.button_close, SIGNAL('clicked()'), self.accept)


class BranchCompareView(standard.Dialog):
    def __init__(self, parent=None):
        standard.Dialog.__init__(self, parent=parent)

        self.setWindowTitle(self.tr('Branch Diff Viewer'))
        self.resize(658, 350)

        self._main_layt = QtGui.QVBoxLayout(self)
        self._main_layt.setMargin(defs.margin)
        self._main_layt.setSpacing(defs.spacing)

        self._splitter = QtGui.QSplitter(self)
        self._splitter.setOrientation(QtCore.Qt.Vertical)
        self._splitter.setHandleWidth(defs.handle_width)

        self._top_widget = QtGui.QWidget(self._splitter)

        self._top_grid_layt = QtGui.QGridLayout(self._top_widget)
        self._top_grid_layt.setMargin(0)
        self._top_grid_layt.setSpacing(defs.spacing)

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
        self._bottom_grid_layt.setMargin(0)

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
        self.button_close.setText(self.tr('Close'))
        self._bottom_grid_layt.addWidget(self.button_close, 1, 3, 1, 1)

        # Exposed
        self.diff_files = QtGui.QTreeWidget(self._bottom_widget)
        self.diff_files.headerItem().setText(0, self.tr('File Differences'))

        self._bottom_grid_layt.addWidget(self.diff_files, 0, 0, 1, 4)
        self._main_layt.addWidget(self._splitter)

        self.connect(self.button_close, SIGNAL('clicked()'), self.accept)
