"""The "Actions" widget"""
from __future__ import division

from PyQt4 import QtCore
from PyQt4 import QtGui

from cola import cmds
from cola.i18n import N_
from cola.models.selection import selection_model
from cola.widgets import defs
from cola.widgets import remote
from cola.widgets import stash
from cola.qtutils import create_button
from cola.qtutils import connect_button


class QFlowLayoutWidget(QtGui.QWidget):

    _horizontal = QtGui.QBoxLayout.LeftToRight
    _vertical = QtGui.QBoxLayout.TopToBottom

    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self._direction = self._vertical
        self._layout = layout = QtGui.QBoxLayout(self._direction)
        layout.setSpacing(defs.spacing)
        layout.setMargin(defs.margin)
        self.setLayout(layout)
        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                   QtGui.QSizePolicy.Minimum)
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


class ActionButtons(QFlowLayoutWidget):
    def __init__(self, parent=None):
        QFlowLayoutWidget.__init__(self, parent)
        layout = self.layout()
        self.stage_button = create_button(text=N_('Stage'), layout=layout)
        self.unstage_button = create_button(text=N_('Unstage'), layout=layout)
        self.refresh_button = create_button(text=N_('Refresh'), layout=layout)
        self.fetch_button = create_button(text=N_('Fetch...'), layout=layout)
        self.push_button = create_button(text=N_('Push...'), layout=layout)
        self.pull_button = create_button(text=N_('Pull...'), layout=layout)
        self.stash_button = create_button(text=N_('Stash...'), layout=layout)
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
