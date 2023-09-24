from functools import partial
import os
import re

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..i18n import N_
from ..editpatch import edit_patch
from ..interaction import Interaction
from ..models import main
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
from .text import TextSearchWidget
from . import defs
from . import patch as patch_mod
from . import imageview


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
    DIFF_HUNK_HEADER_RGX = re.compile(
        r'(?:@@ -[0-9,]+ \+[0-9,]+ @@)|(?:@@@ (?:-[0-9,]+ ){2}\+[0-9,]+ @@@)'
    )
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

        dark = palette.color(QPalette.Base).lightnessF() < 0.5

        self.color_text = qtutils.rgb_triple(cfg.color('text', '030303'))
        self.color_add = qtutils.rgb_triple(
            cfg.color('add', '77aa77' if dark else 'd2ffe4')
        )
        self.color_remove = qtutils.rgb_triple(
            cfg.color('remove', 'aa7777' if dark else 'fee0e4')
        )
        self.color_header = qtutils.rgb_triple(cfg.color('header', header))

        self.diff_header_fmt = qtutils.make_format(foreground=self.color_header)
        self.bold_diff_header_fmt = qtutils.make_format(
            foreground=self.color_header, bold=True
        )

        self.diff_add_fmt = qtutils.make_format(
            foreground=self.color_text, background=self.color_add
        )
        self.diff_remove_fmt = qtutils.make_format(
            foreground=self.color_text, background=self.color_remove
        )
        self.bad_whitespace_fmt = qtutils.make_format(background=Qt.red)
        self.setCurrentBlockState(self.INITIAL_STATE)

    def set_enabled(self, enabled):
        self.enabled = enabled

    def highlightBlock(self, text):
        """Highlight the current text block"""
        if not self.enabled or not text:
            return
        formats = []
        state = self.get_next_state(text)
        if state == self.DIFFSTAT_STATE:
            state, formats = self.get_formats_for_diffstat(state, text)
        elif state == self.DIFF_FILE_HEADER_STATE:
            state, formats = self.get_formats_for_diff_header(state, text)
        elif state == self.DIFF_STATE:
            state, formats = self.get_formats_for_diff_text(state, text)

        for start, end, fmt in formats:
            self.setFormat(start, end, fmt)

        self.setCurrentBlockState(state)

    def get_next_state(self, text):
        """Transition to the next state based on the input text"""
        state = self.previousBlockState()
        if state == DiffSyntaxHighlighter.INITIAL_STATE:
            if text.startswith('Submodule '):
                state = DiffSyntaxHighlighter.SUBMODULE_STATE
            elif text.startswith('diff --git '):
                state = DiffSyntaxHighlighter.DIFFSTAT_STATE
            elif self.is_commit:
                state = DiffSyntaxHighlighter.DEFAULT_STATE
            else:
                state = DiffSyntaxHighlighter.DIFFSTAT_STATE

        return state

    def get_formats_for_diffstat(self, state, text):
        """Returns (state, [(start, end, fmt), ...]) for highlighting diffstat text"""
        formats = []
        if self.DIFF_FILE_HEADER_START_RGX.match(text):
            state = self.DIFF_FILE_HEADER_STATE
            end = len(text)
            fmt = self.diff_header_fmt
            formats.append((0, end, fmt))
        elif self.DIFF_HUNK_HEADER_RGX.match(text):
            state = self.DIFF_STATE
            end = len(text)
            fmt = self.bold_diff_header_fmt
            formats.append((0, end, fmt))
        elif '|' in text:
            offset = text.index('|')
            formats.append((0, offset, self.bold_diff_header_fmt))
            formats.append((offset, len(text) - offset, self.diff_header_fmt))
        else:
            formats.append((0, len(text), self.diff_header_fmt))

        return state, formats

    def get_formats_for_diff_header(self, state, text):
        """Returns (state, [(start, end, fmt), ...]) for highlighting diff headers"""
        formats = []
        if self.DIFF_HUNK_HEADER_RGX.match(text):
            state = self.DIFF_STATE
            formats.append((0, len(text), self.bold_diff_header_fmt))
        else:
            formats.append((0, len(text), self.diff_header_fmt))

        return state, formats

    def get_formats_for_diff_text(self, state, text):
        """Return (state, [(start, end fmt), ...]) for highlighting diff text"""
        formats = []

        if self.DIFF_FILE_HEADER_START_RGX.match(text):
            state = self.DIFF_FILE_HEADER_STATE
            formats.append((0, len(text), self.diff_header_fmt))

        elif self.DIFF_HUNK_HEADER_RGX.match(text):
            formats.append((0, len(text), self.bold_diff_header_fmt))

        elif text.startswith('-'):
            if text == '-- ':
                state = self.END_STATE
            else:
                formats.append((0, len(text), self.diff_remove_fmt))

        elif text.startswith('+'):
            formats.append((0, len(text), self.diff_add_fmt))
            if self.whitespace:
                match = self.BAD_WHITESPACE_RGX.search(text)
                if match is not None:
                    start = match.start()
                    formats.append((start, len(text) - start, self.bad_whitespace_fmt))

        return state, formats


