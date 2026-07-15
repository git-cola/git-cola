from qtpy import QtWidgets
from .. import qtutils
from ..i18n import N_
from . import standard
from . import diff


def summarize_changes(diff_text, filenames):
    """Build a concise diff-stat summary for the revert confirmation dialog."""
    file_count = len(filenames)
    if not diff_text:
        return {
            'file_count': file_count,
            'changed_lines': 0,
            'added_lines': 0,
            'removed_lines': 0,
        }

    added_lines = 0
    removed_lines = 0

    for line in diff_text.splitlines():
        if line.startswith('+++ ') or line.startswith('--- '):
            continue
        if line.startswith('+') and not line.startswith('+++'):
            added_lines += 1
        elif line.startswith('-') and not line.startswith('---'):
            removed_lines += 1

    return {
        'file_count': file_count,
        'changed_lines': added_lines + removed_lines,
        'added_lines': added_lines,
        'removed_lines': removed_lines,
    }


class RevertConfirmDialog(standard.Dialog):
    def __init__(self, context, title, message, diff_text, filenames, parent=None):
        super().__init__(parent)
        self.context = context
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(640, 420)
        self.setSizeGripEnabled(True)

        msg = QtWidgets.QLabel(message)
        msg.setWordWrap(True)

        summary = summarize_changes(diff_text, filenames)
        summary_text = (
            f"{N_('Files')}: {summary['file_count']}\n"
            f"{N_('Insertions')}: {summary['added_lines']}\n"
            f"{N_('Deletions')}: {summary['removed_lines']}"
        )
        summary_label = QtWidgets.QLabel(summary_text)
        summary_label.setWordWrap(True)
        summary_label.setFrameShape(QtWidgets.QFrame.Shape.Panel)
        summary_label.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        summary_label.setContentsMargins(8, 8, 8, 8)
        summary_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        summary_label.setMaximumHeight(96)

        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator.setContentsMargins(0, 4, 0, 4)

        files_group = QtWidgets.QGroupBox(N_('Files to revert:'))
        files_group.setStyleSheet('QGroupBox { padding-top: 16px; }')
        files_layout = QtWidgets.QVBoxLayout()
        files_layout.setContentsMargins(10, 12, 10, 8)
        files_text = QtWidgets.QPlainTextEdit()
        files_text.setPlainText('\n'.join(filenames))
        files_text.setReadOnly(True)
        files_text.setMaximumHeight(120)
        files_text.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        files_layout.addWidget(files_text)
        files_group.setLayout(files_layout)
        files_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        diff_group = QtWidgets.QGroupBox(N_('Changes to be reverted:'))
        diff_group.setStyleSheet('QGroupBox { padding-top: 16px; }')
        diff_layout = QtWidgets.QVBoxLayout()
        diff_layout.setContentsMargins(10, 12, 10, 8)
        # Use the application's DiffTextEdit to get proper syntax highlighting
        diff_edit = diff.DiffTextEdit(self.context, self)
        diff_edit.setPlainText(diff_text or N_('(no changes)'))
        diff_edit.setReadOnly(True)
        diff_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        diff_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        diff_layout.addWidget(diff_edit)
        diff_group.setLayout(diff_layout)
        diff_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        ok_btn = QtWidgets.QPushButton(N_('Revert'))
        cancel_btn = QtWidgets.QPushButton(N_('Cancel'))
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(msg)
        layout.addWidget(summary_label)
        layout.addWidget(separator)
        layout.addWidget(files_group)
        layout.addWidget(diff_group, stretch=1)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.resize(760, 560)