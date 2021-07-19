from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..i18n import N_
from ..qtutils import get
from .. import cmds
from .. import gitcmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from .browse import GitTreeWidget
from .browse import GitFileTreeModel
from . import defs
from . import standard


def browse_recent_files(context):
    dialog = RecentFiles(context, parent=qtutils.active_window())
    dialog.show()
    return dialog


class UpdateFileListThread(QtCore.QThread):
    result = Signal(object)

    def __init__(self, context, count):
        QtCore.QThread.__init__(self)
        self.context = context
        self.count = count

    def run(self):
        context = self.context
        ref = 'HEAD~%d' % self.count
        filenames = gitcmds.diff_index_filenames(context, ref)
        self.result.emit(filenames)


class RecentFiles(standard.Dialog):
    def __init__(self, context, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.context = context
        self.setWindowTitle(N_('Recently Modified Files'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        count = 8
        self.update_thread = UpdateFileListThread(context, count)

        self.count = standard.SpinBox(
            value=count, maxi=10000, suffix=N_(' commits ago')
        )

        self.count_label = QtWidgets.QLabel()
        self.count_label.setText(N_('Showing changes since'))

        self.refresh_button = qtutils.refresh_button(enabled=False)

        self.tree = GitTreeWidget(parent=self)
        self.tree_model = GitFileTreeModel(self)
        self.tree.setModel(self.tree_model)

        self.expand_button = qtutils.create_button(
            text=N_('Expand all'), icon=icons.unfold()
        )

        self.collapse_button = qtutils.create_button(
            text=N_('Collapse all'), icon=icons.fold()
        )

        self.edit_button = qtutils.edit_button(enabled=False, default=True)
        self.close_button = qtutils.close_button()

        self.top_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.count_label,
            self.count,
            qtutils.STRETCH,
            self.refresh_button,
        )

        self.button_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.close_button,
            qtutils.STRETCH,
            self.expand_button,
            self.collapse_button,
            self.edit_button,
        )

        self.main_layout = qtutils.vbox(
            defs.margin, defs.spacing, self.top_layout, self.tree, self.button_layout
        )
        self.setLayout(self.main_layout)

        # pylint: disable=no-member
        self.tree.selection_changed.connect(self.tree_selection_changed)
        self.tree.path_chosen.connect(self.edit_file)
        self.count.valueChanged.connect(self.count_changed)
        self.count.editingFinished.connect(self.refresh)

        thread = self.update_thread
        thread.result.connect(self.set_filenames, type=Qt.QueuedConnection)

        qtutils.connect_button(self.refresh_button, self.refresh)
        qtutils.connect_button(self.expand_button, self.tree.expandAll)
        qtutils.connect_button(self.collapse_button, self.tree.collapseAll)
        qtutils.connect_button(self.close_button, self.accept)
        qtutils.connect_button(self.edit_button, self.edit_selected)

        qtutils.add_action(self, N_('Refresh'), self.refresh, hotkeys.REFRESH)

        self.update_thread.start()
        self.init_size(parent=parent)

    def edit_selected(self):
        filenames = self.tree.selected_files()
        if not filenames:
            return
        self.edit_files(filenames)

    def edit_files(self, filenames):
        cmds.do(cmds.Edit, self.context, filenames)

    def edit_file(self, filename):
        self.edit_files([filename])

    def refresh(self):
        self.refresh_button.setEnabled(False)
        self.count.setEnabled(False)
        self.tree_model.clear()
        self.tree.setEnabled(False)

        self.update_thread.count = get(self.count)
        self.update_thread.start()

    def count_changed(self, _value):
        self.refresh_button.setEnabled(True)

    def tree_selection_changed(self):
        """Update actions based on the current selection"""
        filenames = self.tree.selected_files()
        self.edit_button.setEnabled(bool(filenames))

    def set_filenames(self, filenames):
        self.count.setEnabled(True)
        self.tree.setEnabled(True)
        self.tree_model.clear()
        self.tree_model.add_files(filenames)
        self.tree.expandAll()
        self.tree.select_first_file()
        self.tree.setFocus()
