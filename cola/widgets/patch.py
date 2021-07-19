from __future__ import absolute_import, division, print_function, unicode_literals
import os
import re

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from ..i18n import N_
from ..qtutils import get
from .. import core
from .. import cmds
from .. import hotkeys
from .. import observable
from .. import icons
from .. import qtutils
from .standard import Dialog
from .standard import DraggableTreeWidget
from . import defs
from . import diff


def apply_patches(context):
    parent = qtutils.active_window()
    dlg = new_apply_patches(context, parent=parent)
    dlg.show()
    dlg.raise_()
    return dlg


def new_apply_patches(context, patches=None, parent=None):
    dlg = ApplyPatches(context, parent=parent)
    if patches:
        dlg.add_paths(patches)
    return dlg


def get_patches_from_paths(paths):
    paths = [core.decode(p) for p in paths]
    patches = [
        p
        for p in paths
        if core.isfile(p) and (p.endswith('.patch') or p.endswith('.mbox'))
    ]
    dirs = [p for p in paths if core.isdir(p)]
    dirs.sort()
    for d in dirs:
        patches.extend(get_patches_from_dir(d))
    return patches


def get_patches_from_mimedata(mimedata):
    urls = mimedata.urls()
    if not urls:
        return []
    paths = [x.path() for x in urls]
    return get_patches_from_paths(paths)


def get_patches_from_dir(path):
    """Find patches in a subdirectory"""
    patches = []
    for root, _, files in core.walk(path):
        for name in [f for f in files if f.endswith('.patch')]:
            patches.append(core.decode(os.path.join(root, name)))
    return patches