# pylint: disable=too-many-ancestors
class DiffTextEdit(VimHintedPlainTextEdit):
    """A textedit for interacting with diff text"""

    def __init__(
        self, context, parent, is_commit=False, whitespace=True, numbers=False
    ):
        VimHintedPlainTextEdit.__init__(self, context, '', parent=parent)
        # Diff/patch syntax highlighter
        self.highlighter = DiffSyntaxHighlighter(
            context, self.document(), is_commit=is_commit, whitespace=whitespace
        )
        if numbers:
            self.numbers = DiffLineNumbers(context, self)
            self.numbers.hide()
        else:
            self.numbers = None
        self.scrollvalue = None

        self.copy_diff_action = qtutils.add_action(
            self,
            N_('Copy Diff'),
            self.copy_diff,
            hotkeys.COPY_DIFF,
        )
        self.copy_diff_action.setIcon(icons.copy())
        self.copy_diff_action.setEnabled(False)
        self.menu_actions.append(self.copy_diff_action)

        # pylint: disable=no-member
        self.cursorPositionChanged.connect(self._cursor_changed)
        self.selectionChanged.connect(self._selection_changed)

    def setFont(self, font):
        """Override setFont() so that we can use a custom "block" cursor"""
        super().setFont(font)
        if prefs.block_cursor(self.context):
            metrics = QtGui.QFontMetrics(font)
            width = metrics.width('M')
            self.setCursorWidth(width)

    def _cursor_changed(self):
        """Update the line number display when the cursor changes"""
        line_number = max(0, self.textCursor().blockNumber())
        if self.numbers is not None:
            self.numbers.set_highlighted(line_number)

    def _selection_changed(self):
        """Respond to selection changes"""
        selected = bool(self.selected_text())
        self.copy_diff_action.setEnabled(selected)

    def resizeEvent(self, event):
        super().resizeEvent(event)
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
        """Add a pending loading message in the diff view"""
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

    def selected_diff_stripped(self):
        """Return the selected diff stripped of any diff characters"""
        sep, selection = self.selected_text_lines()
        return sep.join(_strip_diff(line) for line in selection)

    def copy_diff(self):
        """Copy the selected diff text stripped of any diff prefix characters"""
        text = self.selected_diff_stripped()
        qtutils.set_clipboard(text)

    def selected_lines(self):
        """Return selected lines"""
        cursor = self.textCursor()
        selection_start = cursor.selectionStart()
        selection_end = max(selection_start, cursor.selectionEnd() - 1)

        first_line_idx = -1
        last_line_idx = -1
        line_idx = 0
        line_start = 0

        for line_idx, line in enumerate(get(self, default='').splitlines()):
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

    def selected_text_lines(self):
        """Return selected lines and the CRLF / LF separator"""
        first_line_idx, last_line_idx = self.selected_lines()
        text = get(self, default='')
        sep = _get_sep(text)
        lines = []
        for line_idx, line in enumerate(text.split(sep)):
            if first_line_idx <= line_idx <= last_line_idx:
                lines.append(line)
        return sep, lines


def _get_sep(text):
    """Return either CRLF or LF based on the content"""
    if '\r\n' in text:
        sep = '\r\n'
    else:
        sep = '\n'
    return sep


def _strip_diff(value):
    """Remove +/-/<space> from a selection"""
    if value.startswith(('+', '-', ' ')):
        return value[1:]
    return value


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
        self._highlight.setAlphaF(0.3)
        self._highlight_text = palette.color(QPalette.HighlightedText)
        self._window = palette.color(QPalette.Window)
        self._disabled = palette.color(QPalette.Disabled, QPalette.Text)

    def set_diff(self, diff):
        self.lines = self.parser.parse(diff)
        self.formatter.set_digits(self.parser.digits())

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

        digits = parser.digits() * columns

        return defs.margin + (self._char_width * (digits + extra))

    def set_highlighted(self, line_number):
        """Set the line to highlight"""
        self.highlight_line = line_number

    def current_line(self):
        lines = self.lines
        if lines and self.highlight_line >= 0:
            # Find the next valid line
            for i in range(self.highlight_line, len(lines)):
                # take the "new" line number: last value in tuple
                line_number = lines[i][-1]
                if line_number > 0:
                    return line_number

            # Find the previous valid line
            for i in range(self.highlight_line - 1, -1, -1):
                # take the "new" line number: last value in tuple
                if i < len(lines):
                    line_number = lines[i][-1]
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
        text_width = width - (defs.margin * 2)
        text_flags = Qt.AlignRight | Qt.AlignVCenter
        event_rect_bottom = event.rect().bottom()

        highlight_line = self.highlight_line
        highlight = self._highlight
        highlight_text = self._highlight_text
        disabled = self._disabled

        fmt = self.formatter
        lines = self.lines
        num_lines = len(lines)

        while block.isValid():
            block_number = block.blockNumber()
            if block_number >= num_lines:
                break
            block_geom = editor.blockBoundingGeometry(block)
            rect = block_geom.translated(content_offset).toRect()
            if not block.isVisible() or rect.top() >= event_rect_bottom:
                break

            if block_number == highlight_line:
                painter.fillRect(rect.x(), rect.y(), width, rect.height(), highlight)
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

            painter.drawText(
                rect.x(),
                rect.y(),
                text_width,
                rect.height(),
                text_flags,
                text,
            )

            block = block.next()


