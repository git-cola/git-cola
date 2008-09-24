from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QMainWindow

from cola import qtutils
from cola import syntax
from cola.syntax import DiffSyntaxHighlighter
from cola.gui.main import Ui_main

def CreateStandardView(uiclass, qtclass, *classes):
    """CreateStandardView returns a class closure of uiclass and qtclass.
    This class performs the standard setup common to all view classes."""
    class StandardView(uiclass, qtclass):
        def __init__(self, parent=None, *args, **kwargs):
            qtclass.__init__(self, parent)
            uiclass.__init__(self)
            self.parent_view = parent
            syntax.set_theme_properties(self)
            self.setupUi(self)
            self.init(parent, *args, **kwargs)
            for cls in classes:
                cls.init(self, parent, *args, **kwargs)
        def init(self, parent, *args, **kwargs):
            pass
        def get_properties(self):
            # user-definable color properties
            props = {}
            for name in syntax.default_colors:
                props[name] = getattr(self, '_'+name)
            return props
        def reset_syntax(self):
            if hasattr(self, 'syntax') and self.syntax:
                self.syntax.set_colors(self.get_properties())
                self.syntax.reset()
    syntax.install_theme_properties(StandardView)
    return StandardView

class View(CreateStandardView(Ui_main, QMainWindow)):
    """The main cola interface."""
    def init(self, parent=None):
        self.staged.setAlternatingRowColors(True)
        self.unstaged.setAlternatingRowColors(True)
        self.set_display = self.display_text.setText
        self.amend_is_checked = self.amend_radio.isChecked
        self.action_undo = self.commitmsg.undo
        self.action_redo = self.commitmsg.redo
        self.action_paste = self.commitmsg.paste
        self.action_select_all = self.commitmsg.selectAll

        # Qt does not support noun/verbs
        self.commit_button.setText(qtutils.tr('Commit@@verb'))
        self.commit_menu.setTitle(qtutils.tr('Commit@@verb'))

        self.tabifyDockWidget(self.diff_dock, self.editor_dock)

        # Default to creating a new commit(i.e. not an amend commit)
        self.new_commit_radio.setChecked(True)
        self.toolbar_show_log =\
            self.toolbar.addAction(qtutils.get_qicon('git.png'),
                                   'Show/Hide Log Window')
        self.toolbar_show_log.setEnabled(True)

        # Diff/patch syntax highlighter
        self.syntax = DiffSyntaxHighlighter(self.display_text.document())

        # Handle the vertical checkbox action
        self.connect(self.vertical_checkbox,
                     SIGNAL('clicked(bool)'),
                     self.handle_vertical_checkbox)

        # Display the current column
        self.connect(self.commitmsg,
                     SIGNAL('cursorPositionChanged()'),
                     self.show_current_column)

        # Initialize the GUI to show 'Column: 00'
        self.show_current_column()

    def handle_vertical_checkbox(self, checked):
        if checked:
            self.splitter.setOrientation(Qt.Vertical)
        else:
            self.splitter.setOrientation(Qt.Horizontal)

    def set_info(self, txt):
        try:
            translated = self.tr(unicode(txt))
        except:
            translated = unicode(txt)
        self.statusBar().showMessage(translated)
    def show_editor(self):
        self.editor_dock.raise_()
    def show_diff(self):
        self.diff_dock.raise_()

    def action_cut(self):
        self.action_copy()
        self.action_delete()
    def action_copy(self):
        cursor = self.commitmsg.textCursor()
        selection = cursor.selection().toPlainText()
        qtutils.set_clipboard(selection)
    def action_delete(self):
        self.commitmsg.textCursor().removeSelectedText()
    def reset_checkboxes(self):
        self.new_commit_radio.setChecked(True)
        self.amend_radio.setChecked(False)
    def reset_display(self):
        self.set_display('')
        self.set_info('')
    def copy_display(self):
        cursor = self.display_text.textCursor()
        selection = cursor.selection().toPlainText()
        qtutils.set_clipboard(selection)
    def diff_selection(self):
        cursor = self.display_text.textCursor()
        offset = cursor.position()
        selection = cursor.selection().toPlainText()
        return offset, selection
    def selected_line(self):
        cursor = self.display_text.textCursor()
        offset = cursor.position()
        contents = unicode(self.display_text.toPlainText())
        while (offset >= 1
                and contents[offset-1]
                and contents[offset-1] != '\n'):
            offset -= 1
        data = contents[offset:]
        if '\n' in data:
            line, rest = data.split('\n', 1)
        else:
            line = data
        return line
    def display(self, text):
        self.set_display(text)
        self.diff_dock.raise_()
    def show_current_column(self):
        cursor = self.commitmsg.textCursor()
        colnum = cursor.columnNumber()
        self.column_label.setText('Column: %02d' % colnum)

