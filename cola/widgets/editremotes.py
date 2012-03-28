from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola.app
from cola import core
from cola import qtutils
from cola import gitcfg
from cola.git import git
from cola.widgets import defs
from cola.widgets import text


class RemoteEditor(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle('Edit Remotes')
        self.setWindowModality(Qt.WindowModal)

        self.default_hint = (''
            'Add and remove remote repositories using the \n'
            'Add(+) and Delete(-) buttons on the left-hand side.\n'
            '\n'
            'Remotes can be renamed by selecting one from the list\n'
            'and pressing "enter", or by double-clicking.')

        self.remote_list = []
        self.remotes = QtGui.QListWidget()
        self.remotes.setToolTip(self.tr(
            'Remote git repositories - double-click to rename'))

        self.info = text.HintedTextView(self.default_hint, self)
        font = self.info.font()
        metrics = QtGui.QFontMetrics(font)
        width = metrics.width('_' * 72)
        height = metrics.height() * 13
        self.info.setMinimumWidth(width)
        self.info.setMinimumHeight(height)
        self.info_thread = RemoteInfoThread(self)

        self.cfg = gitcfg.instance()
        self.add_btn = QtGui.QToolButton()
        self.add_btn.setIcon(qtutils.icon('add.svg'))
        self.add_btn.setToolTip(self.tr('Add new remote git repository'))

        self.refresh_btn = QtGui.QToolButton()
        self.refresh_btn.setIcon(qtutils.icon('view-refresh.svg'))
        self.refresh_btn.setToolTip(self.tr('Refresh'))

        self.delete_btn = QtGui.QToolButton()
        self.delete_btn.setIcon(qtutils.icon('remove.svg'))
        self.delete_btn.setToolTip(self.tr('Delete remote'))

        self.close_btn = QtGui.QPushButton(self.tr('Close'))

        self._top_layout = QtGui.QSplitter()
        self._top_layout.setOrientation(Qt.Horizontal)
        self._top_layout.setHandleWidth(defs.handle_width)
        self._top_layout.addWidget(self.remotes)
        self._top_layout.addWidget(self.info)
        width = self._top_layout.width()
        self._top_layout.setSizes([width/4, width*3/4])

        self._button_layout = QtGui.QHBoxLayout()
        self._button_layout.addWidget(self.add_btn)
        self._button_layout.addWidget(self.delete_btn)
        self._button_layout.addWidget(self.refresh_btn)
        self._button_layout.addStretch()
        self._button_layout.addWidget(self.close_btn)

        self._layout = QtGui.QVBoxLayout()
        self._layout.setMargin(defs.margin)
        self._layout.setSpacing(defs.spacing)
        self._layout.addWidget(self._top_layout)
        self._layout.addLayout(self._button_layout)
        self.setLayout(self._layout)

        self.refresh()

        qtutils.connect_button(self.add_btn, self.add)
        qtutils.connect_button(self.delete_btn, self.delete)
        qtutils.connect_button(self.refresh_btn, self.refresh)
        qtutils.connect_button(self.close_btn, self.close)

        self.connect(self.info_thread, SIGNAL('info'),
                     self.info.set_value)

        self.connect(self.remotes,
                     SIGNAL('itemChanged(QListWidgetItem*)'),
                     self.remote_renamed)

        self.connect(self.remotes, SIGNAL('itemSelectionChanged()'),
                     self.selection_changed)

    def refresh(self):
        prefix = len('remote.')
        suffix = len('.url')
        remote_urls = self.cfg.find('remote.*.url')
        remotes = [k[prefix:-suffix] for k in sorted(remote_urls.keys())]
        self.remotes.clear()
        self.remotes.addItems(remotes)
        self.remote_list = remotes
        self.info.set_hint(self.default_hint)
        self.info.enable_hint(True)
        for idx, r in enumerate(remotes):
            item = self.remotes.item(idx)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

    def add(self):
        widget = AddRemoteWidget(self)
        if not widget.add_remote():
            return
        name = widget.name.value()
        url = widget.url.value()
        status, out = git.remote('add', name, url,
                                 with_status=True, with_stderr=True)
        if status != 0:
            qtutils.critical('Error creating remote "%s"' % name, out)
        self.refresh()

    def delete(self):
        remote = qtutils.selected_item(self.remotes, self.remote_list)
        if remote is None:
            return

        title = 'Delete Remote'
        question = 'Delete remote?'
        info = unicode(self.tr('Delete remote "%s"')) % remote
        ok_btn = 'Delete'
        if not qtutils.confirm(title, question, info, ok_btn):
            return

        status, out = git.remote('rm', remote,
                                 with_status=True, with_stderr=True)
        if status != 0:
            qtutils.critical('Error deleting remote "%s"' % remote, out)
        cola.model().update_status()
        self.refresh()

    def remote_renamed(self, item):
        idx = self.remotes.row(item)
        if idx < 0:
            return
        if idx >= len(self.remote_list):
            return

        old_name = self.remote_list[idx]
        new_name = unicode(item.text())
        if new_name == old_name:
            return
        if not new_name:
            item.setText(old_name)
            return

        title = 'Rename Remote'
        question = 'Rename remote?'
        info = unicode(self.tr(
                'Rename remote "%s" to "%s"?')) % (old_name, new_name)
        ok_btn = 'Rename'

        if qtutils.confirm(title, question, info, ok_btn):
            git.remote('rename', old_name, new_name)
            self.remote_list[idx] = new_name
        else:
            item.setText(old_name)

    def selection_changed(self):
        remote = qtutils.selected_item(self.remotes, self.remote_list)
        if remote is None:
            return
        self.info.set_hint('Gathering info for "%s"...' % remote)
        self.info.enable_hint(True)

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
        status, out = git.remote('show', remote,
                                 with_stderr=True, with_status=True)
        out = core.decode(out)
        # This call takes a long time and we may have selected a
        # different remote...
        if remote == self.remote:
            self.emit(SIGNAL('info'), out)
        else:
            self.run()


class AddRemoteWidget(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowModality(Qt.WindowModal)

        self.add_btn = QtGui.QPushButton(self.tr('Add Remote'))
        self.add_btn.setIcon(qtutils.apply_icon())

        self.cancel_btn = QtGui.QPushButton(self.tr('Cancel'))

        def lineedit(hint):
            widget = text.HintedLineEdit(hint)
            widget.enable_hint(True)
            metrics = QtGui.QFontMetrics(widget.font())
            widget.setMinimumWidth(metrics.width('_' * 32))
            return widget

        self.name = lineedit('Name for the new remote')
        self.url = lineedit('git://git.example.com/repo.git')

        self._form = QtGui.QFormLayout()
        self._form.setMargin(defs.margin)
        self._form.setSpacing(defs.spacing)
        self._form.addRow(self.tr('Name'), self.name)
        self._form.addRow(self.tr('URL'), self.url)

        self._btn_layout = QtGui.QHBoxLayout()
        self._btn_layout.setMargin(0)
        self._btn_layout.setSpacing(defs.button_spacing)
        self._btn_layout.addStretch()
        self._btn_layout.addWidget(self.add_btn)
        self._btn_layout.addWidget(self.cancel_btn)

        self._layout = QtGui.QVBoxLayout()
        self._layout.setMargin(defs.margin)
        self._layout.setSpacing(defs.margin)
        self._layout.addLayout(self._form)
        self._layout.addLayout(self._btn_layout)
        self.setLayout(self._layout)

        self.connect(self.name, SIGNAL('textChanged(QString)'),
                     self.validate)

        self.connect(self.url, SIGNAL('textChanged(QString)'),
                     self.validate)

        self.add_btn.setEnabled(False)

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


def edit():
    window = RemoteEditor(qtutils.active_window())
    window.show()
    window.raise_()
    return window

if __name__ == '__main__':
    app = cola.app.ColaApplication([])
    edit().exec_()
