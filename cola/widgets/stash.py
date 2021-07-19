"""Widgets for manipulating git stashes"""
from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtCore
from qtpy.QtCore import Qt

from ..i18n import N_
from ..interaction import Interaction
from ..models import stash
from ..qtutils import get
from .. import cmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import utils
from . import defs
from . import diff
from . import standard


def view(context, show=True):
    """Launches a stash dialog using the provided model + view"""
    model = stash.StashModel(context)
    stash_view = StashView(context, model, parent=qtutils.active_window())
    if show:
        stash_view.show()
        stash_view.raise_()
    return stash_view


class StashView(standard.Dialog):
    def __init__(self, context, model, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.context = context
        self.model = model
        self.stashes = []
        self.revids = []
        self.names = []

        self.setWindowTitle(N_('Stash'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.stash_list = standard.ListWidget(parent=self)
        self.stash_text = diff.DiffTextEdit(context, self)

        self.button_apply = qtutils.create_button(
            text=N_('Apply'), tooltip=N_('Apply the selected stash'), icon=icons.ok()
        )

        self.button_save = qtutils.create_button(
            text=N_('Save'),
            tooltip=N_('Save modified state to new stash'),
            icon=icons.save(),
            default=True,
        )

        self.button_drop = qtutils.create_button(
            text=N_('Drop'), tooltip=N_('Drop the selected stash'), icon=icons.discard()
        )

        self.button_pop = qtutils.create_button(
            text=N_('Pop'),
            tooltip=N_('Apply and drop the selected stash (git stash pop)'),
            icon=icons.discard(),
        )

        self.button_close = qtutils.close_button()

        self.keep_index = qtutils.checkbox(
            text=N_('Keep Index'),
            checked=True,
            tooltip=N_('Stash unstaged changes only, keeping staged changes'),
        )

        self.stash_index = qtutils.checkbox(
            text=N_('Stash Index'), tooltip=N_('Stash staged changes only')
        )

        # Arrange layouts
        self.splitter = qtutils.splitter(
            Qt.Horizontal, self.stash_list, self.stash_text
        )
        self.splitter.setChildrenCollapsible(False)

        self.btn_layt = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.button_close,
            qtutils.STRETCH,
            self.stash_index,
            self.keep_index,
            self.button_save,
            self.button_apply,
            self.button_pop,
            self.button_drop,
        )

        self.main_layt = qtutils.vbox(
            defs.margin, defs.spacing, self.splitter, self.btn_layt
        )
        self.setLayout(self.main_layt)
        self.splitter.setSizes([self.width() // 3, self.width() * 2 // 3])

        # Apply stash with Ctrl+Enter
        self.apply_action = qtutils.add_action(
            self, N_('Apply'), self.stash_apply, hotkeys.APPLY
        )
        # Pop stash with Ctrl+Backspace
        self.pop_action = qtutils.add_action(
            self, N_('Pop'), self.stash_pop, hotkeys.DELETE_FILE_SECONDARY
        )
        # Drop stash with Ctrl+Shift+Backspace
        self.drop_action = qtutils.add_action(
            self, N_('Pop'), self.stash_drop, hotkeys.DELETE_FILE
        )

        # pylint: disable=no-member
        self.stash_list.itemSelectionChanged.connect(self.item_selected)

        qtutils.connect_button(self.button_save, self.stash_save)
        qtutils.connect_button(self.button_apply, self.stash_apply)
        qtutils.connect_button(self.button_pop, self.stash_pop)
        qtutils.connect_button(self.button_drop, self.stash_drop)
        qtutils.connect_button(self.button_close, self.close_and_rescan)

        qtutils.connect_checkbox(self.stash_index, self.stash_index_clicked)
        qtutils.connect_checkbox(self.keep_index, self.keep_index_clicked)

        self.init_size(parent=parent)

        self.update_from_model()
        self.update_actions()

    def close_and_rescan(self):
        cmds.do(cmds.Rescan, self.context)
        self.reject()

    # "stash" and "keep" index are mutually disable, but we don't
    # want a radio button because we'd have to add a 3rd "default" option.
    def stash_index_clicked(self, clicked):
        if clicked:
            self.keep_index.setChecked(False)

    def keep_index_clicked(self, clicked):
        if clicked:
            self.stash_index.setChecked(False)

    def selected_stash(self):
        """Returns the stash name of the currently selected stash"""
        list_widget = self.stash_list
        stash_list = self.revids
        return qtutils.selected_item(list_widget, stash_list)

    def selected_name(self):
        list_widget = self.stash_list
        stash_list = self.names
        return qtutils.selected_item(list_widget, stash_list)

    def item_selected(self):
        """Shows the current stash in the main view."""
        self.update_actions()
        selection = self.selected_stash()
        if not selection:
            return
        diff_text = self.model.stash_diff(selection)
        self.stash_text.setPlainText(diff_text)

    def update_actions(self):
        is_staged = self.model.is_staged()
        self.stash_index.setEnabled(is_staged)

        is_changed = self.model.is_changed()
        self.keep_index.setEnabled(is_changed)
        self.button_save.setEnabled(is_changed)

        is_selected = bool(self.selected_stash())
        self.apply_action.setEnabled(is_selected)
        self.drop_action.setEnabled(is_selected)
        self.pop_action.setEnabled(is_selected)
        self.button_apply.setEnabled(is_selected)
        self.button_drop.setEnabled(is_selected)
        self.button_pop.setEnabled(is_selected)

    def update_from_model(self):
        """Initiates git queries on the model and updates the view"""
        stashes, revids, author_dates, names = self.model.stash_info()
        self.stashes = stashes
        self.revids = revids
        self.names = names

        self.stash_list.clear()
        self.stash_list.addItems(self.stashes)
        if self.stash_list.count() > 0:
            for i in range(self.stash_list.count()):
                self.stash_list.item(i).setToolTip(author_dates[i])
            item = self.stash_list.item(0)
            self.stash_list.setCurrentItem(item)

        # "Stash Index" depends on staged changes, so disable this option
        # if there are no staged changes.
        is_staged = self.model.is_staged()
        if get(self.stash_index) and not is_staged:
            self.stash_index.setChecked(False)

    def stash_pop(self):
        self.stash_apply(pop=True)

    def stash_apply(self, pop=False):
        """Applies the currently selected stash"""
        selection = self.selected_stash()
        if not selection:
            return
        context = self.context
        index = get(self.keep_index)
        cmds.do(stash.ApplyStash, context, selection, index, pop)
        QtCore.QTimer.singleShot(1, self.accept)

    def stash_save(self):
        """Saves the worktree in a stash

        This prompts the user for a stash name and creates
        a git stash named accordingly.

        """
        stash_name, ok = qtutils.prompt(
            N_('Enter a name for the stash'), title=N_('Save Stash'), parent=self
        )
        if not ok or not stash_name:
            return
        # Sanitize the stash name
        stash_name = utils.sanitize(stash_name)
        if stash_name in self.names:
            Interaction.critical(
                N_('Error: Stash exists'),
                N_('A stash named "%s" already exists') % stash_name,
            )
            return
        context = self.context
        keep_index = get(self.keep_index)
        stash_index = get(self.stash_index)
        if stash_index:
            cmds.do(stash.StashIndex, context, stash_name)
        else:
            cmds.do(stash.SaveStash, context, stash_name, keep_index)
        QtCore.QTimer.singleShot(1, self.accept)

    def stash_drop(self):
        """Drops the currently selected stash"""
        selection = self.selected_stash()
        name = self.selected_name()
        if not selection:
            return
        if not Interaction.confirm(
            N_('Drop Stash?'),
            N_('Recovering a dropped stash is not possible.'),
            N_('Drop the "%s" stash?') % name,
            N_('Drop Stash'),
            default=True,
            icon=icons.discard(),
        ):
            return
        cmds.do(stash.DropStash, self.context, selection)
        self.update_from_model()
        self.stash_text.setPlainText('')

    def export_state(self):
        """Export persistent settings"""
        state = super(StashView, self).export_state()
        state['keep_index'] = get(self.keep_index)
        state['stash_index'] = get(self.stash_index)
        state['sizes'] = get(self.splitter)
        return state

    def apply_state(self, state):
        """Apply persistent settings"""
        result = super(StashView, self).apply_state(state)
        keep_index = bool(state.get('keep_index', True))
        stash_index = bool(state.get('stash_index', False))
        self.keep_index.setChecked(keep_index)
        self.stash_index.setChecked(stash_index)
        try:
            self.splitter.setSizes(state['sizes'])
        except (KeyError, ValueError, AttributeError):
            pass
        return result
