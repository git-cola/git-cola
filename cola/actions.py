from __future__ import absolute_import

from . import cmds
from . import hotkeys
from . import icons
from . import qtutils
from .i18n import N_


def cmd_action(widget, cmd, context, icon, *shortcuts):
    action = qtutils.add_action(
        widget, cmd.name(), cmds.run(cmd, context), *shortcuts)
    action.setIcon(icon)
    return action


def launch_editor(context, widget, *shortcuts):
    icon = icons.edit()
    return cmd_action(widget, cmds.LaunchEditor, context, icon,
        hotkeys.EDIT, *shortcuts)


def launch_difftool(context, widget):
    icon = icons.diff()
    cmd = cmds.LaunchDifftool
    action = qtutils.add_action(
        widget, cmd.name(), cmds.run(cmd, context), hotkeys.DIFF)
    action.setIcon(icon)
    return action


def stage_or_unstage(context, widget):
    icon = icons.add()
    return cmd_action(widget, cmds.StageOrUnstage, context, icon,
                      hotkeys.STAGE_SELECTION)


def move_down(widget):
    return qtutils.add_action(
            widget, N_('Next File'), widget.down.emit,
            hotkeys.MOVE_DOWN_SECONDARY)


def move_up(widget):
    return qtutils.add_action(
            widget, N_('Previous File'), widget.up.emit,
            hotkeys.MOVE_UP_SECONDARY)
