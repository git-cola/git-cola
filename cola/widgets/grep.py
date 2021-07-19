from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..i18n import N_
from ..utils import Group
from .. import cmds
from .. import core
from .. import hotkeys
from .. import utils
from .. import qtutils
from ..qtutils import get
from .standard import Dialog
from .text import HintedLineEdit
from .text import VimHintedPlainTextEdit
from .text import VimTextBrowser
from . import defs


def grep(context):
    """Prompt and use 'git grep' to find the content."""
    widget = new_grep(context, parent=qtutils.active_window())
    widget.show()
    return widget


def new_grep(context, text=None, parent=None):
    """Construct a new Grep dialog"""
    widget = Grep(context, parent=parent)
    if text:
        widget.search_for(text)
    return widget


def parse_grep_line(line):
    """Parse a grep result line into (filename, line_number, content)"""
    try:
        filename, line_number, contents = line.split(':', 2)
        result = (filename, line_number, contents)
    except ValueError:
        result = None
    return result


def goto_grep(context, line):
    """Called when Search -> Grep's right-click 'goto' action."""
    parsed_line = parse_grep_line(line)
    if parsed_line:
        filename, line_number, _ = parsed_line
        cmds.do(
            cmds.Edit,
            context,
            [filename],
            line_number=line_number,
            background_editor=True,
        )


class GrepThread(QtCore.QThread):
    """Gather `git grep` results in a background thread"""

    result = Signal(object, object, object)

    def __init__(self, context, parent):
        QtCore.QThread.__init__(self, parent)
        self.context = context
        self.query = None
        self.shell = False
        self.regexp_mode = '--basic-regexp'

    def run(self):
        if self.query is None:
            return
        git = self.context.git
        query = self.query
        if self.shell:
            args = utils.shell_split(query)
        else:
            args = [query]
        status, out, err = git.grep(self.regexp_mode, n=True, *args)
        if query == self.query:
            self.result.emit(status, out, err)
        else:
            self.run()


