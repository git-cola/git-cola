import sys
import re
from argparse import ArgumentParser
from functools import partial, reduce

from cola import app  # prints a message if Qt cannot be found
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

# pylint: disable=ungrouped-imports
from cola import core
from cola import difftool
from cola import hotkeys
from cola import icons
from cola import qtutils
from cola import utils
from cola.i18n import N_
from cola.models import dag
from cola.models import prefs
from cola.widgets import defs
from cola.widgets import filelist
from cola.widgets import diff
from cola.widgets import standard
from cola.widgets import text


PICK = 'pick'
REWORD = 'reword'
EDIT = 'edit'
FIXUP = 'fixup'
SQUASH = 'squash'
UPDATE_REF = 'update-ref'
EXEC = 'exec'
COMMANDS = (
    PICK,
    REWORD,
    EDIT,
    FIXUP,
    SQUASH,
)
COMMAND_IDX = {cmd_: idx_ for idx_, cmd_ in enumerate(COMMANDS)}
ABBREV = {
    'p': PICK,
    'r': REWORD,
    'e': EDIT,
    'f': FIXUP,
    's': SQUASH,
    'x': EXEC,
    'u': UPDATE_REF,
}


def main():
    """Start a git-cola-sequence-editor session"""
    args = parse_args()
    context = app.application_init(args)
    view = new_window(context, args.filename)
    app.application_run(context, view, start=view.start, stop=stop)
    return view.status


def stop(_context, _view):
    """All done, cleanup"""
    QtCore.QThreadPool.globalInstance().waitForDone()


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        'filename', metavar='<filename>', help='git-rebase-todo file to edit'
    )
    app.add_common_arguments(parser)
    return parser.parse_args()


def new_window(context, filename):
    window = MainWindow(context)
    editor = Editor(context, filename, parent=window)
    window.set_editor(editor)
    return window


def unabbrev(cmd):
    """Expand shorthand commands into their full name"""
    return ABBREV.get(cmd, cmd)


class MainWindow(standard.MainWindow):
    """The main git-cola application window"""

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.status = 1
        self.editor = None
        default_title = '%s - git cola sequence editor' % core.getcwd()
        title = core.getenv('GIT_COLA_SEQ_EDITOR_TITLE', default_title)
        self.setWindowTitle(title)

        self.show_help_action = qtutils.add_action(
            self, N_('Show Help'), partial(show_help, context), hotkeys.QUESTION
        )

        self.menubar = QtWidgets.QMenuBar(self)
        self.help_menu = self.menubar.addMenu(N_('Help'))
        self.help_menu.addAction(self.show_help_action)
        self.setMenuBar(self.menubar)

        qtutils.add_close_action(self)
        self.init_state(context.settings, self.init_window_size)

    def init_window_size(self):
        """Set the window size on the first initial view"""
        if utils.is_darwin():
            width, height = qtutils.desktop_size()
            self.resize(width, height)
        else:
            self.showMaximized()

    def set_editor(self, editor):
        self.editor = editor
        self.setCentralWidget(editor)
        editor.exit.connect(self.exit)
        editor.setFocus()

    def start(self, _context, _view):
        self.editor.start()

    def exit(self, status):
        self.status = status
        self.close()


