"""Actions widget"""
from __future__ import absolute_import, division, print_function, unicode_literals
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


def tooltip_button(text, layout):
    button = create_button(text, layout=layout)
    button.setToolTip(text)
    return button


class ActionButtons(QFlowLayoutWidget):
    def __init__(self, context, parent=None):
        QFlowLayoutWidget.__init__(self, parent)
        layout = self.layout()
        self.context = context
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
        connect_button(self.refresh_button, cmds.run(cmds.Refresh, context))
        connect_button(self.fetch_button, partial(remote.fetch, context))
        connect_button(self.push_button, partial(remote.push, context))
        connect_button(self.pull_button, partial(remote.pull, context))
        connect_button(self.stash_button, partial(stash.view, context))
        connect_button(self.stage_button, cmds.run(cmds.StageSelected, context))
        connect_button(self.unstage_button, self.unstage)

    def unstage(self):
        """Unstage selected files, or all files if no selection exists."""
        context = self.context
        paths = context.selection.staged
        context = self.context
        if not paths:
            cmds.do(cmds.UnstageAll, context)
        else:
            cmds.do(cmds.Unstage, context, paths)
