"""Provides the StashView dialog."""

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.views import standard


class StashView(standard.StandardDialog):
    def __init__(self, parent=None):
        standard.StandardDialog.__init__(self, parent=parent)

        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowTitle(self.tr('Stash'))
        self.resize(497, 292)

        self._label = QtGui.QLabel()
        self._label.setText('<center>Stash List</center>')

        self._main_layt = QtGui.QVBoxLayout(self)
        self._main_layt.setMargin(4)
        self._main_layt.setSpacing(2)

        # Exposed
        self.stash_list = QtGui.QListWidget(self)

        self._btn_layt = QtGui.QVBoxLayout()
        self._btn_layt.setMargin(0)
        self._btn_layt.setSpacing(2)

        self._btn_layt0 = QtGui.QHBoxLayout()
        self._btn_layt0.setMargin(0)
        self._btn_layt0.setSpacing(4)

        self._btn_layt1 = QtGui.QHBoxLayout()
        self._btn_layt1.setMargin(0)
        self._btn_layt1.setSpacing(4)

        self._btn_layt2 = QtGui.QHBoxLayout()
        self._btn_layt2.setMargin(0)
        self._btn_layt2.setSpacing(4)

        # Exposed
        self.button_stash_show = QtGui.QPushButton(self)
        self.button_stash_show.setToolTip(
                self.tr('Show the changes recorded in the '
                        'selected stash stash as a diff'))
        self.button_stash_show.setText(self.tr('Show'))

        # Exposed
        self.button_stash_apply = QtGui.QPushButton(self)
        self.button_stash_apply.setToolTip(self.tr('Apply the selected stash'))
        self.button_stash_apply.setText(self.tr('Apply'))

        # Exposed
        self.button_stash_save = QtGui.QPushButton(self)
        self.button_stash_save.setText(self.tr('Save'))

        # Exposed
        self.button_stash_drop = QtGui.QPushButton(self)
        self.button_stash_drop.setToolTip(self.tr('Remove the selected stash'))
        self.button_stash_drop.setText(self.tr('Remove'))

        # Exposed
        self.button_stash_clear = QtGui.QPushButton(self)
        self.button_stash_clear.setToolTip(self.tr('Remove all stashed states'))
        self.button_stash_clear.setText(self.tr('Remove All'))

        # Exposed
        self.button_stash_done = QtGui.QPushButton(self)
        self.button_stash_done.setText(self.tr('Done'))

        # Exposed
        self.keep_index = QtGui.QCheckBox(self)
        self.keep_index.setText(self.tr('Keep Index'))
        self.keep_index.setChecked(True)

        self.setTabOrder(self.button_stash_save, self.button_stash_show)
        self.setTabOrder(self.button_stash_show, self.button_stash_apply)
        self.setTabOrder(self.button_stash_apply, self.button_stash_drop)
        self.setTabOrder(self.button_stash_drop, self.button_stash_clear)

        # Arrange layouts
        self._btn_layt0.addStretch()
        self._btn_layt0.addWidget(self.keep_index)

        self._btn_layt1.addWidget(self.button_stash_show)
        self._btn_layt1.addWidget(self.button_stash_apply)
        self._btn_layt1.addWidget(self.button_stash_save)

        self._btn_layt2.addWidget(self.button_stash_drop)
        self._btn_layt2.addWidget(self.button_stash_clear)
        self._btn_layt2.addWidget(self.button_stash_done)

        self._btn_layt.addItem(self._btn_layt0)
        self._btn_layt.addItem(self._btn_layt1)
        self._btn_layt.addItem(self._btn_layt2)

        self._main_layt.addWidget(self._label)
        self._main_layt.addWidget(self.stash_list)
        self._main_layt.addItem(self._btn_layt)
        self._main_layt.addStretch()


        self.connect(self.button_stash_done, SIGNAL('clicked()'), self.accept)


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    stash = StashView()
    stash.show()
    sys.exit(app.exec_())