class Viewer(QtWidgets.QFrame):
    """Text and image diff viewers"""

    INDEX_TEXT = 0
    INDEX_IMAGE = 1

    def __init__(self, context, parent=None):
        super().__init__(parent)

        self.context = context
        self.model = model = context.model
        self.images = []
        self.pixmaps = []
        self.options = options = Options(self)
        self.text = DiffEditor(context, options, self)
        self.image = imageview.ImageView(parent=self)
        self.image.setFocusPolicy(Qt.NoFocus)
        self.search_widget = TextSearchWidget(self.text, self)
        self.search_widget.hide()
        self._drag_has_patches = False

        self.setAcceptDrops(True)
        self.setFocusProxy(self.text)

        stack = self.stack = QtWidgets.QStackedWidget(self)
        stack.addWidget(self.text)
        stack.addWidget(self.image)

        self.main_layout = qtutils.vbox(
            defs.no_margin,
            defs.no_spacing,
            self.stack,
            self.search_widget,
        )
        self.setLayout(self.main_layout)

        # Observe images
        model.images_changed.connect(self.set_images, type=Qt.QueuedConnection)

        # Observe the diff type
        model.diff_type_changed.connect(self.set_diff_type, type=Qt.QueuedConnection)

        # Observe the file type
        model.file_type_changed.connect(self.set_file_type, type=Qt.QueuedConnection)

        # Observe the image mode combo box
        options.image_mode.currentIndexChanged.connect(lambda _: self.render())
        options.zoom_mode.currentIndexChanged.connect(lambda _: self.render())

        self.search_action = qtutils.add_action(
            self,
            N_('Search in Diff'),
            self.show_search_diff,
            hotkeys.SEARCH,
        )

    def dragEnterEvent(self, event):
        """Accepts drops if the mimedata contains patches"""
        super().dragEnterEvent(event)
        patches = patch_mod.get_patches_from_mimedata(event.mimeData())
        if patches:
            event.acceptProposedAction()
            self._drag_has_patches = True

    def dragLeaveEvent(self, event):
        """End the drag+drop interaction"""
        super().dragLeaveEvent(event)
        if self._drag_has_patches:
            event.accept()
        else:
            event.ignore()
        self._drag_has_patches = False

    def dropEvent(self, event):
        """Apply patches when dropped onto the widget"""
        if not self._drag_has_patches:
            event.ignore()
            return
        event.setDropAction(Qt.CopyAction)
        super().dropEvent(event)
        self._drag_has_patches = False

        patches = patch_mod.get_patches_from_mimedata(event.mimeData())
        if patches:
            patch_mod.apply_patches(self.context, patches=patches)

        event.accept()  # must be called after dropEvent()

    def show_search_diff(self):
        """Show a dialog for searching diffs"""
        # The diff search is only active in text mode.
        if self.stack.currentIndex() != self.INDEX_TEXT:
            return
        if not self.search_widget.isVisible():
            self.search_widget.show()
        self.search_widget.setFocus(True)

    def export_state(self, state):
        state['show_diff_line_numbers'] = self.options.show_line_numbers.isChecked()
        state['image_diff_mode'] = self.options.image_mode.currentIndex()
        state['image_zoom_mode'] = self.options.zoom_mode.currentIndex()
        state['word_wrap'] = self.options.enable_word_wrapping.isChecked()
        return state

    def apply_state(self, state):
        diff_numbers = bool(state.get('show_diff_line_numbers', False))
        self.set_line_numbers(diff_numbers, update=True)

        image_mode = utils.asint(state.get('image_diff_mode', 0))
        self.options.image_mode.set_index(image_mode)

        zoom_mode = utils.asint(state.get('image_zoom_mode', 0))
        self.options.zoom_mode.set_index(zoom_mode)

        word_wrap = bool(state.get('word_wrap', True))
        self.set_word_wrapping(word_wrap, update=True)
        return True

    def set_diff_type(self, diff_type):
        """Manage the image and text diff views when selection changes"""
        # The "diff type" is whether the diff viewer is displaying an image.
        self.options.set_diff_type(diff_type)
        if diff_type == main.Types.IMAGE:
            self.stack.setCurrentWidget(self.image)
            self.search_widget.hide()
            self.render()
        else:
            self.stack.setCurrentWidget(self.text)

    def set_file_type(self, file_type):
        """Manage the diff options when the file type changes"""
        # The "file type" is whether the file itself is an image.
        self.options.set_file_type(file_type)

    def update_options(self):
        """Emit a signal indicating that options have changed"""
        self.text.update_options()

    def set_line_numbers(self, enabled, update=False):
        """Enable/disable line numbers in the text widget"""
        self.text.set_line_numbers(enabled, update=update)

    def set_word_wrapping(self, enabled, update=False):
        """Enable/disable word wrapping in the text widget"""
        self.text.set_word_wrapping(enabled, update=update)

    def reset(self):
        self.image.pixmap = QtGui.QPixmap()
        self.cleanup()

    def cleanup(self):
        for image, unlink in self.images:
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
        width = sum(pixmap.width() for pixmap in pixmaps)
        height = max(pixmap.height() for pixmap in pixmaps)
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

        width = max(pixmap.width() for pixmap in pixmaps)
        height = max(pixmap.height() for pixmap in pixmaps)
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
        super().__init__(parent)
        # Create widgets
        self.widget = parent
        self.ignore_space_at_eol = self.add_option(
            N_('Ignore changes in whitespace at EOL')
        )

        self.ignore_space_change = self.add_option(
            N_('Ignore changes in amount of whitespace')
        )

        self.ignore_all_space = self.add_option(N_('Ignore all whitespace'))

        self.function_context = self.add_option(
            N_('Show whole surrounding functions of changes')
        )

        self.show_line_numbers = qtutils.add_action_bool(
            self, N_('Show line numbers'), self.set_line_numbers, True
        )
        self.enable_word_wrapping = qtutils.add_action_bool(
            self, N_('Enable word wrapping'), self.set_word_wrapping, True
        )

        self.options = qtutils.create_action_button(
            tooltip=N_('Diff Options'), icon=icons.configure()
        )

        self.toggle_image_diff = qtutils.create_action_button(
            tooltip=N_('Toggle image diff'), icon=icons.visualize()
        )
        self.toggle_image_diff.hide()

        self.image_mode = qtutils.combo(
            [N_('Side by side'), N_('Diff'), N_('XOR'), N_('Pixel XOR')]
        )

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

        self.menu = menu = qtutils.create_menu(N_('Diff Options'), self.options)
        self.options.setMenu(menu)
        menu.addAction(self.ignore_space_at_eol)
        menu.addAction(self.ignore_space_change)
        menu.addAction(self.ignore_all_space)
        menu.addSeparator()
        menu.addAction(self.function_context)
        menu.addAction(self.show_line_numbers)
        menu.addSeparator()
        menu.addAction(self.enable_word_wrapping)

        # Layouts
        layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.image_mode,
            self.zoom_mode,
            self.options,
            self.toggle_image_diff,
        )
        self.setLayout(layout)

        # Policies
        self.image_mode.setFocusPolicy(Qt.NoFocus)
        self.zoom_mode.setFocusPolicy(Qt.NoFocus)
        self.options.setFocusPolicy(Qt.NoFocus)
        self.toggle_image_diff.setFocusPolicy(Qt.NoFocus)
        self.setFocusPolicy(Qt.NoFocus)

    def set_file_type(self, file_type):
        """Set whether we are viewing an image file type"""
        is_image = file_type == main.Types.IMAGE
        self.toggle_image_diff.setVisible(is_image)

    def set_diff_type(self, diff_type):
        """Toggle between image and text diffs"""
        is_text = diff_type == main.Types.TEXT
        is_image = diff_type == main.Types.IMAGE
        self.options.setVisible(is_text)
        self.image_mode.setVisible(is_image)
        self.zoom_mode.setVisible(is_image)
        if is_image:
            self.toggle_image_diff.setIcon(icons.diff())
        else:
            self.toggle_image_diff.setIcon(icons.visualize())

    def add_option(self, title):
        """Add a diff option which calls update_options() on change"""
        action = qtutils.add_action(self, title, self.update_options)
        action.setCheckable(True)
        return action

    def update_options(self):
        """Update diff options in response to UI events"""
        space_at_eol = get(self.ignore_space_at_eol)
        space_change = get(self.ignore_space_change)
        all_space = get(self.ignore_all_space)
        function_context = get(self.function_context)
        gitcmds.update_diff_overrides(
            space_at_eol, space_change, all_space, function_context
        )
        self.widget.update_options()

    def set_line_numbers(self, value):
        """Enable / disable line numbers"""
        self.widget.set_line_numbers(value, update=False)

    def set_word_wrapping(self, value):
        """Respond to Qt action callbacks"""
        self.widget.set_word_wrapping(value, update=False)

    def hide_advanced_options(self):
        """Hide advanced options that are not applicable to the DiffWidget"""
        self.show_line_numbers.setVisible(False)
        self.ignore_space_at_eol.setVisible(False)
        self.ignore_space_change.setVisible(False)
        self.ignore_all_space.setVisible(False)
        self.function_context.setVisible(False)