class Editor(QtWidgets.QWidget):
    exit = Signal(int)

    def __init__(self, context, filename, parent=None):
        super().__init__(parent)

        self.widget_version = 1
        self.status = 1
        self.context = context
        self.filename = filename
        self.comment_char = comment_char = prefs.comment_char(context)
        self.cancel_action = core.getenv('GIT_COLA_SEQ_EDITOR_CANCEL_ACTION', 'abort')

        self.diff = diff.DiffWidget(context, self)
        self.tree = RebaseTreeWidget(context, comment_char, self)
        self.filewidget = filelist.FileWidget(context, self)
        self.setFocusProxy(self.tree)

        self.rebase_button = qtutils.create_button(
            text=core.getenv('GIT_COLA_SEQ_EDITOR_ACTION', N_('Rebase')),
            tooltip=N_('Accept changes and rebase\nShortcut: Ctrl+Enter'),
            icon=icons.ok(),
            default=True,
        )

        self.extdiff_button = qtutils.create_button(
            text=N_('Launch Diff Tool'),
            tooltip=N_('Launch external diff tool\nShortcut: Ctrl+D'),
        )
        self.extdiff_button.setEnabled(False)

        self.help_button = qtutils.create_button(
            text=N_('Help'), tooltip=N_('Show help\nShortcut: ?'), icon=icons.question()
        )

        self.cancel_button = qtutils.create_button(
            text=N_('Cancel'),
            tooltip=N_('Cancel rebase\nShortcut: Ctrl+Q'),
            icon=icons.close(),
        )

        top = qtutils.splitter(Qt.Horizontal, self.tree, self.filewidget)
        top.setSizes([75, 25])

        main_split = qtutils.splitter(Qt.Vertical, top, self.diff)
        main_split.setSizes([25, 75])

        controls_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.cancel_button,
            qtutils.STRETCH,
            self.help_button,
            self.extdiff_button,
            self.rebase_button,
        )
        layout = qtutils.vbox(defs.no_margin, defs.spacing, main_split, controls_layout)
        self.setLayout(layout)

        self.action_rebase = qtutils.add_action(
            self, N_('Rebase'), self.rebase, hotkeys.CTRL_RETURN, hotkeys.CTRL_ENTER
        )

        self.tree.commits_selected.connect(self.commits_selected)
        self.tree.commits_selected.connect(self.filewidget.commits_selected)
        self.tree.commits_selected.connect(self.diff.commits_selected)
        self.tree.external_diff.connect(self.external_diff)

        self.filewidget.files_selected.connect(self.diff.files_selected)

        qtutils.connect_button(self.rebase_button, self.rebase)
        qtutils.connect_button(self.extdiff_button, self.external_diff)
        qtutils.connect_button(self.help_button, partial(show_help, context))
        qtutils.connect_button(self.cancel_button, self.cancel)

    def start(self):
        insns = core.read(self.filename)
        self.parse_sequencer_instructions(insns)

    # signal callbacks
    def commits_selected(self, commits):
        self.extdiff_button.setEnabled(bool(commits))

    # helpers
    def parse_sequencer_instructions(self, insns):
        idx = 1
        re_comment_char = re.escape(self.comment_char)
        exec_rgx = re.compile(r'^\s*(%s)?\s*(x|exec)\s+(.+)$' % re_comment_char)
        update_ref_rgx = re.compile(
            r'^\s*(%s)?\s*(u|update-ref)\s+(.+)$' % re_comment_char
        )
        # The upper bound of 40 below must match git.OID_LENGTH.
        # We'll have to update this to the new hash length when that happens.
        pick_rgx = re.compile(
            (
                r'^\s*(%s)?\s*'
                + r'(p|pick|r|reword|e|edit|f|fixup|s|squash)'
                + r'\s+([0-9a-f]{7,40})'
                + r'\s+(.+)$'
            )
            % re_comment_char
        )
        for line in insns.splitlines():
            match = pick_rgx.match(line)
            if match:
                enabled = match.group(1) is None
                command = unabbrev(match.group(2))
                oid = match.group(3)
                summary = match.group(4)
                self.tree.add_item(idx, enabled, command, oid=oid, summary=summary)
                idx += 1
                continue
            match = exec_rgx.match(line)
            if match:
                enabled = match.group(1) is None
                command = unabbrev(match.group(2))
                cmdexec = match.group(3)
                self.tree.add_item(idx, enabled, command, cmdexec=cmdexec)
                idx += 1
                continue
            match = update_ref_rgx.match(line)
            if match:
                enabled = match.group(1) is None
                command = unabbrev(match.group(2))
                branch = match.group(3)
                self.tree.add_item(idx, enabled, command, branch=branch)
                idx += 1
                continue

        self.tree.decorate(self.tree.items())
        self.tree.refit()
        self.tree.select_first()

    # actions
    def cancel(self):
        if self.cancel_action == 'save':
            status = self.save('')
        else:
            status = 1

        self.status = status
        self.exit.emit(status)

    def rebase(self):
        lines = [item.value() for item in self.tree.items()]
        sequencer_instructions = '\n'.join(lines) + '\n'
        status = self.save(sequencer_instructions)
        self.status = status
        self.exit.emit(status)

    def save(self, string):
        """Save the instruction sheet"""
        try:
            core.write(self.filename, string)
            status = 0
        except (OSError, ValueError) as exc:
            msg, details = utils.format_exception(exc)
            sys.stderr.write(msg + '\n\n' + details)
            status = 128
        return status

    def external_diff(self):
        items = self.tree.selected_items()
        if not items:
            return
        item = items[0]
        difftool.diff_expression(self.context, self, item.oid + '^!', hide_expr=True)


