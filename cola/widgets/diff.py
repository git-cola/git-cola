from __future__ import division, absolute_import, unicode_literals
import os
import re

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..i18n import N_
from ..interaction import Interaction
from ..models import prefs
from ..qtutils import get
from .. import actions
from .. import cmds
from .. import core
from .. import diffparse
from .. import gitcmds
from .. import gravatar
from .. import hotkeys
from .. import icons
from .. import utils
from .. import qtutils
from .text import TextDecorator
from .text import VimHintedPlainTextEdit
from . import defs
from . import imageview


COMMITS_SELECTED = 'COMMITS_SELECTED'
FILES_SELECTED = 'FILES_SELECTED'


class DiffSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    """Implements the diff syntax highlighting"""

    INITIAL_STATE = -1
    DEFAULT_STATE = 0
    DIFFSTAT_STATE = 1
    DIFF_FILE_HEADER_STATE = 2
    DIFF_STATE = 3
    SUBMODULE_STATE = 4
    END_STATE = 5

    DIFF_FILE_HEADER_START_RGX = re.compile(r'diff --git a/.* b/.*')
    DIFF_HUNK_HEADER_RGX = re.compile(r'(?:@@ -[0-9,]+ \+[0-9,]+ @@)|'
                                      r'(?:@@@ (?:-[0-9,]+ ){2}\+[0-9,]+ @@@)')
    BAD_WHITESPACE_RGX = re.compile(r'\s+$')

    def __init__(self, context, doc, whitespace=True, is_commit=False):
        QtGui.QSyntaxHighlighter.__init__(self, doc)
        self.whitespace = whitespace
        self.enabled = True
        self.is_commit = is_commit

        QPalette = QtGui.QPalette
        cfg = context.cfg
        palette = QPalette()
        disabled = palette.color(QPalette.Disabled, QPalette.Text)
        header = qtutils.rgb_hex(disabled)

        self.color_text = qtutils.RGB(cfg.color('text', '030303'))
        self.color_add = qtutils.RGB(cfg.color('add', 'd2ffe4'))
        self.color_remove = qtutils.RGB(cfg.color('remove', 'fee0e4'))
        self.color_header = qtutils.RGB(cfg.color('header', header))

        self.diff_header_fmt = qtutils.make_format(fg=self.color_header)
        self.bold_diff_header_fmt = qtutils.make_format(
            fg=self.color_header, bold=True)

        self.diff_add_fmt = qtutils.make_format(
            fg=self.color_text, bg=self.color_add)
        self.diff_remove_fmt = qtutils.make_format(
            fg=self.color_text, bg=self.color_remove)
        self.bad_whitespace_fmt = qtutils.make_format(bg=Qt.red)
        self.setCurrentBlockState(self.INITIAL_STATE)

    def set_enabled(self, enabled):
        self.enabled = enabled

    def highlightBlock(self, text):
        if not self.enabled or not text:
            return
        # Aliases for quick local access
        initial_state = self.INITIAL_STATE
        default_state = self.DEFAULT_STATE
        diff_state = self.DIFF_STATE
        diffstat_state = self.DIFFSTAT_STATE
        diff_file_header_state = self.DIFF_FILE_HEADER_STATE
        submodule_state = self.SUBMODULE_STATE
        end_state = self.END_STATE

        diff_file_header_start_rgx = self.DIFF_FILE_HEADER_START_RGX
        diff_hunk_header_rgx = self.DIFF_HUNK_HEADER_RGX
        bad_whitespace_rgx = self.BAD_WHITESPACE_RGX

        diff_header_fmt = self.diff_header_fmt
        bold_diff_header_fmt = self.bold_diff_header_fmt
        diff_add_fmt = self.diff_add_fmt
        diff_remove_fmt = self.diff_remove_fmt
        bad_whitespace_fmt = self.bad_whitespace_fmt

        state = self.previousBlockState()
        if state == initial_state:
            if text.startswith('Submodule '):
                state = submodule_state
            elif text.startswith('diff --git '):
                state = diffstat_state
            elif self.is_commit:
                state = default_state
            else:
                state = diffstat_state

        if state == diffstat_state:
            if diff_file_header_start_rgx.match(text):
                state = diff_file_header_state
                self.setFormat(0, len(text), diff_header_fmt)
            elif diff_hunk_header_rgx.match(text):
                state = diff_state
                self.setFormat(0, len(text), bold_diff_header_fmt)
            elif '|' in text:
                i = text.index('|')
                self.setFormat(0, i, bold_diff_header_fmt)
                self.setFormat(i, len(text) - i, diff_header_fmt)
            else:
                self.setFormat(0, len(text), diff_header_fmt)
        elif state == diff_file_header_state:
            if diff_hunk_header_rgx.match(text):
                state = diff_state
                self.setFormat(0, len(text), bold_diff_header_fmt)
            else:
                self.setFormat(0, len(text), diff_header_fmt)
        elif state == diff_state:
            if diff_file_header_start_rgx.match(text):
                state = diff_file_header_state
                self.setFormat(0, len(text), diff_header_fmt)
            elif diff_hunk_header_rgx.match(text):
                self.setFormat(0, len(text), bold_diff_header_fmt)
            elif text.startswith('-'):
                if text == '-- ':
                    state = end_state
                else:
                    self.setFormat(0, len(text), diff_remove_fmt)
            elif text.startswith('+'):
                self.setFormat(0, len(text), diff_add_fmt)
                if self.whitespace:
                    m = bad_whitespace_rgx.search(text)
                    if m is not None:
                        i = m.start()
                        self.setFormat(i, len(text) - i, bad_whitespace_fmt)

        self.setCurrentBlockState(state)