# pylint: disable=too-many-ancestors
class DiffEditor(DiffTextEdit):
    up = Signal()
    down = Signal()
    options_changed = Signal()

    def __init__(self, context, options, parent):
        DiffTextEdit.__init__(self, context, parent, numbers=True)
        self.context = context
        self.model = model = context.model
        self.selection_model = selection_model = context.selection

        # "Diff Options" tool menu
        self.options = options

        self.action_apply_selection = qtutils.add_action(
            self,
            'Apply',
            self.apply_selection,
            hotkeys.STAGE_DIFF,
            hotkeys.STAGE_DIFF_ALT,
        )

        self.action_revert_selection = qtutils.add_action(
            self, 'Revert', self.revert_selection, hotkeys.REVERT, hotkeys.REVERT_ALT
        )
        self.action_revert_selection.setIcon(icons.undo())

        self.action_edit_and_apply_selection = qtutils.add_action(
            self,
            'Edit and Apply',
            partial(self.apply_selection, edit=True),
            hotkeys.EDIT_AND_STAGE_DIFF,
        )

        self.action_edit_and_revert_selection = qtutils.add_action(
            self,
            'Edit and Revert',
            partial(self.revert_selection, edit=True),
            hotkeys.EDIT_AND_REVERT,
        )
        self.action_edit_and_revert_selection.setIcon(icons.undo())
        self.launch_editor = actions.launch_editor_at_line(
            context, self, hotkeys.EDIT_SHORT, *hotkeys.ACCEPT
        )
        self.launch_difftool = actions.launch_difftool(context, self)
        self.stage_or_unstage = actions.stage_or_unstage(context, self)

        # Emit up/down signals so that they can be routed by the main widget
        self.move_up = actions.move_up(self)
        self.move_down = actions.move_down(self)

        model.diff_text_updated.connect(self.set_diff, type=Qt.QueuedConnection)

        selection_model.selection_changed.connect(
            self.refresh, type=Qt.QueuedConnection
        )
        # Update the selection model when the cursor changes
        self.cursorPositionChanged.connect(self._update_line_number)

        qtutils.connect_button(options.toggle_image_diff, self.toggle_diff_type)

    def toggle_diff_type(self):
        cmds.do(cmds.ToggleDiffType, self.context)

    def refresh(self):
        enabled = False
        s = self.selection_model.selection()
        model = self.model
        if model.is_partially_stageable():
            item = s.modified[0] if s.modified else None
            if item in model.submodules:
                pass
            elif item not in model.unstaged_deleted:
                enabled = True
        self.action_revert_selection.setEnabled(enabled)

    def set_line_numbers(self, enabled, update=False):
        """Enable/disable the diff line number display"""
        self.numbers.setVisible(enabled)
        if update:
            with qtutils.BlockSignals(self.options.show_line_numbers):
                self.options.show_line_numbers.setChecked(enabled)
        # Refresh the display. Not doing this results in the display not
        # correctly displaying the line numbers widget until the text scrolls.
        self.set_value(self.value())

    def update_options(self):
        self.options_changed.emit()

    def create_context_menu(self, event_pos):
        """Override create_context_menu() to display a completely custom menu"""
        menu = super().create_context_menu(event_pos)
        context = self.context
        model = self.model
        s = self.selection_model.selection()
        filename = self.selection_model.filename()

        # These menu actions will be inserted at the start of the widget.
        current_actions = menu.actions()
        menu_actions = []
        add_action = menu_actions.append
        edit_actions_added = False

        if model.is_stageable() or model.is_unstageable():
            if (model.is_amend_mode() and s.staged) or not self.model.is_stageable():
                self.stage_or_unstage.setText(N_('Unstage'))
                self.stage_or_unstage.setIcon(icons.remove())
            else:
                self.stage_or_unstage.setText(N_('Stage'))
                self.stage_or_unstage.setIcon(icons.add())
            add_action(self.stage_or_unstage)

        if s.staged and model.is_unstageable():
            item = s.staged[0]
            if item not in model.submodules and item not in model.staged_deleted:
                if self.has_selection():
                    apply_text = N_('Unstage Selected Lines')
                else:
                    apply_text = N_('Unstage Diff Hunk')
                self.action_apply_selection.setText(apply_text)
                self.action_apply_selection.setIcon(icons.remove())
                add_action(self.action_apply_selection)

        if model.is_partially_stageable():
            item = s.modified[0] if s.modified else None
            if item in model.submodules:
                path = core.abspath(item)
                action = qtutils.add_action_with_icon(
                    menu,
                    icons.add(),
                    cmds.Stage.name(),
                    cmds.run(cmds.Stage, context, s.modified),
                    hotkeys.STAGE_SELECTION,
                )
                add_action(action)

                action = qtutils.add_action_with_icon(
                    menu,
                    icons.cola(),
                    N_('Launch git-cola'),
                    cmds.run(cmds.OpenRepo, context, path),
                )
                add_action(action)
            elif item and item not in model.unstaged_deleted:
                if self.has_selection():
                    apply_text = N_('Stage Selected Lines')
                    edit_and_apply_text = N_('Edit Selected Lines to Stage...')
                    revert_text = N_('Revert Selected Lines...')
                    edit_and_revert_text = N_('Edit Selected Lines to Revert...')
                else:
                    apply_text = N_('Stage Diff Hunk')
                    edit_and_apply_text = N_('Edit Diff Hunk to Stage...')
                    revert_text = N_('Revert Diff Hunk...')
                    edit_and_revert_text = N_('Edit Diff Hunk to Revert...')

                self.action_apply_selection.setText(apply_text)
                self.action_apply_selection.setIcon(icons.add())
                add_action(self.action_apply_selection)

                self.action_revert_selection.setText(revert_text)
                add_action(self.action_revert_selection)

                # Do not show the "edit" action when the file does not exist.
                add_action(qtutils.menu_separator(menu))
                if filename and core.exists(filename):
                    add_action(self.launch_editor)
                # Removed files can still be diffed.
                add_action(self.launch_difftool)
                edit_actions_added = True

                add_action(qtutils.menu_separator(menu))
                self.action_edit_and_apply_selection.setText(edit_and_apply_text)
                self.action_edit_and_apply_selection.setIcon(icons.add())
                add_action(self.action_edit_and_apply_selection)

                self.action_edit_and_revert_selection.setText(edit_and_revert_text)
                add_action(self.action_edit_and_revert_selection)

        if s.staged and model.is_unstageable():
            item = s.staged[0]
            if item in model.submodules:
                path = core.abspath(item)
                action = qtutils.add_action_with_icon(
                    menu,
                    icons.remove(),
                    cmds.Unstage.name(),
                    cmds.run(cmds.Unstage, context, s.staged),
                    hotkeys.STAGE_SELECTION,
                )
                add_action(action)

                qtutils.add_action_with_icon(
                    menu,
                    icons.cola(),
                    N_('Launch git-cola'),
                    cmds.run(cmds.OpenRepo, context, path),
                )
                add_action(action)

            elif item not in model.staged_deleted:
                # Do not show the "edit" action when the file does not exist.
                add_action(qtutils.menu_separator(menu))
                if filename and core.exists(filename):
                    add_action(self.launch_editor)
                # Removed files can still be diffed.
                add_action(self.launch_difftool)
                add_action(qtutils.menu_separator(menu))
                edit_actions_added = True

                if self.has_selection():
                    edit_and_apply_text = N_('Edit Selected Lines to Unstage...')
                else:
                    edit_and_apply_text = N_('Edit Diff Hunk to Unstage...')
                self.action_edit_and_apply_selection.setText(edit_and_apply_text)
                self.action_edit_and_apply_selection.setIcon(icons.remove())
                add_action(self.action_edit_and_apply_selection)

        if not edit_actions_added and (model.is_stageable() or model.is_unstageable()):
            add_action(qtutils.menu_separator(menu))
            # Do not show the "edit" action when the file does not exist.
            # Untracked files exist by definition.
            if filename and core.exists(filename):
                add_action(self.launch_editor)

            # Removed files can still be diffed.
            add_action(self.launch_difftool)

        add_action(qtutils.menu_separator(menu))
        _add_patch_actions(self, self.context, menu)

        # Add the Previous/Next File actions, which improves discoverability
        # of their associated shortcuts
        add_action(qtutils.menu_separator(menu))
        add_action(self.move_up)
        add_action(self.move_down)
        add_action(qtutils.menu_separator(menu))

        if current_actions:
            first_action = current_actions[0]
        else:
            first_action = None
        menu.insertActions(first_action, menu_actions)

        return menu

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Intercept right-click to move the cursor to the current position.
            # setTextCursor() clears the selection so this is only done when
            # nothing is selected.
            if not self.has_selection():
                cursor = self.cursorForPosition(event.pos())
                self.setTextCursor(cursor)

        return super().mousePressEvent(event)

    def setPlainText(self, text):
        """setPlainText(str) while retaining scrollbar positions"""
        model = self.model
        mode = model.mode
        highlight = mode not in (
            model.mode_none,
            model.mode_display,
            model.mode_untracked,
        )
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

    def apply_selection(self, *, edit=False):
        model = self.model
        s = self.selection_model.single_selection()
        if model.is_partially_stageable() and (s.modified or s.untracked):
            self.process_diff_selection(edit=edit)
        elif model.is_unstageable():
            self.process_diff_selection(reverse=True, edit=edit)

    def revert_selection(self, *, edit=False):
        """Destructively revert selected lines or hunk from a worktree file."""

        if not edit:
            if self.has_selection():
                title = N_('Revert Selected Lines?')
                ok_text = N_('Revert Selected Lines')
            else:
                title = N_('Revert Diff Hunk?')
                ok_text = N_('Revert Diff Hunk')

            if not Interaction.confirm(
                title,
                N_(
                    'This operation drops uncommitted changes.\n'
                    'These changes cannot be recovered.'
                ),
                N_('Revert the uncommitted changes?'),
                ok_text,
                default=True,
                icon=icons.undo(),
            ):
                return
        self.process_diff_selection(reverse=True, apply_to_worktree=True, edit=edit)

    def extract_patch(self, reverse=False):
        first_line_idx, last_line_idx = self.selected_lines()
        patch = diffparse.Patch.parse(self.model.filename, self.model.diff_text)
        if self.has_selection():
            return patch.extract_subset(first_line_idx, last_line_idx, reverse=reverse)
        return patch.extract_hunk(first_line_idx, reverse=reverse)

    def patch_encoding(self):
        if isinstance(self.model.diff_text, core.UStr):
            # original encoding must prevail
            return self.model.diff_text.encoding
        return self.context.cfg.file_encoding(self.model.filename)

    def process_diff_selection(
        self, reverse=False, apply_to_worktree=False, edit=False
    ):
        """Implement un/staging of the selected line(s) or hunk."""
        if self.selection_model.is_empty():
            return
        patch = self.extract_patch(reverse)
        if not patch.has_changes():
            return
        patch_encoding = self.patch_encoding()

        if edit:
            patch = edit_patch(
                patch,
                patch_encoding,
                self.context,
                reverse=reverse,
                apply_to_worktree=apply_to_worktree,
            )
            if not patch.has_changes():
                return

        cmds.do(
            cmds.ApplyPatch,
            self.context,
            patch,
            patch_encoding,
            apply_to_worktree,
        )

    def _update_line_number(self):
        """Update the selection model when the cursor changes"""
        self.selection_model.line_number = self.numbers.current_line()


