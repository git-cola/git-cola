from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import qtutils
from cola.i18n import N_


def cmd_action(widget, cmd, icon, *shortcuts):
    action = qtutils.add_action(widget, cmd.name(), cmds.run(cmd),
                                cmd.SHORTCUT, *shortcuts)
    action.setIcon(icon)
    return action


def launch_editor(widget, *shortcuts):
    icon = qtutils.options_icon()
    return cmd_action(widget, cmds.LaunchEditor, icon, *shortcuts)


def launch_difftool(widget):
    icon = qtutils.git_icon()
    return cmd_action(widget, cmds.LaunchDifftool, icon)


def stage_or_unstage(widget):
    icon = qtutils.add_icon()
    return cmd_action(widget, cmds.StageOrUnstage, icon)


def move_down(widget):
    return qtutils.add_action(widget,
            N_('Next File'), lambda: widget.emit(SIGNAL('move_down()')),
            Qt.AltModifier + Qt.Key_J)


def move_up(widget):
    return qtutils.add_action(widget,
            N_('Previous File'), lambda: widget.emit(SIGNAL('move_up()')),
            Qt.AltModifier + Qt.Key_K)
