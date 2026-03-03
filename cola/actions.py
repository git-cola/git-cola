"""QAction creator functions"""
from __future__ import annotations

from . import cmds
from . import difftool
from . import hotkeys
from . import icons
from . import qtutils
from .i18n import N_
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction
from cola.widgets.commitmsg import CommitMessageEditor
from cola.widgets.diff import DiffEditor
from cola.widgets.status import StatusTreeWidget
from cola.cmds import LaunchEditor, StageOrUnstage, LaunchEditorAtLine
from typing import Union


def cmd_action(
    widget: Union[DiffEditor, CommitMessageEditor, StatusTreeWidget],
    cmd: Union[type[LaunchEditor], type[LaunchEditorAtLine], type[StageOrUnstage]],
    context,
    icon: QIcon,
    *shortcuts,
) -> QAction:
    """Wrap a generic ContextCommand in a QAction"""
    action = qtutils.add_action(widget, cmd.name(), cmds.run(cmd, context), *shortcuts)
    action.setIcon(icon)
    return action


def launch_editor(context, widget, *shortcuts):
    """Create a QAction to launch an editor"""
    icon = icons.edit()
    return cmd_action(
        widget, cmds.LaunchEditor, context, icon, hotkeys.EDIT, *shortcuts
    )


def launch_editor_at_line(
    context,
    widget: Union[DiffEditor, CommitMessageEditor, StatusTreeWidget],
    *shortcuts,
) -> QAction:
    """Create a QAction to launch an editor at the current line"""
    icon = icons.edit()
    return cmd_action(
        widget, cmds.LaunchEditorAtLine, context, icon, hotkeys.EDIT, *shortcuts
    )


def launch_difftool(context, widget: Union[DiffEditor, CommitMessageEditor]) -> QAction:
    """Create a QAction to launch git-difftool(1)"""
    icon = icons.diff()
    cmd = difftool.LaunchDifftool
    action = qtutils.add_action(
        widget, cmd.name(), cmds.run(cmd, context), hotkeys.DIFF
    )
    action.setIcon(icon)
    return action


def stage_or_unstage(context, widget: DiffEditor) -> QAction:
    """Create a QAction to stage or unstage the selection"""
    icon = icons.add()
    return cmd_action(
        widget, cmds.StageOrUnstage, context, icon, hotkeys.STAGE_SELECTION
    )


def move_down(widget: Union[DiffEditor, CommitMessageEditor]) -> QAction:
    """Create a QAction to select the next item"""
    action = qtutils.add_action(
        widget, N_('Next File'), widget.down.emit, hotkeys.MOVE_DOWN_SECONDARY
    )
    action.setIcon(icons.move_down())
    return action


def move_up(widget: Union[DiffEditor, CommitMessageEditor]) -> QAction:
    """Create a QAction to select the previous/above item"""
    action = qtutils.add_action(
        widget, N_('Previous File'), widget.up.emit, hotkeys.MOVE_UP_SECONDARY
    )
    action.setIcon(icons.move_up())
    return action