def _add_patch_actions(widget, context, menu):
    """Add actions for manipulating patch files"""
    patches_menu = menu.addMenu(N_('Patches'))
    patches_menu.setIcon(icons.diff())
    export_action = qtutils.add_action(
        patches_menu,
        N_('Export Patch'),
        lambda: _export_patch(widget, context),
    )
    export_action.setIcon(icons.save())
    patches_menu.addAction(export_action)

    # Build the "Append Patch" menu dynamically.
    append_menu = patches_menu.addMenu(N_('Append Patch'))
    append_menu.setIcon(icons.add())
    append_menu.aboutToShow.connect(
        lambda: _build_patch_append_menu(widget, context, append_menu)
    )


def _build_patch_append_menu(widget, context, menu):
    """Build the "Append Patch" submenu"""
    # Build the menu when first displayed only. This initial check avoids
    # re-populating the menu with duplicate actions.
    menu_actions = menu.actions()
    if menu_actions:
        return

    choose_patch_action = qtutils.add_action(
        menu,
        N_('Choose Patch...'),
        lambda: _export_patch(widget, context, append=True),
    )
    choose_patch_action.setIcon(icons.diff())
    menu.addAction(choose_patch_action)

    subdir_menus = {}
    path = prefs.patches_directory(context)
    patches = patch_mod.get_patches_from_dir(path)
    for patch in patches:
        relpath = os.path.relpath(patch, start=path)
        sub_menu = _add_patch_subdirs(menu, subdir_menus, relpath)
        patch_basename = os.path.basename(relpath)
        append_action = qtutils.add_action(
            sub_menu,
            patch_basename,
            lambda patch_file=patch: _append_patch(widget, patch_file),
        )
        append_action.setIcon(icons.save())
        sub_menu.addAction(append_action)


