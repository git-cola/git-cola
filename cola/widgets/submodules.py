"""Provides widgets related to submodules"""
from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import cmds
from .. import compat
from .. import core
from .. import qtutils
from .. import icons
from ..i18n import N_
from ..widgets import defs
from ..widgets import standard
from ..widgets import text


def add_submodule(context, parent):
    """Add a new submodule"""
    dlg = AddSubmodule(parent)
    dlg.show()
    if dlg.exec_() == standard.Dialog.Accepted:
        cmd = dlg.get(context)
        cmd.do()


class SubmodulesWidget(QtWidgets.QFrame):
    def __init__(self, context, parent):
        super(SubmodulesWidget, self).__init__(parent)
        self.context = context
        self.setToolTip(N_('Submodules'))

        self.tree = SubmodulesTreeWidget(context, parent=self)
        self.setFocusProxy(self.tree)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing, self.tree)
        self.setLayout(self.main_layout)

        # Titlebar buttons
        self.add_button = qtutils.create_action_button(
            tooltip=N_('Add Submodule'), icon=icons.add()
        )
        self.refresh_button = qtutils.create_action_button(
            tooltip=N_('Refresh'), icon=icons.sync()
        )

        self.open_parent_button = qtutils.create_action_button(
            tooltip=N_('Open Parent'), icon=icons.repo()
        )

        self.button_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.add_button,
            self.open_parent_button,
            self.refresh_button,
        )
        self.corner_widget = QtWidgets.QWidget(self)
        self.corner_widget.setLayout(self.button_layout)
        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.corner_widget)

        # Connections
        qtutils.connect_button(self.add_button, self.add_submodule)
        qtutils.connect_button(self.refresh_button, self.refresh)
        qtutils.connect_button(
            self.open_parent_button, cmds.run(cmds.OpenParentRepo, context)
        )

    def refresh(self):
        self.context.model.update_submodules_list()

    def add_submodule(self):
        add_submodule(self.context, self)


class AddSubmodule(standard.Dialog):
    """Add a new submodule"""

    def __init__(self, parent):
        super(AddSubmodule, self).__init__(parent=parent)

        hint = N_('git://git.example.com/repo.git')
        tooltip = N_('Submodule URL (can be relative, ex: ../repo.git)')
        self.url_text = text.HintedDefaultLineEdit(hint, tooltip=tooltip, parent=self)

        hint = N_('path/to/submodule')
        tooltip = N_('Submodule path within the current repository (optional)')
        self.path_text = text.HintedDefaultLineEdit(hint, tooltip=tooltip, parent=self)

        hint = N_('Branch name')
        tooltip = N_('Submodule branch to track (optional)')
        self.branch_text = text.HintedDefaultLineEdit(
            hint, tooltip=tooltip, parent=self
        )

        self.depth_spinbox = standard.SpinBox(
            mini=0, maxi=compat.maxint, value=0, parent=self
        )
        self.depth_spinbox.setToolTip(
            N_(
                'Create a shallow clone with history truncated to the '
                'specified number of revisions.  0 performs a full clone.'
            )
        )

        hint = N_('Reference URL')
        tooltip = N_('Reference repository to use when cloning (optional)')
        self.reference_text = text.HintedDefaultLineEdit(
            hint, tooltip=tooltip, parent=self
        )

        self.add_button = qtutils.ok_button(N_('Add Submodule'), enabled=False)
        self.close_button = qtutils.close_button()

        self.form_layout = qtutils.form(
            defs.no_margin,
            defs.button_spacing,
            (N_('URL'), self.url_text),
            (N_('Path'), self.path_text),
            (N_('Branch'), self.branch_text),
            (N_('Depth'), self.depth_spinbox),
            (N_('Reference Repository'), self.reference_text),
        )
        self.button_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            qtutils.STRETCH,
            self.add_button,
            self.close_button,
        )

        self.main_layout = qtutils.vbox(
            defs.large_margin, defs.spacing, self.form_layout, self.button_layout
        )
        self.setLayout(self.main_layout)
        self.init_size(parent=qtutils.active_window())
        # pylint: disable=no-member
        self.url_text.textChanged.connect(lambda x: self._update_widgets())
        qtutils.connect_button(self.add_button, self.accept)
        qtutils.connect_button(self.close_button, self.close)

    def _update_widgets(self):
        value = self.url_text.value()
        self.add_button.setEnabled(bool(value))

    def get(self, context):
        return cmds.SubmoduleAdd(
            context,
            self.url_text.value(),
            self.path_text.value(),
            self.branch_text.value(),
            self.depth_spinbox.value(),
            self.reference_text.value(),
        )


# pylint: disable=too-many-ancestors
class SubmodulesTreeWidget(standard.TreeWidget):
    updated = Signal()

    def __init__(self, context, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)

        model = context.model
        self.context = context

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        # UI
        self._active = False
        self.list_helper = BuildItem()
        # Connections
        # pylint: disable=no-member
        self.itemDoubleClicked.connect(self.tree_double_clicked)
        self.updated.connect(self.refresh, type=Qt.QueuedConnection)
        model.add_observer(model.message_submodules_changed, self.updated.emit)

    def refresh(self):
        if not self._active:
            return

        submodules = self.context.model.submodules_list
        items = [self.list_helper.get(entry) for entry in submodules]
        self.clear()
        if items:
            self.addTopLevelItems(items)

    def showEvent(self, event):
        """Defer updating widgets until the widget is visible"""
        if not self._active:
            self._active = True
            self.refresh()
        return super(SubmodulesTreeWidget, self).showEvent(event)

    def tree_double_clicked(self, item, _column):
        path = core.abspath(item.path)
        cmds.do(cmds.OpenRepo, self.context, path)


class BuildItem(object):
    def __init__(self):
        self.state_folder_map = {}
        self.state_folder_map[''] = icons.folder()
        self.state_folder_map['+'] = icons.staged()
        self.state_folder_map['-'] = icons.modified()
        self.state_folder_map['U'] = icons.merge()

    def get(self, entry):
        """entry: same as returned from list_submodule"""
        name = entry[2]
        path = entry[2]
        # TODO better tip
        tip = path + '\n' + entry[1]
        if entry[3]:
            tip += '\n({0})'.format(entry[3])
        icon = self.state_folder_map[entry[0]]
        return SubmodulesTreeWidgetItem(name, path, tip, icon)


class SubmodulesTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, name, path, tip, icon):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.path = path

        self.setIcon(0, icon)
        self.setText(0, name)
        self.setToolTip(0, tip)
