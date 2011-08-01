"""Provides the StashView dialog."""

from PyQt4 import QtCore
from PyQt4 import QtGui

from cola import qt
from cola import qtutils
from cola.views import standard


class StashView(standard.StandardDialog):
    def __init__(self, parent=None):
        standard.StandardDialog.__init__(self, parent=parent)

        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowTitle(self.tr('Stash'))
        self.resize(600, 200)

        self._label = QtGui.QLabel()
        self._label.setText('<center>Stash List</center>')

        self.stash_list = QtGui.QListWidget(self)

        self.button_apply =\
            self.toolbutton(self.tr('Apply'),
                            self.tr('Apply the selected stash'),
                            qtutils.apply_icon())
        self.button_save =\
            self.toolbutton(self.tr('Save'),
                            self.tr('Save modified state to new stash'),
                            qtutils.save_icon())
        self.button_remove = \
            self.toolbutton(self.tr('Remove'),
                            self.tr('Remove the selected stash'),
                            qtutils.discard_icon())
        self.button_close = \
            self.pushbutton(self.tr('Close'),
                            self.tr('Close'), qtutils.close_icon())

        self.keep_index = QtGui.QCheckBox(self)
        self.keep_index.setText(self.tr('Keep Index'))
        self.keep_index.setChecked(True)

        self.setTabOrder(self.button_save, self.button_apply)
        self.setTabOrder(self.button_apply, self.button_remove)
        self.setTabOrder(self.button_remove, self.keep_index)
        self.setTabOrder(self.keep_index, self.button_close)

        # Arrange layouts
        self._main_layt = QtGui.QVBoxLayout(self)
        self._main_layt.setMargin(6)
        self._main_layt.setSpacing(6)

        self._btn_layt = QtGui.QHBoxLayout()
        self._btn_layt.setMargin(0)
        self._btn_layt.setSpacing(4)

        self._btn_layt.addWidget(self.button_save)
        self._btn_layt.addWidget(self.button_apply)
        self._btn_layt.addWidget(self.button_remove)
        self._btn_layt.addWidget(self.keep_index)
        self._btn_layt.addStretch()
        self._btn_layt.addWidget(self.button_close)

        self._main_layt.addWidget(self._label)
        self._main_layt.addWidget(self.stash_list)
        self._main_layt.addItem(self._btn_layt)


    def toolbutton(self, text, tooltip, icon):
        return qt.create_toolbutton(self,
                                    text=text, tooltip=tooltip, icon=icon)

    def pushbutton(self, text, tooltip, icon):
        btn = QtGui.QPushButton(self)
        btn.setText(self.tr(text))
        btn.setToolTip(self.tr(tooltip))
        btn.setIcon(icon)
        return btn

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    stash = StashView()
    stash.show()
    sys.exit(app.exec_())