# pylint: disable=too-many-ancestors
class RebaseTreeWidget(standard.DraggableTreeWidget):
    commits_selected = Signal(object)
    external_diff = Signal()
    move_rows = Signal(object, object)

    def __init__(self, context, comment_char, parent):
        super().__init__(parent=parent)
        self.context = context
        self.comment_char = comment_char
        # header
        self.setHeaderLabels([
            N_('#'),
            N_('Enabled'),
            N_('Command'),
            N_('SHA-1'),
            N_('Summary'),
        ])
        self.header().setStretchLastSection(True)
        self.setColumnCount(5)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # actions
        self.copy_oid_action = qtutils.add_action(
            self, N_('Copy SHA-1'), self.copy_oid, QtGui.QKeySequence.Copy
        )

        self.external_diff_action = qtutils.add_action(
            self, N_('Launch Diff Tool'), self.external_diff.emit, hotkeys.DIFF
        )

        self.toggle_enabled_action = qtutils.add_action(
            self, N_('Toggle Enabled'), self.toggle_enabled, hotkeys.PRIMARY_ACTION
        )

        self.action_pick = qtutils.add_action(
            self, N_('Pick'), lambda: self.set_selected_to(PICK), *hotkeys.REBASE_PICK
        )

        self.action_reword = qtutils.add_action(
            self,
            N_('Reword'),
            lambda: self.set_selected_to(REWORD),
            *hotkeys.REBASE_REWORD,
        )

        self.action_edit = qtutils.add_action(
            self, N_('Edit'), lambda: self.set_selected_to(EDIT), *hotkeys.REBASE_EDIT
        )

        self.action_fixup = qtutils.add_action(
            self,
            N_('Fixup'),
            lambda: self.set_selected_to(FIXUP),
            *hotkeys.REBASE_FIXUP,
        )

        self.action_squash = qtutils.add_action(
            self,
            N_('Squash'),
            lambda: self.set_selected_to(SQUASH),
            *hotkeys.REBASE_SQUASH,
        )

        self.action_shift_down = qtutils.add_action(
            self, N_('Shift Down'), self.shift_down, hotkeys.MOVE_DOWN_TERTIARY
        )

        self.action_shift_up = qtutils.add_action(
            self, N_('Shift Up'), self.shift_up, hotkeys.MOVE_UP_TERTIARY
        )

        # pylint: disable=no-member
        self.itemChanged.connect(self.item_changed)
        self.itemSelectionChanged.connect(self.selection_changed)
        self.move_rows.connect(self.move)
        self.items_moved.connect(self.decorate)

    def add_item(
        self, idx, enabled, command, oid='', summary='', cmdexec='', branch=''
    ):
        comment_char = self.comment_char
        item = RebaseTreeWidgetItem(
            idx,
            enabled,
            command,
            oid=oid,
            summary=summary,
            cmdexec=cmdexec,
            branch=branch,
            comment_char=comment_char,
        )
        self.invisibleRootItem().addChild(item)

    def decorate(self, items):
        for item in items:
            item.decorate(self)

    def refit(self):
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)
        self.resizeColumnToContents(4)

    # actions
    def item_changed(self, item, column):
        if column == item.ENABLED_COLUMN:
            self.validate()

    def validate(self):
        invalid_first_choice = {FIXUP, SQUASH}
        for item in self.items():
            if item.is_enabled() and item.is_commit():
                if item.command in invalid_first_choice:
                    item.reset_command(PICK)
                break

    def set_selected_to(self, command):
        for i in self.selected_items():
            i.reset_command(command)
        self.validate()

    def set_command(self, item, command):
        item.reset_command(command)
        self.validate()

    def copy_oid(self):
        item = self.selected_item()
        if item is None:
            return
        clipboard = item.oid or item.cmdexec
        qtutils.set_clipboard(clipboard)

    def selection_changed(self):
        item = self.selected_item()
        if item is None or not item.is_commit():
            return
        context = self.context
        oid = item.oid
        params = dag.DAG(oid, 2)
        repo = dag.RepoReader(context, params)
        commits = []
        for commit in repo.get():
            commits.append(commit)
        if commits:
            commits = commits[-1:]
        self.commits_selected.emit(commits)

    def toggle_enabled(self):
        items = self.selected_items()
        logic_or = reduce(lambda res, item: res or item.is_enabled(), items, False)
        for item in items:
            item.set_enabled(not logic_or)

    def select_first(self):
        items = self.items()
        if not items:
            return
        idx = self.model().index(0, 0)
        if idx.isValid():
            self.setCurrentIndex(idx)

    def shift_down(self):
        sel_items = self.selected_items()
        all_items = self.items()
        sel_idx = sorted([all_items.index(item) for item in sel_items])
        if not sel_idx:
            return
        idx = sel_idx[0] + 1
        if not (
            idx > len(all_items) - len(sel_items)
            or all_items[sel_idx[-1]] is all_items[-1]
        ):
            self.move_rows.emit(sel_idx, idx)

    def shift_up(self):
        sel_items = self.selected_items()
        all_items = self.items()
        sel_idx = sorted([all_items.index(item) for item in sel_items])
        if not sel_idx:
            return
        idx = sel_idx[0] - 1
        if idx >= 0:
            self.move_rows.emit(sel_idx, idx)

    def move(self, src_idxs, dst_idx):
        moved_items = []
        src_base = sorted(src_idxs)[0]
        for idx in reversed(sorted(src_idxs)):
            item = self.invisibleRootItem().takeChild(idx)
            moved_items.insert(0, [dst_idx + (idx - src_base), item])

        for item in moved_items:
            self.invisibleRootItem().insertChild(item[0], item[1])
            self.setCurrentItem(item[1])

        if moved_items:
            moved_items = [item[1] for item in moved_items]
            # If we've moved to the top then we need to re-decorate all items.
            # Otherwise, we can decorate just the new items.
            if dst_idx == 0:
                self.decorate(self.items())
            else:
                self.decorate(moved_items)

            for item in moved_items:
                item.setSelected(True)
        self.validate()

    # Qt events

    def dropEvent(self, event):
        super().dropEvent(event)
        self.validate()

    def contextMenuEvent(self, event):
        items = self.selected_items()
        menu = qtutils.create_menu(N_('Actions'), self)
        menu.addAction(self.action_pick)
        menu.addAction(self.action_reword)
        menu.addAction(self.action_edit)
        menu.addAction(self.action_fixup)
        menu.addAction(self.action_squash)
        menu.addSeparator()
        menu.addAction(self.toggle_enabled_action)
        menu.addSeparator()
        menu.addAction(self.copy_oid_action)
        if len(items) > 1:
            self.copy_oid_action.setDisabled(True)
        menu.addAction(self.external_diff_action)
        if len(items) > 1:
            self.external_diff_action.setDisabled(True)
        menu.exec_(self.mapToGlobal(event.pos()))