class Grep(Dialog):
    """A dialog for searching content using `git grep`"""

    def __init__(self, context, parent=None):
        Dialog.__init__(self, parent)
        self.context = context
        self.grep_result = ''

        self.setWindowTitle(N_('Search'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.edit_action = qtutils.add_action(self, N_('Edit'), self.edit, hotkeys.EDIT)

        self.refresh_action = qtutils.add_action(
            self, N_('Refresh'), self.search, *hotkeys.REFRESH_HOTKEYS
        )

        self.input_label = QtWidgets.QLabel('git grep')
        self.input_label.setFont(qtutils.diff_font(context))

        self.input_txt = HintedLineEdit(
            context, N_('command-line arguments'), parent=self
        )

        self.regexp_combo = combo = QtWidgets.QComboBox()
        combo.setToolTip(N_('Choose the "git grep" regular expression mode'))
        items = [N_('Basic Regexp'), N_('Extended Regexp'), N_('Fixed String')]
        combo.addItems(items)
        combo.setCurrentIndex(0)
        combo.setEditable(False)

        tooltip0 = N_('Search using a POSIX basic regular expression')
        tooltip1 = N_('Search using a POSIX extended regular expression')
        tooltip2 = N_('Search for a fixed string')
        combo.setItemData(0, tooltip0, Qt.ToolTipRole)
        combo.setItemData(1, tooltip1, Qt.ToolTipRole)
        combo.setItemData(2, tooltip2, Qt.ToolTipRole)
        combo.setItemData(0, '--basic-regexp', Qt.UserRole)
        combo.setItemData(1, '--extended-regexp', Qt.UserRole)
        combo.setItemData(2, '--fixed-strings', Qt.UserRole)

        self.result_txt = GrepTextView(context, N_('grep result...'), self)
        self.preview_txt = PreviewTextView(context, self)
        self.preview_txt.setFocusProxy(self.result_txt)

        self.edit_button = qtutils.edit_button(default=True)
        qtutils.button_action(self.edit_button, self.edit_action)

        self.refresh_button = qtutils.refresh_button()
        qtutils.button_action(self.refresh_button, self.refresh_action)

        text = N_('Shell arguments')
        tooltip = N_(
            'Parse arguments using a shell.\n'
            'Queries with spaces will require "double quotes".'
        )
        self.shell_checkbox = qtutils.checkbox(
            text=text, tooltip=tooltip, checked=False
        )
        self.close_button = qtutils.close_button()

        self.refresh_group = Group(self.refresh_action, self.refresh_button)
        self.refresh_group.setEnabled(False)

        self.edit_group = Group(self.edit_action, self.edit_button)
        self.edit_group.setEnabled(False)

        self.input_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.input_label,
            self.input_txt,
            self.regexp_combo,
        )

        self.bottom_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.close_button,
            qtutils.STRETCH,
            self.shell_checkbox,
            self.refresh_button,
            self.edit_button,
        )

        self.splitter = qtutils.splitter(Qt.Vertical, self.result_txt, self.preview_txt)

        self.mainlayout = qtutils.vbox(
            defs.margin,
            defs.no_spacing,
            self.input_layout,
            self.splitter,
            self.bottom_layout,
        )
        self.setLayout(self.mainlayout)

        thread = self.worker_thread = GrepThread(context, self)
        thread.result.connect(self.process_result, type=Qt.QueuedConnection)

        # pylint: disable=no-member
        self.input_txt.textChanged.connect(lambda s: self.search())
        self.regexp_combo.currentIndexChanged.connect(lambda x: self.search())
        self.result_txt.leave.connect(self.input_txt.setFocus)
        self.result_txt.cursorPositionChanged.connect(self.update_preview)

        qtutils.add_action(
            self.input_txt,
            'Focus Results',
            self.focus_results,
            hotkeys.DOWN,
            *hotkeys.ACCEPT
        )
        qtutils.add_action(self, 'Focus Input', self.focus_input, hotkeys.FOCUS)

        qtutils.connect_toggle(self.shell_checkbox, lambda x: self.search())
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        self.init_size(parent=parent)

    def focus_input(self):
        """Focus the grep input field and select the text"""
        self.input_txt.setFocus()
        self.input_txt.selectAll()

    def focus_results(self):
        """Give focus to the results window"""
        self.result_txt.setFocus()

    def regexp_mode(self):
        """Return the selected grep regex mode"""
        idx = self.regexp_combo.currentIndex()
        return self.regexp_combo.itemData(idx, Qt.UserRole)

    def search(self):
        """Initiate a search by starting the GrepThread"""
        self.edit_group.setEnabled(False)
        self.refresh_group.setEnabled(False)

        query = get(self.input_txt)
        if len(query) < 2:
            self.result_txt.clear()
            self.preview_txt.clear()
            return
        self.worker_thread.query = query
        self.worker_thread.shell = get(self.shell_checkbox)
        self.worker_thread.regexp_mode = self.regexp_mode()
        self.worker_thread.start()

    def search_for(self, txt):
        """Set the initial value of the input text"""
        self.input_txt.set_value(txt)

    def text_scroll(self):
        """Return the scrollbar value for the results window"""
        scrollbar = self.result_txt.verticalScrollBar()
        if scrollbar:
            return get(scrollbar)
        return None

    def set_text_scroll(self, scroll):
        """Set the scrollbar value for the results window"""
        scrollbar = self.result_txt.verticalScrollBar()
        if scrollbar and scroll is not None:
            scrollbar.setValue(scroll)

    def text_offset(self):
        """Return the cursor's offset within the result text"""
        return self.result_txt.textCursor().position()

    def set_text_offset(self, offset):
        """Set the text cursor from an offset"""
        cursor = self.result_txt.textCursor()
        cursor.setPosition(offset)
        self.result_txt.setTextCursor(cursor)

    def process_result(self, status, out, err):
        """Apply the results from grep to the widgets"""
        if status == 0:
            value = out + err
        elif out + err:
            value = 'git grep: ' + out + err
        else:
            value = ''

        # save scrollbar and text cursor
        scroll = self.text_scroll()
        offset = min(len(value), self.text_offset())

        self.grep_result = value
        self.result_txt.set_value(value)
        # restore
        self.set_text_scroll(scroll)
        self.set_text_offset(offset)

        enabled = status == 0
        self.edit_group.setEnabled(enabled)
        self.refresh_group.setEnabled(True)
        if not value:
            self.preview_txt.clear()

    def update_preview(self):
        """Update the file preview window"""
        parsed_line = parse_grep_line(self.result_txt.selected_line())
        if parsed_line:
            filename, line_number, _ = parsed_line
            self.preview_txt.preview(filename, line_number)

    def edit(self):
        """Launch an editor on the currently selected line"""
        goto_grep(self.context, self.result_txt.selected_line())

    def export_state(self):
        """Export persistent settings"""
        state = super(Grep, self).export_state()
        state['sizes'] = get(self.splitter)
        return state

    def apply_state(self, state):
        """Apply persistent settings"""
        result = super(Grep, self).apply_state(state)
        try:
            self.splitter.setSizes(state['sizes'])
        except (AttributeError, KeyError, ValueError, TypeError):
            result = False
        return result


