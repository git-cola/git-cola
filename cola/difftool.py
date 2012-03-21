from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import utils
from cola import qtutils
from cola import gitcmds
from cola.widgets import defs
from cola.widgets import standard


def launch(args):
    """Launches 'git difftool' with args"""
    difftool_args = ['git', 'difftool', '--no-prompt']
    difftool_args.extend(args)
    utils.fork(difftool_args)


def diff_commits(parent, a, b):
    dlg = FileDiffDialog(parent, a=a, b=b)
    dlg.show()
    dlg.raise_()
    return dlg.exec_() == QtGui.QDialog.Accepted


def diff_expression(parent, expr):
    dlg = FileDiffDialog(parent, expr=expr)
    dlg.show()
    dlg.raise_()
    return dlg.exec_() == QtGui.QDialog.Accepted


class FileDiffDialog(QtGui.QDialog):
    def __init__(self, parent, a=None, b=None, expr=None):
        QtGui.QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.a = a
        self.b = b
        self.expr = expr

        self.setWindowTitle('Select File(s)')
        self.setWindowModality(QtCore.Qt.WindowModal)

        self._tree = standard.TreeWidget(self)
        self._tree.setRootIsDecorated(False)
        self._tree.setSelectionMode(self._tree.ExtendedSelection)
        self._tree.setHeaderHidden(True)

        self._diff_btn = QtGui.QPushButton('Compare')
        self._diff_btn.setIcon(qtutils.ok_icon())
        self._diff_btn.setEnabled(False)

        self._close_btn = QtGui.QPushButton('Close')
        self._close_btn.setIcon(qtutils.close_icon())

        self._button_layt = QtGui.QHBoxLayout()
        self._button_layt.setMargin(0)
        self._button_layt.addStretch()
        self._button_layt.addWidget(self._diff_btn)
        self._button_layt.addWidget(self._close_btn)

        self._layt = QtGui.QVBoxLayout()
        self._layt.setMargin(defs.margin)
        self._layt.setSpacing(defs.spacing)
        self._layt.addWidget(self._tree)
        self._layt.addLayout(self._button_layt)
        self.setLayout(self._layt)

        self.connect(self._tree, SIGNAL('itemSelectionChanged()'),
                     self._tree_selection_changed)

        self.connect(self._tree,
                     SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self._tree_double_clicked)

        qtutils.connect_button(self._diff_btn, self.diff)
        qtutils.connect_button(self._close_btn, self.close)
        qtutils.add_close_action(self)

        if self.expr:
            self.diff_arg = tuple(utils.shell_split(self.expr))
        elif self.b is None:
            self.diff_arg = (self.a,)
        else:
            self.diff_arg = (self.a, self.b)

        self.resize(720, 420)


    def exec_(self):
        if self.expr:
            filenames = gitcmds.diff_filenames(*self.diff_arg)
        elif self.b is None:
            filenames = gitcmds.diff_index_filenames(self.a)
        else:
            filenames = gitcmds.diff_filenames(*self.diff_arg)

        if not filenames:
            details = ('"git diff --name-only %s" returned an empty list' %
                       ' '.join(self.diff_arg))
            self.hide()
            qtutils.information('git cola',
                                message='No changes to diff',
                                details=details)
            self.close()
            return self.Accepted

        icon = qtutils.file_icon()
        items = []
        for filename in filenames:
            item = QtGui.QTreeWidgetItem()
            item.setIcon(0, icon)
            item.setText(0, filename)
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(filename))
            items.append(item)
        self._tree.addTopLevelItems(items)

        return QtGui.QDialog.exec_(self)

    def _tree_selection_changed(self):
        self._diff_btn.setEnabled(bool(self._tree.selectedItems()))

    def _tree_double_clicked(self, item, column):
        path = item.data(0, QtCore.Qt.UserRole).toPyObject()
        launch(self.diff_arg + ('--', unicode(path)))

    def diff(self):
        items = self._tree.selectedItems()
        if not items:
            return
        paths = [i.data(0, QtCore.Qt.UserRole).toPyObject() for i in items]
        for path in paths:
            launch(self.diff_arg + ('--', unicode(path)))