class DiffTextEdit(VimHintedPlainTextEdit):

    def __init__(self, context, parent,
                 is_commit=False, whitespace=True, numbers=False):
        VimHintedPlainTextEdit.__init__(self, context, '', parent=parent)
        # Diff/patch syntax highlighter
        self.highlighter = DiffSyntaxHighlighter(
            context, self.document(),
            is_commit=is_commit, whitespace=whitespace)
        if numbers:
            self.numbers = DiffLineNumbers(context, self)
            self.numbers.hide()
        else:
            self.numbers = None
        self.scrollvalue = None

        self.cursorPositionChanged.connect(self._cursor_changed)

    def _cursor_changed(self):
        """Update the line number display when the cursor changes"""
        line_number = max(0, self.textCursor().blockNumber())
        if self.numbers:
            self.numbers.set_highlighted(line_number)

    def resizeEvent(self, event):
        super(DiffTextEdit, self).resizeEvent(event)
        if self.numbers:
            self.numbers.refresh_size()

    def save_scrollbar(self):
        """Save the scrollbar value, but only on the first call"""
        if self.scrollvalue is None:
            scrollbar = self.verticalScrollBar()
            if scrollbar:
                scrollvalue = get(scrollbar)
            else:
                scrollvalue = None
            self.scrollvalue = scrollvalue

    def restore_scrollbar(self):
        """Restore the scrollbar and clear state"""
        scrollbar = self.verticalScrollBar()
        scrollvalue = self.scrollvalue
        if scrollbar and scrollvalue is not None:
            scrollbar.setValue(scrollvalue)
        self.scrollvalue = None

    def set_loading_message(self):
        self.hint.set_value('+++ ' + N_('Loading...'))
        self.set_value('')

    def set_diff(self, diff):
        """Set the diff text, but save the scrollbar"""
        diff = diff.rstrip('\n')  # diffs include two empty newlines
        self.save_scrollbar()

        self.hint.set_value('')
        if self.numbers:
            self.numbers.set_diff(diff)
        self.set_value(diff)

        self.restore_scrollbar()