def _add_patch_subdirs(menu, subdir_menus, relpath):
    """Build menu leading up to the patch"""
    # If the path contains no directory separators then add it to the
    # root of the menu.
    if os.sep not in relpath:
        return menu

    # Loop over each directory component and build a menu if it doesn't already exist.
    components = []
    for dirname in os.path.dirname(relpath).split(os.sep):
        components.append(dirname)
        current_dir = os.sep.join(components)
        try:
            menu = subdir_menus[current_dir]
        except KeyError:
            menu = subdir_menus[current_dir] = menu.addMenu(dirname)
            menu.setIcon(icons.folder())

    return menu


def _export_patch(diff_editor, context, append=False):
    """Export the selected diff to a patch file"""
    if diff_editor.selection_model.is_empty():
        return
    patch = diff_editor.extract_patch(reverse=False)
    if not patch.has_changes():
        return
    directory = prefs.patches_directory(context)
    if append:
        filename = qtutils.existing_file(directory, title=N_('Append Patch...'))
    else:
        default_filename = os.path.join(directory, 'diff.patch')
        filename = qtutils.save_as(default_filename)
    if not filename:
        return
    _write_patch_to_file(diff_editor, patch, filename, append=append)


def _append_patch(diff_editor, filename):
    """Append diffs to the specified patch file"""
    if diff_editor.selection_model.is_empty():
        return
    patch = diff_editor.extract_patch(reverse=False)
    if not patch.has_changes():
        return
    _write_patch_to_file(diff_editor, patch, filename, append=True)


