"""The "Actions" widget"""
from __future__ import division, absolute_import, unicode_literals

from qtpy import QtCore
from qtpy import QtWidgets

from cola import cmds
from cola import qtutils
from cola.i18n import N_
from cola.models.selection import selection_model
from cola.widgets import defs
from cola.widgets import remote
from cola.widgets import stash
from cola.qtutils import create_button
from cola.qtutils import connect_button


class QFlowLayoutWidget(QtWidgets.QWidget):

    _horizontal = QtWidgets.QBoxLayout.LeftToRight
    _vertical = QtWidgets.QBoxLayout.TopToBottom

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self._direction = self._vertical
        self._layout = layout = QtWidgets.QBoxLayout(self._direction)
        layout.setSpacing(defs.spacing)
        qtutils.set_margin(layout, defs.margin)
        self.setLayout(layout)
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                       QtWidgets.QSizePolicy.Minimum)
        self.setSizePolicy(policy)
        self.setMinimumSize(QtCore.QSize(1, 1))
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


def tooltip_button(text, layout):
    button = create_button(text, layout=layout)
    button.setToolTip(text)
    return button


class ActionButtons(QFlowLayoutWidget):
    def __init__(self, parent=None):
        QFlowLayoutWidget.__init__(self, parent)
        layout = self.layout()
        self.stage_button = tooltip_button(N_('Stage'), layout)
        self.unstage_button = tooltip_button(N_('Unstage'), layout)
        self.refresh_button = tooltip_button(N_('Refresh'), layout)
        self.fetch_button = tooltip_button(N_('Fetch...'), layout)
        self.push_button = tooltip_button(N_('Push...'), layout)
        self.pull_button = tooltip_button(N_('Pull...'), layout)
        self.stash_button = tooltip_button(N_('Stash...'), layout)
        self.aspect_ratio = 0.4
        layout.addStretch()
        self.setMinimumHeight(30)

        # Add callbacks
        connect_button(self.refresh_button, cmds.run(cmds.Refresh))
        connect_button(self.fetch_button, remote.fetch)
        connect_button(self.push_button, remote.push)
        connect_button(self.pull_button, remote.pull)
        connect_button(self.stash_button, stash.stash)
        connect_button(self.stage_button, self.stage)
        connect_button(self.unstage_button, self.unstage)

    def stage(self):
        """Stage selected files, or all files if no selection exists."""
        paths = selection_model().unstaged
        if not paths:
            cmds.do(cmds.StageModified)
        else:
            cmds.do(cmds.Stage, paths)

    def unstage(self):
        """Unstage selected files, or all files if no selection exists."""
        paths = selection_model().staged
        if not paths:
            cmds.do(cmds.UnstageAll)
        else:
            cmds.do(cmds.Unstage, paths)
