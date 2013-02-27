from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import utils
from cola import qtutils
from cola import gitcmds
from cola.i18n import N_
from cola.widgets import completion
from cola.widgets import defs
from cola.widgets import standard


def run():
    s = cola.selection()
    if s.staged:
        selection = s.staged
    elif s.unmerged:
        selection = s.unmerged
    elif s.modified:
        selection = s.modified
    elif s.untracked:
        selection = s.untracked
    else:
        return
    model = cola.model()
    launch_with_head(selection, bool(s.staged), model.head)


def launch_with_head(filenames, staged, head):
    args = []
    if staged:
        args.append('--cached')
    if head != 'HEAD':
        args.append(head)
    args.append('--')
    args.extend(filenames)
    launch(args)


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


def diff_expression(parent, expr, create_widget=False):
    dlg = FileDiffDialog(parent, expr=expr)
    if create_widget:
        return dlg
    dlg.show()
    dlg.raise_()
    return dlg.exec_() == QtGui.QDialog.Accepted


class FileDiffDialog(QtGui.QDialog):
    def __init__(self, parent, a=None, b=None, expr=None, title=None):
        QtGui.QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)

        self.a = a
        self.b = b
        self.expr = expr

        if title is None:
            title = N_('git-cola diff')

        self.setWindowTitle(title)
        self.setWindowModality(QtCore.Qt.WindowModal)

        self._expr = completion.GitRefLineEdit(parent=self)
        if expr is None:
            self._expr.hide()
        else:
            self._expr.setText(expr)

        self._tree = standard.TreeWidget(self)
        self._tree.setRootIsDecorated(False)
        self._tree.setSelectionMode(self._tree.ExtendedSelection)
        self._tree.setHeaderHidden(True)

        self._diff_btn = QtGui.QPushButton(N_('Compare'))
        self._diff_btn.setIcon(qtutils.ok_icon())
        self._diff_btn.setEnabled(False)

        self._close_btn = QtGui.QPushButton(N_('Close'))
        self._close_btn.setIcon(qtutils.close_icon())

        self._button_layt = QtGui.QHBoxLayout()
        self._button_layt.setMargin(0)
        self._button_layt.addStretch()
        self._button_layt.addWidget(self._diff_btn)
        self._button_layt.addWidget(self._close_btn)

        self._layt = QtGui.QVBoxLayout()
        self._layt.setMargin(defs.margin)
        self._layt.setSpacing(defs.spacing)

        self._layt.addWidget(self._expr)
        self._layt.addWidget(self._tree)
        self._layt.addLayout(self._button_layt)
        self.setLayout(self._layt)

        self.connect(self._tree, SIGNAL('itemSelectionChanged()'),
                     self._tree_selection_changed)

        self.connect(self._tree,
                     SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self._tree_double_clicked)

        self.connect(self._expr, SIGNAL('textChanged(QString)'),
                     self.text_changed)

        self.connect(self._expr, SIGNAL('returnPressed()'),
                     self.refresh)

        qtutils.connect_button(self._diff_btn, self.diff)
        qtutils.connect_button(self._close_btn, self.close)
        qtutils.add_close_action(self)

        self.resize(720, 420)
        self.refresh()

    def text_changed(self, txt):
        self.expr = unicode(txt)
        self.refresh()

    def refresh(self):
        if self.expr is not None:
            self.diff_arg = utils.shell_usplit(self.expr)
        elif self.b is None:
            self.diff_arg = [self.a]
        else:
            self.diff_arg = [self.a, self.b]
        self.refresh_filenames()

    def refresh_filenames(self):
        self._tree.clear()

        if self.a and self.b is None:
            filenames = gitcmds.diff_index_filenames(self.a)
        else:
            filenames = gitcmds.diff(self.diff_arg)
        if not filenames:
            return

        icon = qtutils.file_icon()
        items = []
        for filename in filenames:
            item = QtGui.QTreeWidgetItem()
            item.setIcon(0, icon)
            item.setText(0, filename)
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(filename))
            items.append(item)
        self._tree.addTopLevelItems(items)

    def _tree_selection_changed(self):
        self._diff_btn.setEnabled(bool(self._tree.selectedItems()))

    def _tree_double_clicked(self, item, column):
        path = item.data(0, QtCore.Qt.UserRole).toPyObject()
        launch(self.diff_arg + ['--', unicode(path)])

    def diff(self):
        items = self._tree.selectedItems()
        if not items:
            return
        paths = [i.data(0, QtCore.Qt.UserRole).toPyObject() for i in items]
        for path in paths:
            launch(self.diff_arg + ['--', unicode(path)])