def _write_patch_to_file(diff_editor, patch, filename, append=False):
    """Write diffs from the Diff Editor to the specified patch file"""
    encoding = diff_editor.patch_encoding()
    content = patch.as_text()
    try:
        core.write(filename, content, encoding=encoding, append=append)
    except OSError as exc:
        _, details = utils.format_exception(exc)
        title = N_('Error writing patch')
        msg = N_('Unable to write patch to "%s". Check permissions?' % filename)
        Interaction.critical(title, message=msg, details=details)
        return
    Interaction.log('Patch written to "%s"' % filename)


class DiffWidget(QtWidgets.QWidget):
    """Display commit metadata and text diffs"""

    def __init__(self, context, parent, is_commit=False, options=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.context = context
        self.oid = 'HEAD'
        self.oid_start = None
        self.oid_end = None
        self.options = options

        author_font = QtGui.QFont(self.font())
        author_font.setPointSize(int(author_font.pointSize() * 1.1))

        summary_font = QtGui.QFont(author_font)
        summary_font.setWeight(QtGui.QFont.Bold)

        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum
        )

        self.gravatar_label = gravatar.GravatarLabel(self.context, parent=self)

        self.oid_label = TextLabel()
        self.oid_label.setTextFormat(Qt.PlainText)
        self.oid_label.setSizePolicy(policy)
        self.oid_label.setAlignment(Qt.AlignBottom)
        self.oid_label.elide()

        self.author_label = TextLabel()
        self.author_label.setTextFormat(Qt.RichText)
        self.author_label.setFont(author_font)
        self.author_label.setSizePolicy(policy)
        self.author_label.setAlignment(Qt.AlignTop)
        self.author_label.elide()

        self.date_label = TextLabel()
        self.date_label.setTextFormat(Qt.PlainText)
        self.date_label.setSizePolicy(policy)
        self.date_label.setAlignment(Qt.AlignTop)
        self.date_label.elide()

        self.summary_label = TextLabel()
        self.summary_label.setTextFormat(Qt.PlainText)
        self.summary_label.setFont(summary_font)
        self.summary_label.setSizePolicy(policy)
        self.summary_label.setAlignment(Qt.AlignTop)
        self.summary_label.elide()

        self.diff = DiffTextEdit(context, self, is_commit=is_commit, whitespace=False)
        self.setFocusProxy(self.diff)

        self.info_layout = qtutils.vbox(
            defs.no_margin,
            defs.no_spacing,
            self.oid_label,
            self.author_label,
            self.date_label,
            self.summary_label,
        )

        self.logo_layout = qtutils.hbox(
            defs.no_margin, defs.button_spacing, self.gravatar_label, self.info_layout
        )
        self.logo_layout.setContentsMargins(defs.margin, 0, defs.margin, 0)

        self.main_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.logo_layout, self.diff
        )
        self.setLayout(self.main_layout)

        self.set_tabwidth(prefs.tabwidth(context))

    def set_tabwidth(self, width):
        self.diff.set_tabwidth(width)

    def set_word_wrapping(self, enabled, update=False):
        """Enable and disable word wrapping"""
        self.diff.set_word_wrapping(enabled, update=update)

    def set_options(self, options):
        """Register an options widget"""
        self.options = options
        self.diff.set_options(options)

    def start_diff_task(self, task):
        """Clear the display and start a diff-gathering task"""
        self.diff.save_scrollbar()
        self.diff.set_loading_message()
        self.context.runtask.start(task, result=self.set_diff)

    def set_diff_oid(self, oid, filename=None):
        """Set the diff from a single commit object ID"""
        task = DiffInfoTask(self.context, oid, filename)
        self.start_diff_task(task)

    def set_diff_range(self, start, end, filename=None):
        task = DiffRangeTask(self.context, start + '~', end, filename)
        self.start_diff_task(task)

    def commits_selected(self, commits):
        """Display an appropriate diff when commits are selected"""
        if not commits:
            self.clear()
            return
        commit = commits[-1]
        oid = commit.oid
        author = commit.author or ''
        email = commit.email or ''
        date = commit.authdate or ''
        summary = commit.summary or ''
        self.set_details(oid, author, email, date, summary)
        self.oid = oid

        if len(commits) > 1:
            start, end = commits[0], commits[-1]
            self.set_diff_range(start.oid, end.oid)
            self.oid_start = start
            self.oid_end = end
        else:
            self.set_diff_oid(oid)
            self.oid_start = None
            self.oid_end = None

    def set_diff(self, diff):
        """Set the diff text"""
        self.diff.set_diff(diff)

    def set_details(self, oid, author, email, date, summary):
        template_args = {'author': author, 'email': email, 'summary': summary}
        author_text = (
            """%(author)s &lt;"""
            """<a href="mailto:%(email)s">"""
            """%(email)s</a>&gt;""" % template_args
        )
        author_template = '%(author)s <%(email)s>' % template_args

        self.date_label.set_text(date)
        self.date_label.setVisible(bool(date))
        self.oid_label.set_text(oid)
        self.author_label.set_template(author_text, author_template)
        self.summary_label.set_text(summary)
        self.gravatar_label.set_email(email)

    def clear(self):
        self.date_label.set_text('')
        self.oid_label.set_text('')
        self.author_label.set_text('')
        self.summary_label.set_text('')
        self.gravatar_label.clear()
        self.diff.clear()

    def files_selected(self, filenames):
        """Update the view when a filename is selected"""
        if not filenames:
            return
        oid_start = self.oid_start
        oid_end = self.oid_end
        if oid_start and oid_end:
            self.set_diff_range(oid_start.oid, oid_end.oid, filename=filenames[0])
        else:
            self.set_diff_oid(self.oid, filename=filenames[0])