# pylint: disable=too-many-ancestors
class GrepTextView(VimHintedPlainTextEdit):
    """A text view with hotkeys for launching editors"""

    def __init__(self, context, hint, parent):
        VimHintedPlainTextEdit.__init__(self, context, hint, parent=parent)
        self.context = context
        self.goto_action = qtutils.add_action(self, 'Launch Editor', self.edit)
        self.goto_action.setShortcut(hotkeys.EDIT)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.pos())
        menu.addSeparator()
        menu.addAction(self.goto_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def edit(self):
        goto_grep(self.context, self.selected_line())


class PreviewTask(qtutils.Task):
    """Asynchronous task for loading file content"""

    def __init__(self, parent, filename, line_number):
        qtutils.Task.__init__(self, parent)

        self.content = ''
        self.filename = filename
        self.line_number = line_number

    def task(self):
        try:
            self.content = core.read(self.filename, errors='ignore')
        except IOError:
            pass
        return (self.filename, self.content, self.line_number)


# pylint: disable=too-many-ancestors
class PreviewTextView(VimTextBrowser):
    """Preview window for file contents"""

    def __init__(self, context, parent):
        VimTextBrowser.__init__(self, context, parent)
        self.filename = None
        self.content = None
        self.runtask = qtutils.RunTask(parent=self)

    def preview(self, filename, line_number):
        """Preview the a file at the specified line number"""

        if filename != self.filename:
            request = PreviewTask(self, filename, line_number)
            self.runtask.start(request, finish=self.show_preview)
        else:
            self.scroll_to_line(line_number)

    def clear(self):
        self.filename = ''
        self.content = ''
        super(PreviewTextView, self).clear()

    def show_preview(self, task):
        """Show the results of the asynchronous file read"""

        filename = task.filename
        content = task.content
        line_number = task.line_number

        if filename != self.filename:
            self.filename = filename
            self.content = content
            self.set_value(content)

        self.scroll_to_line(line_number)

    def scroll_to_line(self, line_number):
        """Scroll to the specified line number"""
        try:
            line_num = int(line_number) - 1
        except ValueError:
            return

        self.numbers.set_highlighted(line_num)
        cursor = self.textCursor()
        cursor.setPosition(0)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

        cursor.movePosition(cursor.Down, cursor.MoveAnchor, line_num)
        cursor.movePosition(cursor.EndOfLine, cursor.KeepAnchor)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

        scrollbar = self.verticalScrollBar()
        step = scrollbar.pageStep() // 2
        position = scrollbar.sliderPosition() + step
        scrollbar.setSliderPosition(position)
        self.ensureCursorVisible()
