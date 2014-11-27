from __future__ import division, absolute_import, unicode_literals

import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt

from cola import core
from cola import cmds
from cola import qtutils
from cola.i18n import N_
from cola.widgets import defs
from cola.widgets.standard import Dialog
from cola.widgets.standard import DraggableTreeWidget
from cola.compat import ustr


def apply_patches():
    parent = qtutils.active_window()
    dlg = new_apply_patches(parent=parent)
    dlg.show()
    dlg.raise_()
    return dlg


def new_apply_patches(patches=None, parent=None):
    dlg = ApplyPatches(parent=parent)
    if patches:
        dlg.add_paths(patches)
    return dlg


def get_patches_from_paths(paths):
    paths = [core.decode(p) for p in paths]
    patches = [p for p in paths
                if core.isfile(p) and (
                    p.endswith('.patch') or p.endswith('.mbox'))]
    dirs = [p for p in paths if core.isdir(p)]
    dirs.sort()
    for d in dirs:
        patches.extend(get_patches_from_dir(d))
    return patches


def get_patches_from_mimedata(mimedata):
    urls = mimedata.urls()
    if not urls:
        return []
    paths = map(lambda x: ustr(x.path()), urls)
    return get_patches_from_paths(paths)


def get_patches_from_dir(path):
    """Find patches in a subdirectory"""
    patches = []
    for root, subdirs, files in core.walk(path):
        for name in [f for f in files if f.endswith('.patch')]:
            patches.append(core.decode(os.path.join(root, name)))
    return patches


class ApplyPatches(Dialog):

    def __init__(self, parent=None):
        super(ApplyPatches, self).__init__(parent=parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Apply Patches'))
        self.setAcceptDrops(True)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.curdir = core.getcwd()
        self.inner_drag = False

        self.usage = QtGui.QLabel()
        self.usage.setText(N_("""
            <p>
                Drag and drop or use the <strong>Add</strong> button to add
                patches to the list
            </p>
            """))

        self.tree = PatchTreeWidget(parent=self)
        self.tree.setHeaderHidden(True)

        self.add_button = qtutils.create_toolbutton(
                text=N_('Add'), icon=qtutils.add_icon(),
                tooltip=N_('Add patches (+)'))

        self.remove_button = qtutils.create_toolbutton(
                text=N_('Remove'), icon=qtutils.remove_icon(),
                tooltip=N_('Remove selected (Delete)'))

        self.apply_button = qtutils.create_button(
                text=N_('Apply'), icon=qtutils.apply_icon())

        self.close_button = qtutils.create_button(
                text=N_('Close'), icon=qtutils.close_icon())

        self.add_action = qtutils.add_action(self,
                N_('Add'), self.add_files, Qt.Key_Plus)

        self.remove_action = qtutils.add_action(self,
                N_('Remove'), self.tree.remove_selected,
                QtGui.QKeySequence.Delete, Qt.Key_Backspace, Qt.Key_Minus)

        self.top_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                       self.add_button, self.remove_button,
                                       qtutils.STRETCH, self.usage)

        self.bottom_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                          self.apply_button, qtutils.STRETCH,
                                          self.close_button)

        self.main_layout = qtutils.vbox(defs.margin, defs.spacing,
                                        self.top_layout, self.tree,
                                        self.bottom_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.add_button, self.add_files)
        qtutils.connect_button(self.remove_button, self.tree.remove_selected)
        qtutils.connect_button(self.apply_button, self.apply_patches)
        qtutils.connect_button(self.close_button, self.close)

        if not self.restore_state():
            self.resize(666, 420)

    def apply_patches(self):
        items = self.tree.items()
        if not items:
            return
        patches = [ustr(i.data(0, Qt.UserRole).toPyObject()) for i in items]
        cmds.do(cmds.ApplyPatches, patches)
        self.accept()

    def add_files(self):
        files = qtutils.open_files(N_('Select patch file(s)...'),
                                   directory=self.curdir,
                                   filter='Patches (*.patch *.mbox)')
        if not files:
            return
        files = [ustr(f) for f in files]
        self.curdir = os.path.dirname(files[0])
        self.add_paths([os.path.relpath(f) for f in files])

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


class PatchTreeWidget(DraggableTreeWidget):

    def __init__(self, parent=None):
        super(PatchTreeWidget, self).__init__(parent=parent)

    def add_paths(self, paths):
        patches = get_patches_from_paths(paths)
        if not patches:
            return
        items = []
        icon = qtutils.file_icon()
        for patch in patches:
            item = QtGui.QTreeWidgetItem()
            flags = item.flags() & ~Qt.ItemIsDropEnabled
            item.setFlags(flags)
            item.setIcon(0, icon)
            item.setText(0, os.path.basename(patch))
            item.setData(0, Qt.UserRole, QtCore.QVariant(patch))
            item.setToolTip(0, patch)
            items.append(item)
        self.addTopLevelItems(items)

    def remove_selected(self):
        idxs = self.selectedIndexes()
        rows = [idx.row() for idx in idxs]
        for row in reversed(sorted(rows)):
            self.invisibleRootItem().takeChild(row)
