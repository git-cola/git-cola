"""Actions widget"""
from functools import partial

from qtpy import QtCore
from qtpy import QtWidgets

from .. import cmds
from .. import qtutils
from ..i18n import N_
from ..widgets import defs
from ..widgets import remote
from ..widgets import stash
from ..qtutils import create_button
from ..qtutils import connect_button


class QFlowLayoutWidget(QtWidgets.QFrame):
    _horizontal = QtWidgets.QBoxLayout.LeftToRight
    _vertical = QtWidgets.QBoxLayout.TopToBottom

    def __init__(self, parent):
        QtWidgets.QFrame.__init__(self, parent)
        self._direction = self._vertical
        self._layout = layout = QtWidgets.QBoxLayout(self._direction)
        layout.setSpacing(defs.spacing)
        qtutils.set_margin(layout, defs.margin)
        self.setLayout(layout)
        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        self.setSizePolicy(policy)
        self.setMinimumSize(QtCore.QSize(10, 10))
        self.aspect_ratio = 0.8

    def resizeEvent(self, event):
        size = event.size()
        if size.width() * self.aspect_ratio < size.height():
            dxn = self._vertical
        else:
            dxn = self._horizontal

        if dxn != self._direction:
            self._direction = dxn
            self.layout().setDirection(dxn)


def tooltip_button(text, layout, tooltip=''):
    """Convenience wrapper around qtutils.create_button()"""
    return create_button(text, layout=layout, tooltip=tooltip)


class ActionButtons(QFlowLayoutWidget):
    def __init__(self, context, parent=None):
        QFlowLayoutWidget.__init__(self, parent)
        layout = self.layout()
        self.context = context
        self.stage_button = tooltip_button(
            N_('Stage'), layout, tooltip=N_('Stage changes using "git add"')
        )
        self.unstage_button = tooltip_button(
            N_('Unstage'), layout, tooltip=N_('Unstage changes using "git reset"')
        )
        self.refresh_button = tooltip_button(N_('Refresh'), layout)
        self.fetch_button = tooltip_button(
            N_('Fetch...'),
            layout,
            tooltip=N_('Fetch from one or more remotes using "git fetch"'),
        )
        self.push_button = tooltip_button(
            N_('Push...'), layout, N_('Push to one or more remotes using "git push"')
        )
        self.pull_button = tooltip_button(
            N_('Pull...'), layout, tooltip=N_('Integrate changes using "git pull"')
        )
        self.sync_button = tooltip_button(
            N_('Sync'),
            layout,
            tooltip=N_('Integrate changes from tracking branches using "git pull"'),
        )
        self.sync_out_button = tooltip_button(
            N_('Sync out'),
            layout,
            tooltip=N_('Push changes to tracking branch using "git push"'),
        )
        self.stash_button = tooltip_button(
            N_('Stash...'),
            layout,
            tooltip=N_('Temporarily stash away uncommitted changes using "git stash"'),
        )
        self.exit_diff_mode_button = tooltip_button(
            N_('Exit Diff'), layout, tooltip=N_('Exit Diff mode')
        )
        self.exit_diff_mode_button.setVisible(False)
        self.aspect_ratio = 0.4
        layout.addStretch()
        self.setMinimumHeight(30)

        # Add callbacks
        connect_button(self.refresh_button, cmds.run(cmds.Refresh, context))
        connect_button(self.fetch_button, partial(remote.fetch, context))
        connect_button(self.push_button, partial(remote.push, context))
        connect_button(self.pull_button, partial(remote.pull, context))
        connect_button(self.sync_button, cmds.run(cmds.Sync, context))
        connect_button(self.sync_out_button, cmds.run(cmds.SyncOut, context))
        connect_button(self.stash_button, partial(stash.view, context))
        connect_button(self.stage_button, cmds.run(cmds.StageSelected, context))
        connect_button(self.exit_diff_mode_button, cmds.run(cmds.ResetMode, context))
        connect_button(self.unstage_button, self.unstage)

    def unstage(self):
        """Unstage selected files, or all files if no selection exists."""
        context = self.context
        paths = context.selection.staged
        if not paths:
            cmds.do(cmds.UnstageAll, context)
        else:
            cmds.do(cmds.Unstage, context, paths)

    def set_mode(self, mode):
        """Respond to changes to the diff mode"""
        diff_mode = mode == self.context.model.mode_diff
        self.exit_diff_mode_button.setVisible(diff_mode)