class ComboBox(QtWidgets.QComboBox):
    validate = Signal()


class RebaseTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    ENABLED_COLUMN = 1
    COMMAND_COLUMN = 2
    OID_LENGTH = 7

    def __init__(
        self,
        idx,
        enabled,
        command,
        oid='',
        summary='',
        cmdexec='',
        branch='',
        comment_char='#',
        parent=None,
    ):
        QtWidgets.QTreeWidgetItem.__init__(self, parent)
        self.combo = None
        self.command = command
        self.idx = idx
        self.oid = oid
        self.summary = summary
        self.cmdexec = cmdexec
        self.branch = branch
        self.comment_char = comment_char

        # if core.abbrev is set to a higher value then we will notice by
        # simply tracking the longest oid we've seen
        oid_len = self.__class__.OID_LENGTH
        self.__class__.OID_LENGTH = max(len(oid), oid_len)

        self.setText(0, '%02d' % idx)
        self.set_enabled(enabled)
        # checkbox on 1
        # combo box on 2
        if self.is_exec():
            self.setText(3, '')
            self.setText(4, cmdexec)
        elif self.is_update_ref():
            self.setText(3, '')
            self.setText(4, branch)
        else:
            self.setText(3, oid)
            self.setText(4, summary)

        flags = self.flags() | Qt.ItemIsUserCheckable
        flags = flags | Qt.ItemIsDragEnabled
        flags = flags & ~Qt.ItemIsDropEnabled
        self.setFlags(flags)

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return self.oid

    def copy(self):
        return self.__class__(
            self.idx,
            self.is_enabled(),
            self.command,
            oid=self.oid,
            summary=self.summary,
            cmdexec=self.cmdexec,
            branch=self.branch,
            comment_char=self.comment_char,
        )

    def decorate(self, parent):
        if self.is_exec():
            items = [EXEC]
            idx = 0
        elif self.is_update_ref():
            items = [UPDATE_REF]
            idx = 0
        else:
            items = COMMANDS
            idx = COMMAND_IDX[self.command]
        combo = self.combo = ComboBox()
        combo.setEditable(False)
        combo.addItems(items)
        combo.setCurrentIndex(idx)
        combo.setEnabled(self.is_commit())

        signal = combo.currentIndexChanged
        # pylint: disable=no-member
        signal.connect(lambda x: self.set_command_and_validate(combo))
        combo.validate.connect(parent.validate)

        parent.setItemWidget(self, self.COMMAND_COLUMN, combo)

    def is_exec(self):
        return self.command == EXEC

    def is_update_ref(self):
        return self.command == UPDATE_REF

    def is_commit(self):
        return bool(
            not (self.is_exec() or self.is_update_ref()) and self.oid and self.summary
        )

    def value(self):
        """Return the serialized representation of an item"""
        if self.is_enabled():
            comment = ''
        else:
            comment = self.comment_char + ' '
        if self.is_exec():
            return f'{comment}{self.command} {self.cmdexec}'
        if self.is_update_ref():
            return f'{comment}{self.command} {self.branch}'
        return f'{comment}{self.command} {self.oid} {self.summary}'

    def is_enabled(self):
        return self.checkState(self.ENABLED_COLUMN) == Qt.Checked

    def set_enabled(self, enabled):
        self.setCheckState(self.ENABLED_COLUMN, enabled and Qt.Checked or Qt.Unchecked)

    def toggle_enabled(self):
        self.set_enabled(not self.is_enabled())

    def set_command(self, command):
        """Set the item to a different command, no-op for exec items"""
        if self.is_exec():
            return
        self.command = command

    def refresh(self):
        """Update the view to match the updated state"""
        if self.is_commit():
            command = self.command
            self.combo.setCurrentIndex(COMMAND_IDX[command])

    def reset_command(self, command):
        """Set and refresh the item in one shot"""
        self.set_command(command)
        self.refresh()

    def set_command_and_validate(self, combo):
        command = COMMANDS[combo.currentIndex()]
        self.set_command(command)
        self.combo.validate.emit()


def show_help(context):
    help_text = N_(
        """
Commands
--------
pick = use commit
reword = use commit, but edit the commit message
edit = use commit, but stop for amending
squash = use commit, but meld into previous commit
fixup = like "squash", but discard this commit's log message
exec = run command (the rest of the line) using shell
update-ref = update branches that point to commits

These lines can be re-ordered; they are executed from top to bottom.

If you disable a line here THAT COMMIT WILL BE LOST.

However, if you disable everything, the rebase will be aborted.

Keyboard Shortcuts
------------------
? = show help
j = move down
k = move up
J = shift row down
K = shift row up

1, p = pick
2, r = reword
3, e = edit
4, f = fixup
5, s = squash
spacebar = toggle enabled

ctrl+enter = accept changes and rebase
ctrl+q     = cancel and abort the rebase
ctrl+d     = launch difftool
"""
    )
    title = N_('Help - git-cola-sequence-editor')
    return text.text_dialog(context, help_text, title)
