from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import guicmds
from cola import utils
from cola import qtutils
from cola.git import git
from cola.prefs import diff_font
from cola.widgets import defs
from cola.widgets.standard import Dialog
from cola.widgets.text import HintedTextView, HintedLineEdit


class GrepThread(QtCore.QThread):
    def __init__(self, parent):
        QtCore.QThread.__init__(self, parent)
        self.txt = None
        self.shell = False

    def run(self):
        if self.txt is None:
            return
        if self.shell:
            args = utils.shell_split(self.txt)
        else:
            args = [self.txt]
        result = core.decode(git.grep(with_stderr=True, n=True, *args))
        self.emit(SIGNAL('result'), result)


class Grep(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowModality(Qt.WindowModal)

        self.input_label = QtGui.QLabel('git grep')
        self.input_label.setFont(diff_font())

        hint = 'command-line arguments'
        self.input_txt = HintedLineEdit(hint, self)
        self.input_txt.enable_hint(True)

        hint = 'grep result...'
        self.result_txt = GrepTextView(hint, self)
        self.result_txt.enable_hint(True)

        self.search_button = QtGui.QPushButton('Search')
        self.shell_checkbox = QtGui.QCheckBox('Shell arguments')
        self.shell_checkbox.setToolTip(
                'Parse arguments using a shell.\n'
                'Queries with spaces will require "double quotes".')
        self.shell_checkbox.setChecked(False)

        self.close_button = QtGui.QPushButton('Close')

        self.input_layout = QtGui.QHBoxLayout()
        self.input_layout.setMargin(0)
        self.input_layout.setSpacing(defs.button_spacing)

        self.bottom_layout = QtGui.QHBoxLayout()
        self.bottom_layout.setMargin(0)
        self.bottom_layout.setSpacing(defs.button_spacing)

        self.mainlayout = QtGui.QVBoxLayout()
        self.mainlayout.setMargin(defs.margin)
        self.mainlayout.setSpacing(defs.spacing)

        self.input_layout.addWidget(self.input_label)
        self.input_layout.addWidget(self.input_txt)
        self.input_layout.addWidget(self.search_button)

        self.bottom_layout.addWidget(self.shell_checkbox)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.close_button)

        self.mainlayout.addLayout(self.input_layout)
        self.mainlayout.addWidget(self.result_txt)
        self.mainlayout.addLayout(self.bottom_layout)
        self.setLayout(self.mainlayout)

        self.grep_thread = GrepThread(self)
        self.search_button.setEnabled(False)

        self.connect(self.grep_thread, SIGNAL('result'),
                     self.process_result)

        self.connect(self.input_txt, SIGNAL('textChanged(QString)'),
                     lambda x: self.search_button.setEnabled(bool(unicode(x))))

        qtutils.connect_button(self.search_button, self.search)
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        if not qtutils.apply_state(self):
            self.resize(666, 420)

    def done(self, exit_code):
        qtutils.save_state(self)
        return Dialog.done(self, exit_code)

    def search(self):
        self.grep_thread.txt = self.input_txt.as_unicode()
        self.grep_thread.shell = self.shell_checkbox.isChecked()
        self.grep_thread.start()
        self.search_button.setEnabled(False)

    def search_for(self, txt):
        self.input_txt.set_value(txt)
        self.run()

    def process_result(self, result):
        self.result_txt.set_value(result)
        self.search_button.setEnabled(True)


class GrepTextView(HintedTextView):
    def __init__(self, hint, parent):
        HintedTextView.__init__(self, hint, parent)
        self.goto_action = qtutils.add_action(
                self, 'Launch Editor',
                lambda: guicmds.goto_grep(self.selected_line()),
                'Ctrl+E')

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.pos())
        menu.addSeparator()
        menu.addAction(self.goto_action)
        menu.exec_(self.mapToGlobal(event.pos()))


def run_grep(txt=None, parent=None):
    widget = Grep(parent)
    if txt is not None:
        widget.search_for(txt)
    return widget