class DiffLineNumbers(TextDecorator):

    def __init__(self, context, parent):
        TextDecorator.__init__(self, parent)
        self.highlight_line = -1
        self.lines = None
        self.parser = diffparse.DiffLines()
        self.formatter = diffparse.FormatDigits()

        self.setFont(qtutils.diff_font(context))
        self._char_width = self.fontMetrics().width('0')

        QPalette = QtGui.QPalette
        self._palette = palette = self.palette()
        self._base = palette.color(QtGui.QPalette.Base)
        self._highlight = palette.color(QPalette.Highlight)
        self._highlight_text = palette.color(QPalette.HighlightedText)
        self._window = palette.color(QPalette.Window)
        self._disabled = palette.color(QPalette.Disabled, QPalette.Text)

    def set_diff(self, diff):
        parser = self.parser
        lines = parser.parse(diff)
        if parser.valid:
            self.lines = lines
            self.formatter.set_digits(self.parser.digits())
        else:
            self.lines = None

    def set_lines(self, lines):
        self.lines = lines

    def width_hint(self):
        if not self.isVisible():
            return 0
        parser = self.parser

        if parser.merge:
            columns = 3
            extra = 3  # one space in-between, one space after
        else:
            columns = 2
            extra = 2  # one space in-between, one space after

        if parser.valid:
            digits = parser.digits() * columns
        else:
            digits = 4

        return defs.margin + (self._char_width * (digits + extra))

    def set_highlighted(self, line_number):
        """Set the line to highlight"""
        self.highlight_line = line_number

    def current_line(self):
        if self.lines and self.highlight_line >= 0:
            # Find the next valid line
            for line in self.lines[self.highlight_line:]:
                # take the "new" line number: last value in tuple
                line_number = line[-1]
                if line_number > 0:
                    return line_number

            # Find the previous valid line
            for line in self.lines[self.highlight_line-1::-1]:
                # take the "new" line number: last value in tuple
                line_number = line[-1]
                if line_number > 0:
                    return line_number
        return None

    def paintEvent(self, event):
        """Paint the line number"""
        if not self.lines:
            return

        painter = QtGui.QPainter(self)
        painter.fillRect(event.rect(), self._base)

        editor = self.editor
        content_offset = editor.contentOffset()
        block = editor.firstVisibleBlock()
        width = self.width()
        event_rect_bottom = event.rect().bottom()

        highlight = self._highlight
        highlight_text = self._highlight_text
        disabled = self._disabled

        fmt = self.formatter
        lines = self.lines
        num_lines = len(self.lines)
        painter.setPen(disabled)
        text = ''

        while block.isValid():
            block_number = block.blockNumber()
            if block_number >= num_lines:
                break
            block_geom = editor.blockBoundingGeometry(block)
            block_top = block_geom.translated(content_offset).top()
            if not block.isVisible() or block_top >= event_rect_bottom:
                break

            rect = block_geom.translated(content_offset).toRect()
            if block_number == self.highlight_line:
                painter.fillRect(rect.x(), rect.y(),
                                 width, rect.height(), highlight)
                painter.setPen(highlight_text)
            else:
                painter.setPen(disabled)

            line = lines[block_number]
            if len(line) == 2:
                a, b = line
                text = fmt.value(a, b)
            elif len(line) == 3:
                old, base, new = line
                text = fmt.merge_value(old, base, new)

            painter.drawText(rect.x(), rect.y(),
                             self.width() - (defs.margin * 2), rect.height(),
                             Qt.AlignRight | Qt.AlignVCenter, text)

            block = block.next()  # pylint: disable=next-method-called


