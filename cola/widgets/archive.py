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
from cola.qt import ExpandableGroupBox
from cola.widgets import defs
from cola.dag.model import archive


class GitArchiveDialog(QtGui.QDialog):

    @staticmethod
    def create(ref, shortref, parent):
        dlg = GitArchiveDialog(ref, shortref, parent)
        if dlg.exec_() != dlg.Accepted:
            return None
        return dlg

    @classmethod
    def save(cls, ref, shortref, parent):
        dlg = cls.create(ref, shortref, parent)
        if dlg is None:
            return
        parent.emit(SIGNAL(archive), ref, dlg.fmt, dlg.prefix, dlg.filename)
        qtutils.information('File Saved', 'File saved to "%s"' % dlg.filename)

    def __init__(self, ref, shortref=None, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowModality(QtCore.Qt.WindowModal)

        # input
        self.ref = ref
        if shortref is None:
            shortref = ref

        # outputs
        self.fmt = None

        filename = '%s-%s' % (os.path.basename(os.getcwd()), shortref)
        self.prefix = filename + '/'
        self.filename = filename

        # widgets
        self.setWindowTitle('Save Archive')

        self.filetext = QtGui.QLineEdit()
        self.filetext.setText(self.filename)

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

        self.prefix_label = QtGui.QLabel()
        self.prefix_label.setText('Prefix')
        self.prefix_text = QtGui.QLineEdit()
        self.prefix_text.setText(self.prefix)

        self.prefix_group = ExpandableGroupBox()
        self.prefix_group.setTitle('Advanced')

        # layouts
        self.filelayt = QtGui.QHBoxLayout()
        self.filelayt.setMargin(0)
        self.filelayt.setSpacing(defs.spacing)
        self.filelayt.addWidget(self.browse)
        self.filelayt.addWidget(self.filetext)
        self.filelayt.addWidget(self.format_combo)

        self.prefixlayt = QtGui.QHBoxLayout()
        self.prefixlayt.setMargin(defs.margin)
        self.prefixlayt.setSpacing(defs.spacing)
        self.prefixlayt.addWidget(self.prefix_label)
        self.prefixlayt.addWidget(self.prefix_text)
        self.prefix_group.setLayout(self.prefixlayt)
        self.prefix_group.set_expanded(False)

        self.btnlayt = QtGui.QHBoxLayout()
        self.btnlayt.setMargin(0)
        self.btnlayt.setSpacing(defs.spacing)
        self.btnlayt.addStretch()
        self.btnlayt.addWidget(self.cancel)
        self.btnlayt.addWidget(self.save)

        self.mainlayt = QtGui.QVBoxLayout()
        self.mainlayt.setMargin(defs.margin)
        self.mainlayt.setSpacing(0)
        self.mainlayt.addLayout(self.filelayt)
        self.mainlayt.addWidget(self.prefix_group)
        self.mainlayt.addStretch()
        self.mainlayt.addLayout(self.btnlayt)
        self.setLayout(self.mainlayt)
        self.resize(555, 0)

        # initial setup; done before connecting to avoid
        # signal/slot side-effects
        if 'tar.gz' in self.format_strings:
            idx = self.format_strings.index('tar.gz')
        elif 'zip' in self.format_strings:
            idx = self.format_strings.index('zip')
        else:
            idx = 0
        self.format_combo.setCurrentIndex(idx)
        self.update_filetext_for_format(idx)

        # connections
        self.connect(self.filetext, SIGNAL('textChanged(QString)'),
                     self.filetext_changed)

        self.connect(self.prefix_text, SIGNAL('textChanged(QString)'),
                     self.prefix_text_changed)

        self.connect(self.format_combo, SIGNAL('currentIndexChanged(int)'),
                     self.update_filetext_for_format)

        self.connect(self.prefix_group, SIGNAL('expanded(bool)'),
                     self.prefix_group_expanded)

        self.connect(self.browse, SIGNAL('clicked()'), self.choose_filename)

        self.connect(self.cancel, SIGNAL('clicked()'), self.reject)
        self.connect(self.save, SIGNAL('clicked()'), self.save_archive)


    def save_archive(self):
        filename = self.filename
        if not filename:
            return
        if os.path.exists(filename):
            title = 'Overwrite File?'
            msg = 'The file "%s" exists and will be overwritten.' % filename
            info_txt = 'Overwrite "%s"?' % filename
            ok_txt = 'Overwrite'
            icon = qtutils.save_icon()
            if not qtutils.confirm(title, msg, info_txt, ok_txt,
                                   default=False, icon=icon):
                return
        self.accept()

    def choose_filename(self):
        filename = qtutils.save_as(self.filename)
        if not filename:
            return
        self.filetext.setText(filename)
        self.update_filetext_for_format(self.format_combo.currentIndex())

    def filetext_changed(self, qstr):
        self.filename = unicode(qstr)
        self.save.setEnabled(bool(self.filename))
        prefix = self.strip_exts(os.path.basename(self.filename)) + '/'
        self.prefix_text.setText(prefix)

    def prefix_text_changed(self, qstr):
        self.prefix = unicode(qstr)

    def strip_exts(self, text):
        for format_string in self.format_strings:
            ext = '.'+format_string
            if text.endswith(ext):
                return text[:-len(ext)]
        return text

    def update_filetext_for_format(self, idx):
        self.fmt = self.format_strings[idx]
        text = self.strip_exts(unicode(self.filetext.text()))
        self.filename = '%s.%s' % (text, self.fmt)
        self.filetext.setText(self.filename)
        self.filetext.setFocus(True)
        if '/' in text:
            start = text.rindex('/') + 1
        else:
            start = 0
        self.filetext.setSelection(start, len(text) - start)

    def prefix_group_expanded(self, expanded):
        if expanded:
            self.prefix_text.setFocus(True)
        else:
            self.filetext.setFocus(True)


if __name__ == '__main__':
    from cola.app import ColaApplication
    app = ColaApplication([])
    dlg = GitArchiveDialog('master')
    dlg.show()
    dlg.raise_()
    app.exec_()
