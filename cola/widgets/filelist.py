from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Signal
from qtpy.QtCore import Qt

from .. import cmds
from .. import hotkeys
from .. import qtutils
from ..i18n import N_
from ..models import dag
from .standard import TreeWidget


class FileWidget(TreeWidget):
    files_selected = Signal(object)
    difftool_selected = Signal(object)
    histories_selected = Signal(object)
    grab_file = Signal(object)
    grab_file_from_parent = Signal(object)
    select_line_range_for_file = Signal(object)
    remark_toggled = Signal(object, object)

    def __init__(self, context, parent, remarks=False):
        TreeWidget.__init__(self, parent)
        self.context = context
        self._columns_initialized = False
        self.setHeaderLabels([N_('Filename'), '+', '-'])

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
        self.grab_file_from_parent_action = qtutils.add_action(
            self, N_('Grab File from Parent Commit...'), self._grab_file_from_parent
        )
        self.select_line_range_action = qtutils.add_action(
            self, N_('Trace Evolution of Line Range...'), self._select_line_range
        )
        if remarks:
            self.toggle_remark_actions = tuple(
                qtutils.add_action(
                    self,
                    r,
                    lambda remark=r: self.toggle_remark(remark),
                    hotkeys.hotkey(Qt.CTRL | getattr(Qt, 'Key_' + r)),
                )
                for r in map(str, range(10))
            )
        else:
            self.toggle_remark_actions = tuple()

        self.itemSelectionChanged.connect(self.selection_changed)

    def selection_changed(self):
        items = self.selected_items()
        self.files_selected.emit([i.path for i in items])

    def commits_selected(self, commits):
        if not commits:
            self.clear()
            return

        git = self.context.git
        paths = []

        if len(commits) > 1:
            # Get a list of changed files for a commit range.
            start_oid = commits[0].oid
            end = commits[-1].oid
            start = start_oid + '~'
            if end == dag.STAGE:
                status, out, _ = git.diff(
                    start, cached=True, z=True, numstat=True, no_renames=True
                )
            elif end == dag.WORKTREE:
                if start_oid == dag.STAGE:
                    status, out, _ = git.diff(z=True, numstat=True, no_renames=True)
                else:
                    status, out, _ = git.diff(
                        start, z=True, numstat=True, no_renames=True
                    )
            else:
                status, out, _ = git.diff(
                    start, end, z=True, numstat=True, no_renames=True
                )
            if status == 0:
                paths = [f for f in out.rstrip('\0').split('\0') if f]
        else:
            # Get the list of changed files in a single commit.
            commit = commits[0]
            oid = commit.oid
            # NOTE: The output from "git diff-files --numstat -z" is not equivalent
            # to the output of "git show --numstat -z". "git diff-files" does not
            # emit a NULL separator between each entry. That's why we use the
            # default output (without "-z") and split on newline instead.
            # This is also true for "git diff-index" as well.
            if oid == dag.STAGE:
                status, out, _ = git.diff_index(
                    'HEAD', cached=True, numstat=True, _readonly=True
                )
                if status == 0:
                    paths = [f for f in out.split('\n') if f]
            elif oid == dag.WORKTREE:
                status, out, _ = git.diff_files(numstat=True, _readonly=True)
                if status == 0:
                    paths = [f for f in out.split('\n') if f]
            else:
                status, out, _ = git.show(
                    oid,
                    format='',
                    numstat=True,
                    no_renames=True,
                    z=True,
                    _readonly=True,
                )
                if status == 0:
                    paths = [f for f in out.rstrip('\0').split('\0') if f]

        self.list_files(paths)

    def list_files(self, files_log):
        self.clear()
        if not files_log:
            return
        files = []
        for filename in files_log:
            item = FileTreeWidgetItem(filename)
            files.append(item)
        self.insertTopLevelItems(0, files)

    def _resize_columns(self):
        """Set columns to their initial size"""
        header_width = self.header().width() - 1
        metrics = QtGui.QFontMetrics(self.font())
        numbers_max = qtutils.fontmetrics_width(metrics, '12345678')  # Linux had 28,000,000+ LOC of code in 2020.
        numbers_width = min(numbers_max, header_width // 8 - 1)
        files_width = header_width - numbers_width * 2
        self.setColumnWidth(0, files_width)
        self.setColumnWidth(1, numbers_width)
        self.setColumnWidth(2, numbers_width)

    def showEvent(self, event):
        """Defer initializaztion of column widths"""
        super().showEvent(event)
        if not self._columns_initialized:
            self._columns_initialized = True
            self._resize_columns()

    def resizeEvent(self, event):
        """Defer initializaztion of column widths"""
        super().resizeEvent(event)
        self._resize_columns()

    def contextMenuEvent(self, event):
        menu = qtutils.create_menu(N_('Actions'), self)
        menu.addAction(self.select_line_range_action)
        menu.addSeparator()
        menu.addAction(self.grab_file_action)
        menu.addAction(self.grab_file_from_parent_action)
        menu.addAction(self.show_history_action)
        menu.addAction(self.launch_difftool_action)
        menu.addAction(self.launch_editor_action)
        if self.toggle_remark_actions:
            menu_toggle_remark = menu.addMenu(N_('Toggle remark of touching commits'))
            tuple(map(menu_toggle_remark.addAction, self.toggle_remark_actions))
        menu.exec_(self.mapToGlobal(event.pos()))

    def show_diff(self):
        self.difftool_selected.emit(self.selected_paths())

    def _grab_file(self):
        for path in self.selected_paths():
            self.grab_file.emit(path)

    def _grab_file_from_parent(self):
        for path in self.selected_paths():
            self.grab_file_from_parent.emit(path)

    def _select_line_range(self):
        """Emit a signal so that we can select the line range for the selected file"""
        paths = self.selected_paths()
        if paths:
            self.select_line_range_for_file.emit(paths[0])

    def selected_paths(self):
        return [i.path for i in self.selected_items()]

    def edit_paths(self):
        cmds.do(cmds.Edit, self.context, self.selected_paths())

    def show_history(self):
        items = self.selected_items()
        paths = [i.path for i in items]
        self.histories_selected.emit(paths)

    def toggle_remark(self, remark):
        items = self.selected_items()
        paths = tuple(i.path for i in items)
        self.remark_toggled.emit(remark, paths)


class FileTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, file_log, parent=None):
        QtWidgets.QTreeWidgetItem.__init__(self, parent)
        texts = file_log.split('\t')
        self.path = path = texts[2]
        self.setText(0, path)
        self.setText(1, texts[0])
        self.setText(2, texts[1])