class ApplyPatches(Dialog):
    def __init__(self, context, parent=None):
        super(ApplyPatches, self).__init__(parent=parent)
        self.context = context
        self.setWindowTitle(N_('Apply Patches'))
        self.setAcceptDrops(True)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.curdir = core.getcwd()
        self.inner_drag = False

        self.usage = QtWidgets.QLabel()
        self.usage.setText(
            N_(
                """
            <p>
                Drag and drop or use the <strong>Add</strong> button to add
                patches to the list
            </p>
            """
            )
        )

        self.tree = PatchTreeWidget(parent=self)
        self.tree.setHeaderHidden(True)
        # pylint: disable=no-member
        self.tree.itemSelectionChanged.connect(self._tree_selection_changed)

        self.notifier = notifier = observable.Observable()
        self.diffwidget = diff.DiffWidget(context, notifier, self, is_commit=True)

        self.add_button = qtutils.create_toolbutton(
            text=N_('Add'), icon=icons.add(), tooltip=N_('Add patches (+)')
        )

        self.remove_button = qtutils.create_toolbutton(
            text=N_('Remove'),
            icon=icons.remove(),
            tooltip=N_('Remove selected (Delete)'),
        )

        self.apply_button = qtutils.create_button(text=N_('Apply'), icon=icons.ok())

        self.close_button = qtutils.close_button()

        self.add_action = qtutils.add_action(
            self, N_('Add'), self.add_files, hotkeys.ADD_ITEM
        )

        self.remove_action = qtutils.add_action(
            self,
            N_('Remove'),
            self.tree.remove_selected,
            hotkeys.DELETE,
            hotkeys.BACKSPACE,
            hotkeys.REMOVE_ITEM,
        )

        self.top_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.add_button,
            self.remove_button,
            qtutils.STRETCH,
            self.usage,
        )

        self.bottom_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.close_button,
            qtutils.STRETCH,
            self.apply_button,
        )

        self.splitter = qtutils.splitter(Qt.Vertical, self.tree, self.diffwidget)

        self.main_layout = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.top_layout,
            self.splitter,
            self.bottom_layout,
        )
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.add_button, self.add_files)
        qtutils.connect_button(self.remove_button, self.tree.remove_selected)
        qtutils.connect_button(self.apply_button, self.apply_patches)
        qtutils.connect_button(self.close_button, self.close)

        self.init_state(None, self.resize, 666, 420)

    def apply_patches(self):
        items = self.tree.items()
        if not items:
            return
        context = self.context
        patches = [i.data(0, Qt.UserRole) for i in items]
        cmds.do(cmds.ApplyPatches, context, patches)
        self.accept()

    def add_files(self):
        files = qtutils.open_files(
            N_('Select patch file(s)...'),
            directory=self.curdir,
            filters='Patches (*.patch *.mbox)',
        )
        if not files:
            return
        self.curdir = os.path.dirname(files[0])
        self.add_paths([core.relpath(f) for f in files])

    def dragEnterEvent(self, event):
        """Accepts drops if the mimedata contains patches"""
        super(ApplyPatches, self).dragEnterEvent(event)
        patches = get_patches_from_mimedata(event.mimeData())
        if patches:
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Add dropped patches"""
        event.accept()
        patches = get_patches_from_mimedata(event.mimeData())
        if not patches:
            return
        self.add_paths(patches)

    def add_paths(self, paths):
        self.tree.add_paths(paths)

    def _tree_selection_changed(self):
        items = self.tree.selected_items()
        if not items:
            return
        item = items[-1]  # take the last item
        path = item.data(0, Qt.UserRole)
        if not core.exists(path):
            return
        commit = parse_patch(path)
        self.diffwidget.set_details(
            commit.oid, commit.author, commit.email, commit.date, commit.summary
        )
        self.diffwidget.set_diff(commit.diff)

    def export_state(self):
        """Export persistent settings"""
        state = super(ApplyPatches, self).export_state()
        state['sizes'] = get(self.splitter)
        return state

    def apply_state(self, state):
        """Apply persistent settings"""
        result = super(ApplyPatches, self).apply_state(state)
        try:
            self.splitter.setSizes(state['sizes'])
        except (AttributeError, KeyError, ValueError, TypeError):
            pass
        return result


# pylint: disable=too-many-ancestors
class PatchTreeWidget(DraggableTreeWidget):
    def add_paths(self, paths):
        patches = get_patches_from_paths(paths)
        if not patches:
            return
        items = []
        icon = icons.file_text()
        for patch in patches:
            item = QtWidgets.QTreeWidgetItem()
            flags = item.flags() & ~Qt.ItemIsDropEnabled
            item.setFlags(flags)
            item.setIcon(0, icon)
            item.setText(0, os.path.basename(patch))
            item.setData(0, Qt.UserRole, patch)
            item.setToolTip(0, patch)
            items.append(item)
        self.addTopLevelItems(items)

    def remove_selected(self):
        idxs = self.selectedIndexes()
        rows = [idx.row() for idx in idxs]
        for row in reversed(sorted(rows)):
            self.invisibleRootItem().takeChild(row)


class Commit(object):
    """Container for commit details"""

    def __init__(self):
        self.content = ''
        self.author = ''
        self.email = ''
        self.oid = ''
        self.summary = ''
        self.diff = ''
        self.date = ''


def parse_patch(path):
    content = core.read(path)
    commit = Commit()
    parse(content, commit)
    return commit


def parse(content, commit):
    """Parse commit details from a patch"""
    from_rgx = re.compile(r'^From (?P<oid>[a-f0-9]{40}) .*$')
    author_rgx = re.compile(r'^From: (?P<author>[^<]+) <(?P<email>[^>]+)>$')
    date_rgx = re.compile(r'^Date: (?P<date>.*)$')
    subject_rgx = re.compile(r'^Subject: (?P<summary>.*)$')

    commit.content = content

    lines = content.splitlines()
    for idx, line in enumerate(lines):
        match = from_rgx.match(line)
        if match:
            commit.oid = match.group('oid')
            continue

        match = author_rgx.match(line)
        if match:
            commit.author = match.group('author')
            commit.email = match.group('email')
            continue

        match = date_rgx.match(line)
        if match:
            commit.date = match.group('date')
            continue

        match = subject_rgx.match(line)
        if match:
            commit.summary = match.group('summary')
            commit.diff = '\n'.join(lines[idx + 1 :])
            break