class Viewer(QtWidgets.QFrame):
    """Text and image diff viewers"""

    images_changed = Signal(object)
    type_changed = Signal(object)

    def __init__(self, context, parent=None):
        super(Viewer, self).__init__(parent)

        self.context = context
        self.model = model = context.model
        self.images = []
        self.pixmaps = []
        self.options = options = Options(self)
        self.text = DiffEditor(context, options, self)
        self.image = imageview.ImageView(parent=self)
        self.image.setFocusPolicy(Qt.NoFocus)

        stack = self.stack = QtWidgets.QStackedWidget(self)
        stack.addWidget(self.text)
        stack.addWidget(self.image)

        self.main_layout = qtutils.vbox(
            defs.no_margin, defs.no_spacing, self.stack)
        self.setLayout(self.main_layout)

        # Observe images
        images_msg = model.message_images_changed
        model.add_observer(images_msg, self.images_changed.emit)
        self.images_changed.connect(self.set_images, type=Qt.QueuedConnection)

        # Observe the diff type
        diff_type_msg = model.message_diff_type_changed
        model.add_observer(diff_type_msg, self.type_changed.emit)
        self.type_changed.connect(self.set_diff_type, type=Qt.QueuedConnection)

        # Observe the image mode combo box
        options.image_mode.currentIndexChanged.connect(lambda _: self.render())
        options.zoom_mode.currentIndexChanged.connect(lambda _: self.render())

        self.setFocusProxy(self.text)

    def export_state(self, state):
        state['show_diff_line_numbers'] = self.text.show_line_numbers()
        state['image_diff_mode'] = self.options.image_mode.currentIndex()
        state['image_zoom_mode'] = self.options.zoom_mode.currentIndex()
        return state

    def apply_state(self, state):
        diff_numbers = bool(state.get('show_diff_line_numbers', False))
        self.text.enable_line_numbers(diff_numbers)

        image_mode = utils.asint(state.get('image_diff_mode', 0))
        self.options.image_mode.set_index(image_mode)

        zoom_mode = utils.asint(state.get('image_zoom_mode', 0))
        self.options.zoom_mode.set_index(zoom_mode)
        return True

    def set_diff_type(self, diff_type):
        """Manage the image and text diff views when selection changes"""
        self.options.set_diff_type(diff_type)
        if diff_type == 'image':
            self.stack.setCurrentWidget(self.image)
            self.render()
        else:
            self.stack.setCurrentWidget(self.text)

    def update_options(self):
        self.text.update_options()

    def reset(self):
        self.image.pixmap = QtGui.QPixmap()
        self.cleanup()

    def cleanup(self):
        for (image, unlink) in self.images:
            if unlink and core.exists(image):
                os.unlink(image)
        self.images = []

    def set_images(self, images):
        self.images = images
        self.pixmaps = []
        if not images:
            self.reset()
            return False

        # In order to comp, we first have to load all the images
        all_pixmaps = [QtGui.QPixmap(image[0]) for image in images]
        pixmaps = [pixmap for pixmap in all_pixmaps if not pixmap.isNull()]
        if not pixmaps:
            self.reset()
            return False

        self.pixmaps = pixmaps
        self.render()
        self.cleanup()
        return True

    def render(self):
        # Update images
        if self.pixmaps:
            mode = self.options.image_mode.currentIndex()
            if mode == self.options.SIDE_BY_SIDE:
                image = self.render_side_by_side()
            elif mode == self.options.DIFF:
                image = self.render_diff()
            elif mode == self.options.XOR:
                image = self.render_xor()
            elif mode == self.options.PIXEL_XOR:
                image = self.render_pixel_xor()
            else:
                image = self.render_side_by_side()
        else:
            image = QtGui.QPixmap()
        self.image.pixmap = image

        # Apply zoom
        zoom_mode = self.options.zoom_mode.currentIndex()
        zoom_factor = self.options.zoom_factors[zoom_mode][1]
        if zoom_factor > 0.0:
            self.image.resetTransform()
            self.image.scale(zoom_factor, zoom_factor)
            poly = self.image.mapToScene(self.image.viewport().rect())
            self.image.last_scene_roi = poly.boundingRect()

    def render_side_by_side(self):
        # Side-by-side lineup comp
        pixmaps = self.pixmaps
        width = sum([pixmap.width() for pixmap in pixmaps])
        height = max([pixmap.height() for pixmap in pixmaps])
        image = create_image(width, height)

        # Paint each pixmap
        painter = create_painter(image)
        x = 0
        for pixmap in pixmaps:
            painter.drawPixmap(x, 0, pixmap)
            x += pixmap.width()
        painter.end()

        return image

    def render_comp(self, comp_mode):
        # Get the max size to use as the render canvas
        pixmaps = self.pixmaps
        if len(pixmaps) == 1:
            return pixmaps[0]

        width = max([pixmap.width() for pixmap in pixmaps])
        height = max([pixmap.height() for pixmap in pixmaps])
        image = create_image(width, height)

        painter = create_painter(image)
        for pixmap in (pixmaps[0], pixmaps[-1]):
            x = (width - pixmap.width()) // 2
            y = (height - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
            painter.setCompositionMode(comp_mode)
        painter.end()

        return image

    def render_diff(self):
        comp_mode = QtGui.QPainter.CompositionMode_Difference
        return self.render_comp(comp_mode)

    def render_xor(self):
        comp_mode = QtGui.QPainter.CompositionMode_Xor
        return self.render_comp(comp_mode)

    def render_pixel_xor(self):
        comp_mode = QtGui.QPainter.RasterOp_SourceXorDestination
        return self.render_comp(comp_mode)


def create_image(width, height):
    size = QtCore.QSize(width, height)
    image = QtGui.QImage(size, QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    return image


def create_painter(image):
    painter = QtGui.QPainter(image)
    painter.fillRect(image.rect(), Qt.transparent)
    return painter


class Options(QtWidgets.QWidget):
    """Provide the options widget used by the editor

    Actions are registered on the parent widget.

    """

    # mode combobox indexes
    SIDE_BY_SIDE = 0
    DIFF = 1
    XOR = 2
    PIXEL_XOR = 3

    def __init__(self, parent):
        super(Options, self).__init__(parent)
        self.widget = parent
        self.ignore_space_at_eol = self.add_option(
            N_('Ignore changes in whitespace at EOL'))

        self.ignore_space_change = self.add_option(
            N_('Ignore changes in amount of whitespace'))

        self.ignore_all_space = self.add_option(
            N_('Ignore all whitespace'))

        self.function_context = self.add_option(
            N_('Show whole surrounding functions of changes'))

        self.show_line_numbers = self.add_option(
            N_('Show line numbers'))

        self.options = options = qtutils.create_action_button(
            tooltip=N_('Diff Options'), icon=icons.configure())
        qtutils.hide_button_menu_indicator(options)

        self.image_mode = qtutils.combo([
            N_('Side by side'),
            N_('Diff'),
            N_('XOR'),
            N_('Pixel XOR'),
        ])

        self.zoom_factors = (
            (N_('Zoom to Fit'), 0.0),
            (N_('25%'), 0.25),
            (N_('50%'), 0.5),
            (N_('100%'), 1.0),
            (N_('200%'), 2.0),
            (N_('400%'), 4.0),
            (N_('800%'), 8.0),
        )
        zoom_modes = [factor[0] for factor in self.zoom_factors]
        self.zoom_mode = qtutils.combo(zoom_modes, parent=self)

        self.menu = menu = qtutils.create_menu(N_('Diff Options'), options)
        options.setMenu(menu)

        menu.addAction(self.ignore_space_at_eol)
        menu.addAction(self.ignore_space_change)
        menu.addAction(self.ignore_all_space)
        menu.addAction(self.show_line_numbers)
        menu.addAction(self.function_context)

        layout = qtutils.hbox(
            defs.no_margin, defs.no_spacing,
            self.image_mode, defs.button_spacing, self.zoom_mode, options)
        self.setLayout(layout)

        self.image_mode.setFocusPolicy(Qt.NoFocus)
        self.zoom_mode.setFocusPolicy(Qt.NoFocus)
        self.options.setFocusPolicy(Qt.NoFocus)
        self.setFocusPolicy(Qt.NoFocus)

    def set_diff_type(self, diff_type):
        is_text = diff_type == 'text'
        is_image = diff_type == 'image'
        self.options.setVisible(is_text)
        self.image_mode.setVisible(is_image)
        self.zoom_mode.setVisible(is_image)

    def add_option(self, title):
        action = qtutils.add_action(self, title, self.update_options)
        action.setCheckable(True)
        return action

    def update_options(self):
        space_at_eol = get(self.ignore_space_at_eol)
        space_change = get(self.ignore_space_change)
        all_space = get(self.ignore_all_space)
        function_context = get(self.function_context)
        gitcmds.update_diff_overrides(
            space_at_eol, space_change, all_space, function_context)
        self.widget.update_options()


class DiffEditor(DiffTextEdit):

    up = Signal()
    down = Signal()
    options_changed = Signal()
    updated = Signal()
    diff_text_updated = Signal(object)

    def __init__(self, context, options, parent):
        DiffTextEdit.__init__(self, context, parent, numbers=True)
        self.context = context
        self.model = model = context.model
        self.selection_model = selection_model = context.selection

        # "Diff Options" tool menu
        self.options = options
        self.action_apply_selection = qtutils.add_action(
            self, 'Apply', self.apply_selection, hotkeys.STAGE_DIFF)

        self.action_revert_selection = qtutils.add_action(
            self, 'Revert', self.revert_selection, hotkeys.REVERT)
        self.action_revert_selection.setIcon(icons.undo())

        self.launch_editor = actions.launch_editor_at_line(
            context, self, *hotkeys.ACCEPT)
        self.launch_difftool = actions.launch_difftool(context, self)
        self.stage_or_unstage = actions.stage_or_unstage(context, self)

        # Emit up/down signals so that they can be routed by the main widget
        self.move_up = actions.move_up(self)
        self.move_down = actions.move_down(self)

        diff_text_updated = model.message_diff_text_updated
        model.add_observer(diff_text_updated, self.diff_text_updated.emit)
        self.diff_text_updated.connect(self.set_diff, type=Qt.QueuedConnection)

        selection_model.add_observer(
            selection_model.message_selection_changed, self.updated.emit)
        self.updated.connect(self.refresh, type=Qt.QueuedConnection)
        # Update the selection model when the cursor changes
        self.cursorPositionChanged.connect(self._update_line_number)

    def refresh(self):
        enabled = False
        s = self.selection_model.selection()
        model = self.model
        if s.modified and model.stageable():
            if s.modified[0] in model.submodules:
                pass
            elif s.modified[0] not in model.unstaged_deleted:
                enabled = True
        self.action_revert_selection.setEnabled(enabled)

    def enable_line_numbers(self, enabled):
        """Enable/disable the diff line number display"""
        self.numbers.setVisible(enabled)
        self.options.show_line_numbers.setChecked(enabled)

    def show_line_numbers(self):
        """Return True if we should show line numbers"""
        return get(self.options.show_line_numbers)

    def update_options(self):
        self.numbers.setVisible(self.show_line_numbers())
        self.options_changed.emit()

    # Qt overrides
    def contextMenuEvent(self, event):
        """Create the context menu for the diff display."""
        menu = qtutils.create_menu(N_('Actions'), self)
        context = self.context
        model = self.model
        s = self.selection_model.selection()
        filename = self.selection_model.filename()

        if model.stageable() or model.unstageable():
            if model.stageable():
                self.stage_or_unstage.setText(N_('Stage'))
            else:
                self.stage_or_unstage.setText(N_('Unstage'))
            menu.addAction(self.stage_or_unstage)

        if s.modified and model.stageable():
            item = s.modified[0]
            if item in model.submodules:
                path = core.abspath(item)
                action = menu.addAction(
                    icons.add(), cmds.Stage.name(),
                    cmds.run(cmds.Stage, context, s.modified))
                action.setShortcut(hotkeys.STAGE_SELECTION)
                menu.addAction(icons.cola(), N_('Launch git-cola'),
                               cmds.run(cmds.OpenRepo, context, path))
            elif item not in model.unstaged_deleted:
                if self.has_selection():
                    apply_text = N_('Stage Selected Lines')
                    revert_text = N_('Revert Selected Lines...')
                else:
                    apply_text = N_('Stage Diff Hunk')
                    revert_text = N_('Revert Diff Hunk...')

                self.action_apply_selection.setText(apply_text)
                self.action_apply_selection.setIcon(icons.add())

                self.action_revert_selection.setText(revert_text)

                menu.addAction(self.action_apply_selection)
                menu.addAction(self.action_revert_selection)

        if s.staged and model.unstageable():
            item = s.staged[0]
            if item in model.submodules:
                path = core.abspath(item)
                action = menu.addAction(
                    icons.remove(), cmds.Unstage.name(),
                    cmds.run(cmds.Unstage, context, s.staged))
                action.setShortcut(hotkeys.STAGE_SELECTION)
                menu.addAction(icons.cola(), N_('Launch git-cola'),
                               cmds.run(cmds.OpenRepo, context, path))
            elif item not in model.staged_deleted:
                if self.has_selection():
                    apply_text = N_('Unstage Selected Lines')
                else:
                    apply_text = N_('Unstage Diff Hunk')

                self.action_apply_selection.setText(apply_text)
                self.action_apply_selection.setIcon(icons.remove())
                menu.addAction(self.action_apply_selection)

        if model.stageable() or model.unstageable():
            # Do not show the "edit" action when the file does not exist.
            # Untracked files exist by definition.
            if filename and core.exists(filename):
                menu.addSeparator()
                menu.addAction(self.launch_editor)

            # Removed files can still be diffed.
            menu.addAction(self.launch_difftool)

        # Add the Previous/Next File actions, which improves discoverability
        # of their associated shortcuts
        menu.addSeparator()
        menu.addAction(self.move_up)
        menu.addAction(self.move_down)

        menu.addSeparator()
        action = menu.addAction(icons.copy(), N_('Copy'), self.copy)
        action.setShortcut(QtGui.QKeySequence.Copy)

        action = menu.addAction(icons.select_all(), N_('Select All'),
                                self.selectAll)
        action.setShortcut(QtGui.QKeySequence.SelectAll)
        menu.exec_(self.mapToGlobal(event.pos()))

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Intercept right-click to move the cursor to the current position.
            # setTextCursor() clears the selection so this is only done when
            # nothing is selected.
            if not self.has_selection():
                cursor = self.cursorForPosition(event.pos())
                self.setTextCursor(cursor)

        return super(DiffEditor, self).mousePressEvent(event)

    def setPlainText(self, text):
        """setPlainText(str) while retaining scrollbar positions"""
        model = self.model
        mode = model.mode
        highlight = mode not in (model.mode_none, model.mode_untracked)
        self.highlighter.set_enabled(highlight)

        scrollbar = self.verticalScrollBar()
        if scrollbar:
            scrollvalue = get(scrollbar)
        else:
            scrollvalue = None

        if text is None:
            return

        DiffTextEdit.setPlainText(self, text)

        if scrollbar and scrollvalue is not None:
            scrollbar.setValue(scrollvalue)

    def selected_lines(self):
        cursor = self.textCursor()
        selection_start = cursor.selectionStart()
        selection_end = max(selection_start, cursor.selectionEnd() - 1)

        first_line_idx = -1
        last_line_idx = -1
        line_idx = 0
        line_start = 0

        for line_idx, line in enumerate(get(self).splitlines()):
            line_end = line_start + len(line)
            if line_start <= selection_start <= line_end:
                first_line_idx = line_idx
            if line_start <= selection_end <= line_end:
                last_line_idx = line_idx
                break
            line_start = line_end + 1

        if first_line_idx == -1:
            first_line_idx = line_idx

        if last_line_idx == -1:
            last_line_idx = line_idx

        return first_line_idx, last_line_idx

    def apply_selection(self):
        model = self.model
        s = self.selection_model.single_selection()
        if model.stageable() and s.modified:
            self.process_diff_selection()
        elif model.unstageable():
            self.process_diff_selection(reverse=True)

    def revert_selection(self):
        """Destructively revert selected lines or hunk from a worktree file."""

        if self.has_selection():
            title = N_('Revert Selected Lines?')
            ok_text = N_('Revert Selected Lines')
        else:
            title = N_('Revert Diff Hunk?')
            ok_text = N_('Revert Diff Hunk')

        if not Interaction.confirm(
                title,
                N_('This operation drops uncommitted changes.\n'
                   'These changes cannot be recovered.'),
                N_('Revert the uncommitted changes?'),
                ok_text, default=True, icon=icons.undo()):
            return
        self.process_diff_selection(reverse=True, apply_to_worktree=True)

    def process_diff_selection(self, reverse=False, apply_to_worktree=False):
        """Implement un/staging of the selected line(s) or hunk."""
        if self.selection_model.is_empty():
            return
        context = self.context
        first_line_idx, last_line_idx = self.selected_lines()
        cmds.do(cmds.ApplyDiffSelection, context,
                first_line_idx, last_line_idx,
                self.has_selection(), reverse, apply_to_worktree)

    def _update_line_number(self):
        """Update the selection model when the cursor changes"""
        self.selection_model.line_number = self.numbers.current_line()


class DiffWidget(QtWidgets.QWidget):

    def __init__(self, context, notifier, parent, is_commit=False):
        QtWidgets.QWidget.__init__(self, parent)

        self.context = context
        self.oid = 'HEAD'

        author_font = QtGui.QFont(self.font())
        author_font.setPointSize(int(author_font.pointSize() * 1.1))

        summary_font = QtGui.QFont(author_font)
        summary_font.setWeight(QtGui.QFont.Bold)

        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                       QtWidgets.QSizePolicy.Minimum)

        self.gravatar_label = gravatar.GravatarLabel()

        self.author_label = TextLabel()
        self.author_label.setTextFormat(Qt.RichText)
        self.author_label.setFont(author_font)
        self.author_label.setSizePolicy(policy)
        self.author_label.setAlignment(Qt.AlignBottom)
        self.author_label.elide()

        self.date_label = TextLabel()
        self.date_label.setTextFormat(Qt.PlainText)
        self.date_label.setSizePolicy(policy)
        self.date_label.setAlignment(Qt.AlignTop)
        self.date_label.hide()

        self.summary_label = TextLabel()
        self.summary_label.setTextFormat(Qt.PlainText)
        self.summary_label.setFont(summary_font)
        self.summary_label.setSizePolicy(policy)
        self.summary_label.setAlignment(Qt.AlignTop)
        self.summary_label.elide()

        self.oid_label = TextLabel()
        self.oid_label.setTextFormat(Qt.PlainText)
        self.oid_label.setSizePolicy(policy)
        self.oid_label.setAlignment(Qt.AlignTop)
        self.oid_label.elide()

        self.diff = DiffTextEdit(
            context, self, is_commit=is_commit, whitespace=False)

        self.info_layout = qtutils.vbox(defs.no_margin, defs.no_spacing,
                                        self.author_label, self.date_label,
                                        self.summary_label, self.oid_label)

        self.logo_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                        self.gravatar_label, self.info_layout)
        self.logo_layout.setContentsMargins(defs.margin, 0, defs.margin, 0)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.logo_layout, self.diff)
        self.setLayout(self.main_layout)

        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)
        notifier.add_observer(FILES_SELECTED, self.files_selected)
        self.set_tabwidth(prefs.tabwidth(context))

    def set_tabwidth(self, width):
        self.diff.set_tabwidth(width)

    def set_diff_oid(self, oid, filename=None):
        context = self.context
        self.diff.save_scrollbar()
        self.diff.set_loading_message()
        task = DiffInfoTask(context, oid, filename, self)
        self.context.runtask.start(task, result=self.set_diff)

    def commits_selected(self, commits):
        if len(commits) != 1:
            return
        commit = commits[0]
        oid = self.oid = commit.oid
        email = commit.email or ''
        summary = commit.summary or ''
        author = commit.author or ''

        self.set_details(oid, author, email, '', summary)
        self.set_diff_oid(oid)

    def set_diff(self, diff):
        self.diff.set_diff(diff)

    def set_details(self, oid, author, email, date, summary):
        template_args = {
            'author': author,
            'email': email,
            'summary': summary
        }
        author_text = ("""%(author)s &lt;"""
                       """<a href="mailto:%(email)s">"""
                       """%(email)s</a>&gt;"""
                       % template_args)
        author_template = '%(author)s <%(email)s>' % template_args

        self.date_label.set_text(date)
        self.date_label.setVisible(bool(date))
        self.oid_label.set_text(oid)
        self.author_label.set_template(author_text, author_template)
        self.summary_label.set_text(summary)
        self.gravatar_label.set_email(email)

    def files_selected(self, filenames):
        if not filenames:
            return
        self.set_diff_oid(self.oid, filenames[0])


