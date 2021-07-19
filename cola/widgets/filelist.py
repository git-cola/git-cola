from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtWidgets
from qtpy.QtCore import Signal
from qtpy.QtCore import QSize

from .. import cmds
from .. import hotkeys
from .. import qtutils
from ..i18n import N_
from .standard import TreeWidget
from .diff import COMMITS_SELECTED
from .diff import FILES_SELECTED

HISTORIES_SELECTED = 'HISTORIES_SELECTED'
DIFFTOOL_SELECTED = 'DIFFTOOL_SELECTED'


# pylint: disable=too-many-ancestors
class FileWidget(TreeWidget):

    grab_file = Signal(object)

    def __init__(self, context, notifier, parent):
        TreeWidget.__init__(self, parent)
        self.context = context
        self.notifier = notifier

        labels = [N_('Filename'), N_('Additions'), N_('Deletions')]
        self.setHeaderLabels(labels)

        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)

        self.show_history_action = qtutils.add_action(
            self, N_('Show History'), self.show_history, hotkeys.HISTORY
        )

        self.launch_difftool_action = qtutils.add_action(
            self, N_('Launch Diff Tool'), self.show_diff
        )

        self.launch_editor_action = qtutils.add_action(
            self, N_('Launch Editor'), self.edit_paths, hotkeys.EDIT
        )

        self.grab_file_action = qtutils.add_action(
            self, N_('Grab File...'), self._grab_file
        )

        # pylint: disable=no-member
        self.itemSelectionChanged.connect(self.selection_changed)

    def selection_changed(self):
        items = self.selected_items()
        self.notifier.notify_observers(FILES_SELECTED, [i.path for i in items])

    def commits_selected(self, commits):
        if not commits:
            return
        git = self.context.git
        commit = commits[0]
        oid = commit.oid
        status, out, _ = git.show(
            oid, z=True, numstat=True, oneline=True, no_renames=True
        )
        if status == 0:
            paths = [f for f in out.rstrip('\0').split('\0') if f]
            if paths:
                paths = paths[1:]
        else:
            paths = []
        self.list_files(paths)

    def list_files(self, files_log):
        self.clear()
        if not files_log:
            return
        files = []
        for f in files_log:
            item = FileTreeWidgetItem(f)
            files.append(item)
        self.insertTopLevelItems(0, files)

    def adjust_columns(self, size, old_size):
        if size.isValid() and old_size.isValid():
            width = self.columnWidth(0) + size.width() - old_size.width()
            self.setColumnWidth(0, width)
        else:
            width = self.width()
            two_thirds = (width * 2) // 3
            one_sixth = width // 6
            self.setColumnWidth(0, two_thirds)
            self.setColumnWidth(1, one_sixth)
            self.setColumnWidth(2, one_sixth)

    def show(self):
        self.adjust_columns(QSize(), QSize())

    def resizeEvent(self, e):
        self.adjust_columns(e.size(), e.oldSize())

    def contextMenuEvent(self, event):
        menu = qtutils.create_menu(N_('Actions'), self)
        menu.addAction(self.grab_file_action)
        menu.addAction(self.show_history_action)
        menu.addAction(self.launch_difftool_action)
        menu.addAction(self.launch_editor_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def show_diff(self):
        self.notifier.notify_observers(DIFFTOOL_SELECTED, self.selected_paths())

    def _grab_file(self):
        for path in self.selected_paths():
            self.grab_file.emit(path)

    def selected_paths(self):
        return [i.path for i in self.selected_items()]

    def edit_paths(self):
        cmds.do(cmds.Edit, self.context, self.selected_paths())

    def show_history(self):
        items = self.selected_items()
        paths = [i.path for i in items]
        self.notifier.notify_observers(HISTORIES_SELECTED, paths)


class FileTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, file_log, parent=None):
        QtWidgets.QTreeWidgetItem.__init__(self, parent)
        texts = file_log.split('\t')
        self.path = path = texts[2]
        self.setText(0, path)
        self.setText(1, texts[0])
        self.setText(2, texts[1])
