import functools

from ..i18n import N_
from .. import cmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import utils


def cmd_action(parent, cmd, context, func, *keys):
    """Wrap a standard Command object in a QAction

    This function assumes that :func:`func()` takes no arguments,
    that `cmd` has a :func:`name()` method, and that the `cmd`
    constructor takes a single argument, as returned by `func`.

    """
    return qtutils.add_action(
        parent, cmd.name(), lambda: cmds.do(cmd, context, func()), *keys
    )


def default_app_action(context, parent, func):
    """Open paths with the OS-default app -> QAction"""
    action = cmd_action(
        parent, cmds.OpenDefaultApp, context, func, hotkeys.PRIMARY_ACTION
    )
    action.setIcon(icons.default_app())
    return action


def edit_action(context, parent, *keys):
    """Launch an editor -> QAction"""
    action = qtutils.add_action_with_tooltip(
        parent,
        cmds.LaunchEditor.name(),
        N_('Edit selected paths'),
        cmds.run(cmds.LaunchEditor, context),
        hotkeys.EDIT,
        *keys
    )
    action.setIcon(icons.edit())
    return action


def parent_dir_action(context, parent, func):
    """Open the parent directory of paths -> QAction"""
    hotkey = hotkeys.SECONDARY_ACTION
    action = cmd_action(parent, cmds.OpenParentDir, context, func, hotkey)
    action.setIcon(icons.folder())
    return action


def worktree_dir_action(context, parent, *keys):
    """Open the repository worktree -> QAction"""
    # lambda: None is a no-op.
    action = cmd_action(parent, cmds.OpenWorktree, context, lambda: None, *keys)
    action.setIcon(icons.folder())
    return action


def refresh_action(context, parent):
    """Refresh the repository state -> QAction"""
    return qtutils.add_action(
        parent, cmds.Refresh.name(), cmds.run(cmds.Refresh, context), hotkeys.REFRESH
    )


def terminal_action(context, parent, func=None, hotkey=None):
    """Launch a terminal -> QAction"""
    action = None
    if cmds.LaunchTerminal.is_available(context):
        if func is None:
            func = functools.partial(lambda: None)
        action = cmd_action(
            parent,
            cmds.LaunchTerminal,
            context,
            lambda: utils.select_directory(func()),
        )
        action.setIcon(icons.terminal())
        if hotkey is not None:
            action.setShortcut(hotkey)
    return action