class TextLabel(QtWidgets.QLabel):

    def __init__(self, parent=None):
        QtWidgets.QLabel.__init__(self, parent)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse |
                                     Qt.LinksAccessibleByMouse)
        self._display = ''
        self._template = ''
        self._text = ''
        self._elide = False
        self._metrics = QtGui.QFontMetrics(self.font())
        self.setOpenExternalLinks(True)

    def elide(self):
        self._elide = True

    def set_text(self, text):
        self.set_template(text, text)

    def set_template(self, text, template):
        self._display = text
        self._text = text
        self._template = template
        self.update_text(self.width())
        self.setText(self._display)

    def update_text(self, width):
        self._display = self._text
        if not self._elide:
            return
        text = self._metrics.elidedText(self._template,
                                        Qt.ElideRight, width-2)
        if text != self._template:
            self._display = text

    # Qt overrides
    def setFont(self, font):
        self._metrics = QtGui.QFontMetrics(font)
        QtWidgets.QLabel.setFont(self, font)

    def resizeEvent(self, event):
        if self._elide:
            self.update_text(event.size().width())
            block = self.blockSignals(True)
            self.setText(self._display)
            self.blockSignals(block)
        QtWidgets.QLabel.resizeEvent(self, event)


class DiffInfoTask(qtutils.Task):

    def __init__(self, context, oid, filename, parent):
        qtutils.Task.__init__(self, parent)
        self.context = context
        self.oid = oid
        self.filename = filename

    def task(self):
        context = self.context
        oid = self.oid
        return gitcmds.diff_info(context, oid, filename=self.filename)
