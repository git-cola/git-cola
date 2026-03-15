"""QAction creator functions"""
from __future__ import annotations
from typing import TYPE_CHECKING

from . import cmds
from . import difftool
from . import hotkeys
from . import icons
from . import qtutils
from .i18n import N_

if TYPE_CHECKING:
    from qtpy.QtGui import QIcon
    from qtpy.QtWidgets import QAction

    from .app import ApplicationContext
    from .cmds import LaunchEditor, LaunchEditorAtLine, StageOrUnstage
    from .widgets.commitmsg import CommitMessageEditor
    from .widgets.diff import DiffEditor
    from .widgets.status import StatusTreeWidget


def cmd_action(
    widget: DiffEditor | CommitMessageEditor | StatusTreeWidget,
    cmd: type[LaunchEditor] | type[LaunchEditorAtLine] | type[StageOrUnstage],
    context: ApplicationContext,
    icon: QIcon,
    *shortcuts,
) -> QAction:
    """Wrap a generic ContextCommand in a QAction"""
    action = qtutils.add_action(widget, cmd.name(), cmds.run(cmd, context), *shortcuts)
    action.setIcon(icon)
    return action


def launch_editor(
    context: ApplicationContext, widget: DiffEditor | CommitMessageEditor, *shortcuts
) -> QAction:
    """Create a QAction to launch an editor"""
    icon = icons.edit()
    return cmd_action(
        widget, cmds.LaunchEditor, context, icon, hotkeys.EDIT, *shortcuts
    )


def launch_editor_at_line(
    context: ApplicationContext,
    widget: DiffEditor | CommitMessageEditor | StatusTreeWidget,
    *shortcuts,
) -> QAction:
    """Create a QAction to launch an editor at the current line"""
    icon = icons.edit()
    return cmd_action(
        widget, cmds.LaunchEditorAtLine, context, icon, hotkeys.EDIT, *shortcuts
    )


def launch_difftool(
    context: ApplicationContext, widget: DiffEditor | CommitMessageEditor
) -> QAction:
    """Create a QAction to launch git-difftool(1)"""
    icon = icons.diff()
    cmd = difftool.LaunchDifftool
    action = qtutils.add_action(
        widget, cmd.name(), cmds.run(cmd, context), hotkeys.DIFF
    )
    action.setIcon(icon)
    return action


def stage_or_unstage(
    context: ApplicationContext, widget: DiffEditor | CommitMessageEditor
) -> QAction:
    """Create a QAction to stage or unstage the selection"""
    icon = icons.add()
    return cmd_action(
        widget, cmds.StageOrUnstage, context, icon, hotkeys.STAGE_SELECTION
    )


def move_down(widget: DiffEditor | CommitMessageEditor) -> QAction:
    """Create a QAction to select the next item"""
    action = qtutils.add_action(
        widget, N_('Next File'), widget.down.emit, hotkeys.MOVE_DOWN_SECONDARY
    )
    action.setIcon(icons.move_down())
    return action


def move_up(widget: DiffEditor | CommitMessageEditor) -> QAction:
    """Create a QAction to select the previous/above item"""
    action = qtutils.add_action(
        widget, N_('Previous File'), widget.up.emit, hotkeys.MOVE_UP_SECONDARY
    )
    action.setIcon(icons.move_up())
    return action
