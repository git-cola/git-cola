from __future__ import absolute_import

from cola import sipcompat
sipcompat.initialize()

from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import hotkeys
from cola import icons
from cola import qtutils
from cola.i18n import N_


def cmd_action(widget, cmd, icon, *shortcuts):
    action = qtutils.add_action(widget, cmd.name(), cmds.run(cmd), *shortcuts)
    action.setIcon(icon)
    return action


def launch_editor(widget, *shortcuts):
    icon = icons.configure()
    return cmd_action(widget, cmds.LaunchEditor, icon, hotkeys.EDIT, *shortcuts)


def launch_difftool(widget):
    icon = icons.diff()
    return cmd_action(widget, cmds.LaunchDifftool, icon, hotkeys.DIFF)


def stage_or_unstage(widget):
    icon = icons.add()
    return cmd_action(widget, cmds.StageOrUnstage, icon,
                      hotkeys.STAGE_SELECTION)


def move_down(widget):
    return qtutils.add_action(widget,
            N_('Next File'), lambda: widget.emit(SIGNAL('move_down()')),
            hotkeys.MOVE_DOWN_SECONDARY)


def move_up(widget):
    return qtutils.add_action(widget,
            N_('Previous File'), lambda: widget.emit(SIGNAL('move_up()')),
            hotkeys.MOVE_UP_SECONDARY)
