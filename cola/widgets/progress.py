from __future__ import absolute_import
from __future__ import unicode_literals

import time

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import qtutils


class ProgressDialog(QtGui.QProgressDialog):
    """Custom progress dialog

    This dialog ignores the ESC key so that it is not
    prematurely closed.

    An thread is spawned to animate the progress label text.

    """
    def __init__(self, title, label, parent):
        QtGui.QProgressDialog.__init__(self, parent)
        self.setFont(qtutils.diff_font())
        self.setRange(0, 0)
        self.setCancelButton(None)
        self.setWindowTitle(title)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)
        self.setLabelText(label + '     ')
        self.progress_thread = ProgressAnimationThread(label, self)
        self.connect(self.progress_thread,
                     SIGNAL('update_progress'), self.update_progress)

    def update_progress(self, txt):
        self.setLabelText(txt)

    def keyPressEvent(self, event):
        if event.key() != Qt.Key_Escape:
            QtGui.QProgressDialog.keyPressEvent(self, event)

    def show(self):
        QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)
        self.progress_thread.start()
        QtGui.QProgressDialog.show(self)

    def hide(self):
        QtGui.QApplication.restoreOverrideCursor()
        self.progress_thread.stop()
        self.progress_thread.wait()
        QtGui.QProgressDialog.hide(self)


class ProgressAnimationThread(QtCore.QThread):
    """Emits a pseudo-animated text stream for progress bars"""

    def __init__(self, txt, parent, timeout=0.1):
        QtCore.QThread.__init__(self, parent)
        self.running = False
        self.txt = txt
        self.timeout = timeout
        self.symbols = [
            '.  ..',
            '..  .',
            '...  ',
            ' ... ',
            '  ...',
        ]
        self.idx = -1

    def next(self):
        self.idx = (self.idx + 1) % len(self.symbols)
        return self.txt + self.symbols[self.idx]

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.emit(SIGNAL('update_progress'), self.next())
            time.sleep(self.timeout)
