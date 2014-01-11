from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt, SIGNAL

from cola.i18n import N_
from cola.git import git
from cola.git import STDOUT
from cola.widgets.standard import TreeWidget
from cola.widgets.diff import COMMITS_SELECTED
from cola.widgets.diff import FILES_SELECTED

class FileWidget(TreeWidget):

    def __init__(self, notifier, parent):
        TreeWidget.__init__(self, parent)
        self.notifier = notifier
        self.setHeaderLabels([N_('File Name'), N_('Addition'), N_('Deletion')])
        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.selection_changed)


    def selection_changed(self):
        items = self.selected_items()
        self.notifier.notify_observers(FILES_SELECTED,
                                       [i.file_name for i in items])

    def commits_selected(self, commits):
        if len(commits) != 1:
            return
        commit = commits[0]
        sha1 = commit.sha1
        files_log = git.show(sha1, "--numstat", "--oneline")[STDOUT].splitlines()[1:]
        self.list_files(files_log)

    def list_files(self, files_log):
        files = []
        for f in files_log:
            file = FileTreeWidgetItem(f)
            files.append(file)
        self.clear()
        self.insertTopLevelItems(0, files)

    def adjust_columns(self):
        width = self.width()-20
        zero = width*2/3
        onetwo = width/6
        self.setColumnWidth(0, zero)
        self.setColumnWidth(1, onetwo)
        self.setColumnWidth(2, onetwo)

    def show(self):
        self.adjust_columns()

    def resizeEvent(self, e):
        self.adjust_columns()


class FileTreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, file_log, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        texts = file_log.split("\t")
        self.file_name = texts[2]
        self.setText(0, self.file_name) # file name
        self.setText(1, texts[0]) # addition
        self.setText(2, texts[1]) # deletion
