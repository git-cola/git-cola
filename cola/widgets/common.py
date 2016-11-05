from __future__ import division, absolute_import, unicode_literals

from ..i18n import N_
from .. import cmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import utils


def cmd_action(parent, cmd, fn, *hotkeys):
    """Wrap a standard Command object in a QAction

    This function assumes that :func:`fn()` takes no arguments,
    that `cmd` has a :func:`name()` method, and that the `cmd`
    constructor takes a single argument, as returned by `fn`.

    """
    return qtutils.add_action(parent, cmd.name(),
                              lambda: cmds.do(cmd, fn()),
                              *hotkeys)


def default_app_action(parent, fn):
    """Open paths with the OS-default app -> QAction"""
    action = cmd_action(parent, cmds.OpenDefaultApp, fn,
                        hotkeys.PRIMARY_ACTION)
    action.setIcon(icons.default_app())
    return action


def edit_action(parent, *keys):
    """Launch an editor -> QAction"""
    action = qtutils.add_action_with_status_tip(
            parent, cmds.LaunchEditor.name(),
            N_('Edit selected paths'),
            cmds.run(cmds.LaunchEditor), hotkeys.EDIT, *keys)
    action.setIcon(icons.edit())
    return action


def parent_dir_action(parent, fn):
    """Open the parent directory of paths -> QAction"""
    action = cmd_action(parent, cmds.OpenParentDir, fn,
                        hotkeys.SECONDARY_ACTION)
    action.setIcon(icons.folder())
    return action


def refresh_action(parent):
    """Refresh the repository state -> QAction"""
    return qtutils.add_action(parent, cmds.Refresh.name(),
                              cmds.run(cmds.Refresh), hotkeys.REFRESH)


def terminal_action(parent, fn):
    """Launch a terminal -> QAction"""
    action = cmd_action(parent, cmds.LaunchTerminal,
                        lambda: utils.select_directory(fn()),
                        hotkeys.TERMINAL)
    return action
