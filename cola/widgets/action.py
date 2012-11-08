"""The "Actions" widget"""

import cola
from cola import cmds
from cola import qt
from cola import stash
from cola.widgets import remote
from cola.qt import create_button
from cola.qtutils import connect_button


class ActionButtons(qt.QFlowLayoutWidget):
    def __init__(self, parent=None):
        qt.QFlowLayoutWidget.__init__(self, parent)
        layout = self.layout()
        self.stage_button = create_button(text='Stage', layout=layout)
        self.unstage_button = create_button(text='Unstage', layout=layout)
        self.rescan_button = create_button(text='Rescan', layout=layout)
        self.fetch_button = create_button(text='Fetch...', layout=layout)
        self.push_button = create_button(text='Push...', layout=layout)
        self.pull_button = create_button(text='Pull...', layout=layout)
        self.stash_button = create_button(text='Stash...', layout=layout)
        layout.addStretch()
        self.setMinimumHeight(30)

        # Add callbacks
        connect_button(self.rescan_button, cmds.run(cmds.RescanAndRefresh))
        connect_button(self.fetch_button, remote.fetch)
        connect_button(self.push_button, remote.push)
        connect_button(self.pull_button, remote.pull)
        connect_button(self.stash_button, stash.stash)
        connect_button(self.stage_button, self.stage)
        connect_button(self.unstage_button, self.unstage)

    def stage(self):
        """Stage selected files, or all files if no selection exists."""
        paths = cola.selection_model().unstaged
        if not paths:
            cmds.do(cmds.StageModified)
        else:
            cmds.do(cmds.Stage, paths)

    def unstage(self):
        """Unstage selected files, or all files if no selection exists."""
        paths = cola.selection_model().staged
        if not paths:
            cmds.do(cmds.UnstageAll)
        else:
            cmds.do(cmds.Unstage, paths)
