from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import qtutils
from cola.git import git
from cola.git import STDOUT
from cola.i18n import N_
from cola.widgets import defs
from cola.widgets import text
from cola.compat import ustr


def remote_editor():
    view= new_remote_editor(parent=qtutils.active_window())
    view.show()
    view.raise_()
    return view


def new_remote_editor(parent=None):
    return RemoteEditor(parent=parent)


class RemoteEditor(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle(N_('Edit Remotes'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)
            width = max(640, parent.width())
            height = max(480, parent.height())
            self.resize(width, height)
        else:
            self.resize(720, 300)

        self.default_hint = N_(''
            'Add and remove remote repositories using the \n'
            'Add(+) and Delete(-) buttons on the left-hand side.\n'
            '\n'
            'Remotes can be renamed by selecting one from the list\n'
            'and pressing "enter", or by double-clicking.')

        self.remote_list = []
        self.remotes = QtGui.QListWidget()
        self.remotes.setToolTip(N_(
            'Remote git repositories - double-click to rename'))

        self.info = text.HintedTextView(self.default_hint, self)
        font = self.info.font()
        metrics = QtGui.QFontMetrics(font)
        width = metrics.width('_' * 42)
        height = metrics.height() * 13
        self.info.setMinimumWidth(width)
        self.info.setMinimumHeight(height)
        self.info_thread = RemoteInfoThread(self)

        self.add_btn = QtGui.QToolButton()
        self.add_btn.setIcon(qtutils.add_icon())
        self.add_btn.setToolTip(N_('Add new remote git repository'))

        self.refresh_btn = QtGui.QToolButton()
        self.refresh_btn.setIcon(qtutils.reload_icon())
        self.refresh_btn.setToolTip(N_('Refresh'))

        self.delete_btn = QtGui.QToolButton()
        self.delete_btn.setIcon(qtutils.remove_icon())
        self.delete_btn.setToolTip(N_('Delete remote'))

        self.close_btn = QtGui.QPushButton(N_('Close'))

        self._top_layout = qtutils.splitter(Qt.Horizontal,
                                            self.remotes, self.info)
        width = self._top_layout.width()
        self._top_layout.setSizes([width//4, width*3//4])

        self._button_layout = qtutils.hbox(defs.margin, defs.spacing,
                                           self.add_btn, self.delete_btn,
                                           self.refresh_btn, qtutils.STRETCH,
                                           self.close_btn)

        self._layout = qtutils.vbox(defs.margin, defs.spacing,
                                    self._top_layout, self._button_layout)
        self.setLayout(self._layout)
        self.refresh()

        qtutils.connect_button(self.add_btn, self.add)
        qtutils.connect_button(self.delete_btn, self.delete)
        qtutils.connect_button(self.refresh_btn, self.refresh)
        qtutils.connect_button(self.close_btn, self.close)

        self.connect(self.info_thread, SIGNAL('info(PyQt_PyObject)'),
                     self.info.set_value, Qt.QueuedConnection)

        self.connect(self.remotes,
                     SIGNAL('itemChanged(QListWidgetItem*)'),
                     self.remote_renamed)

        self.connect(self.remotes, SIGNAL('itemSelectionChanged()'),
                     self.selection_changed)

    def refresh(self):
        remotes = git.remote()[STDOUT].splitlines()
        self.remotes.clear()
        self.remotes.addItems(remotes)
        self.remote_list = remotes
        self.info.hint.set_value(self.default_hint)
        self.info.hint.enable(True)
        for idx, r in enumerate(remotes):
            item = self.remotes.item(idx)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

    def add(self):
        widget = AddRemoteWidget(self)
        if not widget.add_remote():
            return
        name = widget.name.value()
        url = widget.url.value()
        cmds.do(cmds.RemoteAdd, name, url)
        self.refresh()

    def delete(self):
        remote = qtutils.selected_item(self.remotes, self.remote_list)
        if remote is None:
            return
        cmds.do(cmds.RemoteRemove, remote)
        self.refresh()

    def remote_renamed(self, item):
        idx = self.remotes.row(item)
        if idx < 0:
            return
        if idx >= len(self.remote_list):
            return

        old_name = self.remote_list[idx]
        new_name = ustr(item.text())
        if new_name == old_name:
            return
        if not new_name:
            item.setText(old_name)
            return
        ok, status, out, err = cmds.do(cmds.RemoteRename, old_name, new_name)
        if ok and status == 0:
            self.remote_list[idx] = new_name
        else:
            item.setText(old_name)

    def selection_changed(self):
        remote = qtutils.selected_item(self.remotes, self.remote_list)
        if remote is None:
            return
        self.info.hint.set_value(N_('Gathering info for "%s"...') % remote)
        self.info.hint.enable(True)

        self.info_thread.remote = remote
        self.info_thread.start()


class RemoteInfoThread(QtCore.QThread):
    def __init__(self, parent):
        QtCore.QThread.__init__(self, parent)
        self.remote = None

    def run(self):
        remote = self.remote
        if remote is None:
            return
        status, out, err = git.remote('show', remote)
        # This call takes a long time and we may have selected a
        # different remote...
        if remote == self.remote:
            self.emit(SIGNAL('info(PyQt_PyObject)'), out + err)
        else:
            self.run()


class AddRemoteWidget(QtGui.QDialog):

    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowModality(Qt.WindowModal)

        self.add_btn = QtGui.QPushButton(N_('Add Remote'))
        self.add_btn.setIcon(qtutils.apply_icon())
        self.add_btn.setEnabled(False)

        self.cancel_btn = QtGui.QPushButton(N_('Cancel'))

        def lineedit(hint):
            widget = text.HintedLineEdit(hint)
            widget.hint.enable(True)
            metrics = QtGui.QFontMetrics(widget.font())
            widget.setMinimumWidth(metrics.width('_' * 32))
            return widget

        self.setWindowTitle(N_('Add remote'))
        self.name = lineedit(N_('Name for the new remote'))
        self.url = lineedit('git://git.example.com/repo.git')

        self._form = qtutils.form(defs.margin, defs.spacing,
                                  (N_('Name'), self.name),
                                  (N_('URL'), self.url))

        self._btn_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                        qtutils.STRETCH,
                                        self.add_btn, self.cancel_btn)

        self._layout = qtutils.vbox(defs.margin, defs.spacing,
                                    self._form, self._btn_layout)
        self.setLayout(self._layout)

        self.connect(self.name, SIGNAL('textChanged(QString)'), self.validate)
        self.connect(self.url, SIGNAL('textChanged(QString)'), self.validate)

        qtutils.connect_button(self.add_btn, self.accept)
        qtutils.connect_button(self.cancel_btn, self.reject)

    def validate(self, dummy_text):
        name = self.name.value()
        url = self.url.value()
        self.add_btn.setEnabled(bool(name) and bool(url))

    def add_remote(self):
        self.show()
        self.raise_()
        return self.exec_() == QtGui.QDialog.Accepted