class DiffPanel(QtWidgets.QWidget):
    """A combined diff + search panel"""

    def __init__(self, diff_widget, text_widget, parent):
        super().__init__(parent)
        self.diff_widget = diff_widget
        self.search_widget = TextSearchWidget(text_widget, self)
        self.search_widget.hide()
        layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.diff_widget, self.search_widget
        )
        self.setLayout(layout)
        self.setFocusProxy(self.diff_widget)

        self.search_action = qtutils.add_action(
            self,
            N_('Search in Diff'),
            self.show_search,
            hotkeys.SEARCH,
        )

    def show_search(self):
        """Show a dialog for searching diffs"""
        # The diff search is only active in text mode.
        if not self.search_widget.isVisible():
            self.search_widget.show()
        self.search_widget.setFocus(True)


class TextLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        QtWidgets.QLabel.__init__(self, parent)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
        )
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
        text = self._metrics.elidedText(self._template, Qt.ElideRight, width - 2)
        if text != self._template:
            self._display = text

    # Qt overrides
    def setFont(self, font):
        self._metrics = QtGui.QFontMetrics(font)
        QtWidgets.QLabel.setFont(self, font)

    def resizeEvent(self, event):
        if self._elide:
            self.update_text(event.size().width())
            with qtutils.BlockSignals(self):
                self.setText(self._display)
        QtWidgets.QLabel.resizeEvent(self, event)


class DiffInfoTask(qtutils.Task):
    """Gather diffs for a single commit"""

    def __init__(self, context, oid, filename):
        qtutils.Task.__init__(self)
        self.context = context
        self.oid = oid
        self.filename = filename

    def task(self):
        context = self.context
        oid = self.oid
        return gitcmds.diff_info(context, oid, filename=self.filename)


class DiffRangeTask(qtutils.Task):
    """Gather diffs for a range of commits"""

    def __init__(self, context, start, end, filename):
        qtutils.Task.__init__(self)
        self.context = context
        self.start = start
        self.end = end
        self.filename = filename

    def task(self):
        context = self.context
        return gitcmds.diff_range(context, self.start, self.end, filename=self.filename)
