"""Provides the StashView dialog."""

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.views import standard


class StashView(standard.StandardDialog):
    def __init__(self, parent=None):
        standard.StandardDialog.__init__(self, parent=parent)

        self.setWindowTitle(self.tr('Stash'))
        self.resize(497, 292)
        self._main_layt = QtGui.QGridLayout(self)
        self._main_layt.setMargin(10)

        # Exposed
        self.stash_list = QtGui.QListWidget(self)
        self._main_layt.addWidget(self.stash_list, 0, 0, 1, 4)

        # Exposed
        self.button_stash_show = QtGui.QPushButton(self)
        self.button_stash_show.setToolTip(
                self.tr('Show the changes recorded in the '
                        'selected stash stash as a diff'))
        self.button_stash_show.setText(self.tr('Show'))
        self._main_layt.addWidget(self.button_stash_show, 1, 0, 1, 1)

        # Exposed
        self.button_stash_apply = QtGui.QPushButton(self)
        self.button_stash_apply.setToolTip(self.tr('Apply the selected stash'))
        self.button_stash_apply.setText(self.tr('Apply'))
        self._main_layt.addWidget(self.button_stash_apply, 1, 1, 1, 1)

        # Exposed
        self.button_stash_save = QtGui.QPushButton(self)
        self.button_stash_save.setText(self.tr('Save'))
        self._main_layt.addWidget(self.button_stash_save, 1, 2, 1, 1)

        # Exposed
        self.button_stash_drop = QtGui.QPushButton(self)
        self.button_stash_drop.setToolTip(self.tr('Remove the selected stash'))
        self.button_stash_drop.setText(self.tr('Remove'))
        self._main_layt.addWidget(self.button_stash_drop, 4, 0, 1, 1)

        # Exposed
        self.button_stash_clear = QtGui.QPushButton(self)
        self.button_stash_clear.setToolTip(self.tr('Remove all stashed states'))
        self.button_stash_clear.setText(self.tr('Remove All'))
        self._main_layt.addWidget(self.button_stash_clear, 4, 1, 1, 1)

        # Exposed
        self.button_stash_done = QtGui.QPushButton(self)
        self.button_stash_done.setText(self.tr('Done'))
        self._main_layt.addWidget(self.button_stash_done, 4, 2, 1, 1)

        self._spacer = QtGui.QSpacerItem(1, 1,
                                         QtGui.QSizePolicy.Expanding,
                                         QtGui.QSizePolicy.Minimum)
        self._main_layt.addItem(self._spacer, 4, 3, 1, 1)

        # Exposed
        self.keep_index = QtGui.QCheckBox(self)
        self.keep_index.setText(self.tr('Keep Index'))
        self.keep_index.setChecked(True)
        self._main_layt.addWidget(self.keep_index, 1, 3, 1, 1)

        self.setTabOrder(self.button_stash_save, self.button_stash_show)
        self.setTabOrder(self.button_stash_show, self.button_stash_apply)
        self.setTabOrder(self.button_stash_apply, self.button_stash_drop)
        self.setTabOrder(self.button_stash_drop, self.button_stash_clear)

        self.connect(self.button_stash_done, SIGNAL('clicked()'), self.accept)


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    stash = StashView()
    stash.show()
    sys.exit(app.exec_())
