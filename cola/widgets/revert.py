from qtpy import QtWidgets
from .. import qtutils
from ..i18n import N_
from . import standard

class RevertConfirmDialog(standard.Dialog):
    def __init__(self, title, message, diff_text, filenames, parent=None):
           
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        
        msg = QtWidgets.QLabel(message)
        msg.setWordWrap(True)
        
        files_group = QtWidgets.QGroupBox(N_('Files to revert:'))
        files_layout = QtWidgets.QVBoxLayout()
        files_text = QtWidgets.QPlainTextEdit()
        files_text.setPlainText('\n'.join(filenames))
        files_text.setReadOnly(True)
        files_text.setMaximumHeight(80)
        files_layout.addWidget(files_text)
        files_group.setLayout(files_layout)
        
        diff_group = QtWidgets.QGroupBox(N_('Changes to be reverted:'))
        diff_layout = QtWidgets.QVBoxLayout()
        diff_edit = QtWidgets.QPlainTextEdit()
        diff_edit.setPlainText(diff_text or N_('(no changes)'))
        diff_edit.setReadOnly(True)
        diff_edit.setFont(qtutils.default_monospace_font())
        diff_layout.addWidget(diff_edit)
        diff_group.setLayout(diff_layout)
        
        ok_btn = QtWidgets.QPushButton(N_('Revert'))
        cancel_btn = QtWidgets.QPushButton(N_('Cancel'))
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(msg)
        layout.addWidget(files_group)
        layout.addWidget(diff_group, stretch=1)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.resize(700, 500)