from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import hotkeys
from cola import qtutils
from cola.i18n import N_
from cola.git import git
from cola.widgets.standard import TreeWidget
from cola.widgets.diff import COMMITS_SELECTED
from cola.widgets.diff import FILES_SELECTED

HISTORIES_SELECTED = 'HISTORIES_SELECTED'
DIFFTOOL_SELECTED = 'DIFFTOOL_SELECTED'

class FileWidget(TreeWidget):

    def __init__(self, notifier, parent):
        TreeWidget.__init__(self, parent)
        self.notifier = notifier
        self.setHeaderLabels([N_('Filename'), N_('Additions'), N_('Deletions')])
        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)

        self.show_history_action = (
                qtutils.add_action(self, N_('Show History'),
                                   self.show_file_history, hotkeys.HISTORY))

        self.launch_difftool_action = (
                qtutils.add_action(self, N_('Launch Diff Tool'),
                                   self.show_file_diff, hotkeys.DIFF))

        self.launch_editor_action = (
                qtutils.add_action(self, N_('Launch Diff Tool'),
                                   self.edit_paths, hotkeys.EDIT))

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.selection_changed)

    def selection_changed(self):
        items = self.selected_items()
        self.notifier.notify_observers(FILES_SELECTED,
                                       [i.path for i in items])

    def commits_selected(self, commits):
        if not commits:
            return
        commit = commits[0]
        sha1 = commit.sha1
        status, out, err = git.show(sha1, z=True, numstat=True,
                                    oneline=True, no_renames=True)
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

    def adjust_columns(self):
        width = self.width() - 20
        zero = width*2 // 3
        onetwo = width // 6
        self.setColumnWidth(0, zero)
        self.setColumnWidth(1, onetwo)
        self.setColumnWidth(2, onetwo)

    def show(self):
        self.adjust_columns()

    def resizeEvent(self, e):
        self.adjust_columns()

    def contextMenuEvent(self, event):
        menu = QtGui.QMenu(self)
        menu.addAction(self.show_history_action)
        menu.addAction(self.launch_difftool_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def show_file_diff(self):
        self.notifier.notify_observers(DIFFTOOL_SELECTED, self.selected_paths())

    def selected_paths(self):
        return [i.path for i in self.selected_items()]

    def edit_paths(self):
        cmds.do(cmds.Edit, self.selected_paths())

    def show_file_history(self):
        items = self.selected_items()
        self.notifier.notify_observers(HISTORIES_SELECTED,
                                       [i.path for i in items])

class FileTreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, file_log, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        texts = file_log.split('\t')
        self.path = path = texts[2]
        self.setText(0, path)
        self.setText(1, texts[0])
        self.setText(2, texts[1])
