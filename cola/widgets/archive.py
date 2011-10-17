from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

import os
import sys

if __name__ == '__main__':
    sys.path.insert(1,
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from cola import qtutils
from cola.git import git
from cola.qt import QCollapsibleGroupBox


class GitArchiveDialog(QtGui.QDialog):

    @staticmethod
    def create(ref, parent=None):
        dlg = GitArchiveDialog(ref, parent=parent)
        if dlg.exec_() != dlg.Accepted:
            return None
        return dlg

    def __init__(self, ref, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowModality(QtCore.Qt.WindowModal)

        # input
        self.ref = ref

        # outputs
        self.fmt = None
        self.prefix = None
        self.filename = ref

        # constants
        spacing = 4
        margin = 4
        inner_margin = 0

        # widgets
        self.setWindowTitle('Save Archive')

        self.filetext = QtGui.QLineEdit()
        self.filetext.setText(ref)

        self.browse = QtGui.QToolButton()
        self.browse.setAutoRaise(True)
        style = self.style()
        self.browse.setIcon(style.standardIcon(QtGui.QStyle.SP_DirIcon))

        self.format_strings = git.archive('--list').rstrip().splitlines()
        self.format_combo = QtGui.QComboBox()
        self.format_combo.setEditable(False)
        self.format_combo.addItems(self.format_strings)

        self.cancel = QtGui.QPushButton()
        self.cancel.setText('Cancel')

        self.save = QtGui.QPushButton()
        self.save.setText('Save')
        self.save.setDefault(True)
        self.save.setEnabled(False)

        self.prefix_label = QtGui.QLabel()
        self.prefix_label.setText('Prefix')
        self.prefix_text = QtGui.QLineEdit()

        self.prefix_group = QCollapsibleGroupBox(parent=self)
        self.prefix_group.setTitle('Advanced')

        # layouts
        self.filelayt = QtGui.QHBoxLayout()
        self.filelayt.setSpacing(spacing)
        self.filelayt.setMargin(inner_margin)
        self.filelayt.addWidget(self.browse)
        self.filelayt.addWidget(self.filetext)
        self.filelayt.addWidget(self.format_combo)

        self.prefixlayt = QtGui.QHBoxLayout()
        self.prefixlayt.setSpacing(spacing)
        self.prefixlayt.setMargin(margin)
        self.prefixlayt.addWidget(self.prefix_label)
        self.prefixlayt.addWidget(self.prefix_text)
        self.prefix_group.setLayout(self.prefixlayt)
        self.prefix_group.set_collapsed(True)

        self.btnlayt = QtGui.QHBoxLayout()
        self.btnlayt.setSpacing(spacing)
        self.btnlayt.setMargin(inner_margin)
        self.btnlayt.addStretch()
        self.btnlayt.addWidget(self.cancel)
        self.btnlayt.addWidget(self.save)

        self.mainlayt = QtGui.QVBoxLayout()
        self.mainlayt.setMargin(margin)
        self.mainlayt.setSpacing(0)
        self.mainlayt.addLayout(self.filelayt)
        self.mainlayt.addWidget(self.prefix_group)
        self.mainlayt.addStretch()
        self.mainlayt.addLayout(self.btnlayt)
        self.setLayout(self.mainlayt)

        # connections
        self.connect(self.filetext, SIGNAL('textChanged(QString)'),
                     self.filetext_changed)

        self.connect(self.format_combo, SIGNAL('currentIndexChanged(int)'),
                     self.update_filetext_for_format)

        self.connect(self.browse, SIGNAL('clicked()'), self.choose_filename)

        self.connect(self.cancel, SIGNAL('clicked()'), self.reject)
        self.connect(self.save, SIGNAL('clicked()'), self.save_archive)

        if 'tar.gz' in self.format_strings:
            self.format_combo.setCurrentIndex(self.format_strings.index('tar.gz'))

        self.resize(420, 0)

    def save_archive(self):
        if not self.filename:
            return
        if os.path.exists(self.filename):
            title = 'Overwrite'
            text = 'Save and Overwrite?'
            info = ('The file "%s" exists and will be overwritten.\n'
                    'Save anyways?') % self.filename
            ok_text = 'Save'
            icon = qtutils.save_icon()
            if not qtutils.confirm(self, title, text, info, ok_text, icon=icon):
                return
        self.accept()

    def choose_filename(self):
        filename = QtGui.QFileDialog.getSaveFileName(self,
                        self.tr('Save File'), self.filename)
        if not filename:
            return
        self.filetext.setText(filename)
        self.update_filetext_for_format(self.format_combo.currentIndex())

    def filetext_changed(self, qstr):
        self.filename = unicode(qstr)
        self.save.setEnabled(bool(self.filename))

    def update_filetext_for_format(self, idx):
        self.fmt = self.format_strings[idx]
        text = unicode(self.filetext.text())
        for format_string in self.format_strings:
            ext = '.'+format_string
            if text.endswith(ext):
                text = text[:-len(ext)]
                break
        self.filetext.setText(text + '.' + self.fmt)
        self.filetext.setFocus(True)
        if '/' in text:
            start = text.rindex('/') + 1
        else:
            start = 0
        self.filetext.setSelection(start, len(text) - start)


if __name__ == '__main__':
    from cola.app import ColaApplication
    app = ColaApplication([])
    dlg = GitArchiveDialog('master')
    dlg.show()
    dlg.raise_()
    app.exec_()
