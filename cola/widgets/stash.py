"""Widgets for manipulating git stashes"""
from qtpy.QtCore import Qt

from ..i18n import N_
from ..interaction import Interaction
from ..models import stash
from ..qtutils import get
from .. import cmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from . import defs
from . import diff
from . import standard
from . import text


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

        self.rename_button = qtutils.create_button(
            text=N_('Rename'),
            tooltip=N_('Rename the selected stash'),
            icon=icons.edit(),
        )

        self.apply_button = qtutils.create_button(
            text=N_('Apply'), tooltip=N_('Apply the selected stash'), icon=icons.ok()
        )

        self.save_button = qtutils.create_button(
            text=N_('Save'),
            tooltip=N_('Save modified state to new stash'),
            icon=icons.save(),
            default=True,
        )

        self.drop_button = qtutils.create_button(
            text=N_('Drop'), tooltip=N_('Drop the selected stash'), icon=icons.discard()
        )

        self.pop_button = qtutils.create_button(
            text=N_('Pop'),
            tooltip=N_('Apply and drop the selected stash (git stash pop)'),
            icon=icons.discard(),
        )

        self.help_button = qtutils.create_button(
            text=N_('Help'), tooltip=N_('Show help\nShortcut: ?'), icon=icons.question()
        )
        self.close_button = qtutils.close_button()

        # A list of tuples [(display_text, tooltip), ...] containing the save modes.
        save_modes = stash.SaveModes.get()
        self.save_modes = qtutils.combo([mode[0] for mode in save_modes])
        # Change the combobox's tooltip when the selection changes.
        self.save_modes.currentIndexChanged.connect(
            lambda idx: self.save_modes.setToolTip(save_modes[idx][1])
        )
        # Set tooltips for the individual items in the tooltip.
        for idx, mode in enumerate(save_modes):
            self.save_modes.setItemData(idx, mode[1], Qt.ToolTipRole)

        self.recreate_index = qtutils.checkbox(
            text=N_('Recreate Index'),
            tooltip=N_('Recreate the index when restoring stashes'),
        )

        # Arrange layouts
        self.splitter = qtutils.splitter(
            Qt.Horizontal, self.stash_list, self.stash_text
        )
        self.splitter.setChildrenCollapsible(False)

        self.action_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.rename_button,
            self.pop_button,
            self.drop_button,
            self.apply_button,
            qtutils.STRETCH,
            self.save_modes,
            self.save_button,
        )

        self.bottom_layout = qtutils.hbox(
            defs.margin,
            defs.button_spacing,
            self.help_button,
            self.recreate_index,
            qtutils.STRETCH,
            self.close_button,
        )

        self.main_layt = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.splitter,
            self.action_layout,
            self.bottom_layout,
        )
        self.setLayout(self.main_layt)
        self.splitter.setSizes([self.width() // 3, self.width() * 2 // 3])

        # Save stash  with Ctrl+S
        self.save_action = qtutils.add_action(
            self, N_('Save'), self.stash_save, hotkeys.SAVE
        )
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
            self, N_('Delete'), self.stash_drop, hotkeys.DELETE_FILE
        )

        self.choose_all_changes_action = qtutils.add_action(
            self,
            N_('All changes'),
            lambda: self.save_modes.set_index_if_enabled(stash.SaveModes.ALL),
            hotkeys.CTRL_1,
            hotkeys.STASH_ALL,
        )
        self.choose_staged_only_action = qtutils.add_action(
            self,
            N_('Staged only'),
            lambda: self.save_modes.set_index_if_enabled(stash.SaveModes.STAGED),
            hotkeys.CTRL_2,
            hotkeys.STASH_STAGED,
        )
        self.choose_unstaged_only_action = qtutils.add_action(
            self,
            N_('Unstaged only'),
            lambda: self.save_modes.set_index_if_enabled(stash.SaveModes.UNSTAGED),
            hotkeys.CTRL_3,
            hotkeys.STASH_UNSTAGED,
        )
        self.show_help_action = qtutils.add_action(
            self, N_('Show Help'), lambda: show_help(context), hotkeys.QUESTION
        )

        self.stash_list.itemSelectionChanged.connect(self.item_selected)
        qtutils.connect_button(self.save_button, self.stash_save)
        qtutils.connect_button(self.rename_button, self.stash_rename)
        qtutils.connect_button(self.apply_button, self.stash_apply)
        qtutils.connect_button(self.pop_button, self.stash_pop)
        qtutils.connect_button(self.drop_button, self.stash_drop)
        qtutils.connect_button(self.close_button, self.close_and_rescan)
        qtutils.connect_button(self.help_button, lambda: show_help(context))

        self.init_size(parent=parent)
        self.update_from_model()
        self.update_actions()

    def close_and_rescan(self):
        cmds.do(cmds.Rescan, self.context)
        self.reject()

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
        is_changed = self.model.is_changed()
        self.save_modes.set_item_enabled(stash.SaveModes.STAGED, is_staged)
        self.save_modes.set_item_enabled(stash.SaveModes.UNSTAGED, is_staged)
        self.save_modes.setEnabled(is_changed)
        self.save_button.setEnabled(is_changed)

        is_selected = bool(self.selected_stash())
        self.apply_action.setEnabled(is_selected)
        self.drop_action.setEnabled(is_selected)
        self.pop_action.setEnabled(is_selected)
        self.recreate_index.setEnabled(is_selected)
        self.rename_button.setEnabled(is_selected)
        self.apply_button.setEnabled(is_selected)
        self.drop_button.setEnabled(is_selected)
        self.pop_button.setEnabled(is_selected)

    def update_from_model(self):
        """Initiates git queries on the model and updates the view"""
        stashes, revids, author_dates, names = self.model.stash_info()
        self.stashes = stashes
        self.revids = revids
        self.names = names

        displayed = False
        self.stash_list.clear()
        self.stash_list.addItems(self.stashes)
        if self.stash_list.count() > 0:
            for i in range(self.stash_list.count()):
                self.stash_list.item(i).setToolTip(author_dates[i])
            item = self.stash_list.item(0)
            self.stash_list.setCurrentItem(item)
            displayed = True

        # "Stash Index" depends on staged changes, so disable this option
        # if there are no staged changes.
        is_staged = self.model.is_staged()
        if stash.should_stash_staged(self.save_modes.current_index()) and not is_staged:
            self.save_modes.set_index(stash.SaveModes.ALL)

        return displayed

    def stash_rename(self):
        """Renames the currently selected stash"""
        selection = self.selected_stash()
        name = self.selected_name()
        new_name, ok = qtutils.prompt(
            N_('Enter a new name for the stash'),
            text=name,
            title=N_('Rename Stash'),
            parent=self,
        )
        if not ok or not new_name:
            return
        if new_name == name:
            Interaction.information(
                N_('No change made'), N_('The stash has not been renamed')
            )
            return
        context = self.context
        cmds.do(stash.RenameStash, context, selection, new_name)
        self.update_from_model()

    def stash_pop(self):
        self.stash_apply(pop=True)

    def stash_apply(self, pop=False):
        """Applies the currently selected stash"""
        selection = self.selected_stash()
        if not selection:
            return
        context = self.context
        index = get(self.recreate_index)
        cmds.do(stash.ApplyStash, context, selection, index, pop)
        self.update_from_model()

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
        context = self.context
        keep_index = stash.should_keep_index(self.save_modes.current_index())
        stash_index = stash.should_stash_staged(self.save_modes.current_index())
        if stash_index:
            cmds.do(stash.StashIndex, context, stash_name)
        else:
            cmds.do(stash.SaveStash, context, stash_name, keep_index)
        self.update_from_model()

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
        if not self.update_from_model():
            self.stash_text.setPlainText('')

    def export_state(self):
        """Export persistent settings"""
        state = super().export_state()
        current_index = self.save_modes.current_index()
        state['keep_index'] = stash.should_keep_index(current_index)
        state['stash_index'] = stash.should_stash_staged(current_index)
        state['recreate_index'] = get(self.recreate_index)
        state['sizes'] = get(self.splitter)
        return state

    def apply_state(self, state):
        """Apply persistent settings"""
        result = super().apply_state(state)
        keep_index = bool(state.get('keep_index', True))
        recreate_index = bool(state.get('recreate_index', True))
        stash_index = bool(state.get('stash_index', False))

        # It would be simpler to have a "save_mode" instead of individual booleans.
        # This is done for compatibility with older versions.
        self.recreate_index.setChecked(recreate_index)
        if stash_index:
            self.save_modes.set_index(stash.SaveModes.STAGED)
        elif keep_index:
            self.save_modes.set_index(stash.SaveModes.UNSTAGED)
        else:
            self.save_modes.set_index(stash.SaveModes.ALL)

        try:
            self.splitter.setSizes(state['sizes'])
        except (KeyError, ValueError, AttributeError):
            pass
        return result


def show_help(context):
    help_text = N_(
        """
Keyboard Shortcuts  Actions
------------------  --------------------------------
?                   show help
esc                 close and exit
ctrl + 1, alt + a   set save mode to "All changes"
ctrl + 2, alt + s   set save mode to "Staged only"
ctrl + 3, alt + u   set save mode to "Unstaged only"
ctrl + enter        apply stash
ctrl + s            save stash
"""
    )
    title = N_('Help')
    return text.text_dialog(context, help_text, title)
