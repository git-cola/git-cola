import re

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QSyntaxHighlighter
from PyQt4.QtGui import QTextCharFormat
from PyQt4.QtGui import QColor

from cola import utils
from cola import qtutils
from cola.i18n import N_
from cola.widgets import completion
from cola.widgets import defs


def create_button(text='', layout=None, tooltip=None, icon=None):
    """Create a button, set its title, and add it to the parent."""
    button = QtGui.QPushButton()
    button.setCursor(Qt.PointingHandCursor)
    if text:
        button.setText(text)
    if icon:
        button.setIcon(icon)
    if tooltip is not None:
        button.setToolTip(tooltip)
    if layout is not None:
        layout.addWidget(button)
    return button


class DockTitleBarWidget(QtGui.QWidget):

    def __init__(self, parent, title):
        QtGui.QWidget.__init__(self, parent)
        self.label = label = QtGui.QLabel()
        font = label.font()
        font.setCapitalization(QtGui.QFont.SmallCaps)
        label.setFont(font)
        label.setText(title)

        self.setCursor(QtCore.Qt.OpenHandCursor)

        self.close_button = QtGui.QPushButton()
        self.close_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.close_button.setFlat(True)
        self.close_button.setFixedSize(QtCore.QSize(16, 16))
        self.close_button.setIcon(qtutils.titlebar_close_icon())
        self.close_button.setToolTip(N_('Close'))

        self.toggle_button = QtGui.QPushButton()
        self.toggle_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.toggle_button.setFlat(True)
        self.toggle_button.setFixedSize(QtCore.QSize(16, 16))
        self.toggle_button.setIcon(qtutils.titlebar_normal_icon())
        self.toggle_button.setToolTip(N_('Detach'))

        self.corner_layout = QtGui.QHBoxLayout()
        self.corner_layout.setMargin(defs.no_margin)
        self.corner_layout.setSpacing(defs.spacing)

        self.main_layout = layout = QtGui.QHBoxLayout()
        self.main_layout.setMargin(defs.small_margin)
        self.main_layout.setSpacing(defs.spacing)

        self.main_layout.addWidget(label)
        self.main_layout.addStretch()
        self.main_layout.addLayout(self.corner_layout)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.close_button)
        self.setLayout(layout)

        qtutils.connect_button(self.toggle_button, self.toggle_floating)
        qtutils.connect_button(self.close_button, self.toggle_visibility)

    def toggle_floating(self):
        self.parent().setFloating(not self.parent().isFloating())
        self.update_tooltips()

    def toggle_visibility(self):
        self.parent().toggleViewAction().trigger()

    def set_title(self, title):
        self.label.setText(title)

    def add_corner_widget(self, widget):
        self.corner_layout.addWidget(widget)

    def update_tooltips(self):
        if self.parent().isFloating():
            tooltip = N_('Attach')
        else:
            tooltip = N_('Detach')
        self.toggle_button.setToolTip(tooltip)


def create_dock(title, parent):
    """Create a dock widget and set it up accordingly."""
    dock = QtGui.QDockWidget(parent)
    dock.setWindowTitle(title)
    dock.setObjectName(title)
    titlebar = DockTitleBarWidget(dock, title)
    dock.setTitleBarWidget(titlebar)
    return dock


def create_menu(title, parent):
    """Create a menu and set its title."""
    qmenu = QtGui.QMenu(parent)
    qmenu.setTitle(title)
    return qmenu


def create_toolbutton(text=None, layout=None, tooltip=None, icon=None):
    button = QtGui.QToolButton()
    button.setAutoRaise(True)
    button.setAutoFillBackground(True)
    button.setCursor(Qt.PointingHandCursor)
    if icon:
        button.setIcon(icon)
    if text:
        button.setText(text)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    if tooltip:
        button.setToolTip(tooltip)
    if layout is not None:
        layout.addWidget(button)
    return button


class QFlowLayoutWidget(QtGui.QWidget):

    _horizontal = QtGui.QBoxLayout.LeftToRight
    _vertical = QtGui.QBoxLayout.TopToBottom

    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self._direction = self._vertical
        self._layout = layout = QtGui.QBoxLayout(self._direction)
        layout.setSpacing(defs.spacing)
        layout.setMargin(defs.margin)
        self.setLayout(layout)
        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                   QtGui.QSizePolicy.Minimum)
        self.setSizePolicy(policy)
        self.setMinimumSize(QtCore.QSize(1, 1))
        self.aspect_ratio = 0.8

    def resizeEvent(self, event):
        size = event.size()
        if size.width() * self.aspect_ratio < size.height():
            dxn = self._vertical
        else:
            dxn = self._horizontal

        if dxn != self._direction:
            self._direction = dxn
            self.layout().setDirection(dxn)


class ExpandableGroupBox(QtGui.QGroupBox):
    def __init__(self, parent=None):
        QtGui.QGroupBox.__init__(self, parent)
        self.setFlat(True)
        self.expanded = True
        self.click_pos = None
        self.arrow_icon_size = 16

    def set_expanded(self, expanded):
        if expanded == self.expanded:
            self.emit(SIGNAL('expanded(bool)'), expanded)
            return
        self.expanded = expanded
        for widget in self.findChildren(QtGui.QWidget):
            widget.setHidden(not expanded)
        self.emit(SIGNAL('expanded(bool)'), expanded)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            option = QtGui.QStyleOptionGroupBox()
            self.initStyleOption(option)
            icon_size = self.arrow_icon_size
            button_area = QtCore.QRect(0, 0, icon_size, icon_size)
            offset = self.arrow_icon_size + defs.spacing
            adjusted = option.rect.adjusted(0, 0, -offset, 0)
            top_left = adjusted.topLeft()
            button_area.moveTopLeft(QtCore.QPoint(top_left))
            self.click_pos = event.pos()
        QtGui.QGroupBox.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if (event.button() == Qt.LeftButton and
            self.click_pos == event.pos()):
            self.set_expanded(not self.expanded)
        QtGui.QGroupBox.mouseReleaseEvent(self, event)

    def paintEvent(self, event):
        painter = QtGui.QStylePainter(self)
        option = QtGui.QStyleOptionGroupBox()
        self.initStyleOption(option)
        painter.save()
        painter.translate(self.arrow_icon_size + defs.spacing, 0)
        painter.drawText(option.rect, Qt.AlignLeft, self.title())
        painter.restore()

        style = QtGui.QStyle
        point = option.rect.adjusted(0, -4, 0, 0).topLeft()
        icon_size = self.arrow_icon_size
        option.rect = QtCore.QRect(point.x(), point.y(), icon_size, icon_size)
        if self.expanded:
            painter.drawPrimitive(style.PE_IndicatorArrowDown, option)
        else:
            painter.drawPrimitive(style.PE_IndicatorArrowRight, option)


class GitRefDialog(QtGui.QDialog):
    def __init__(self, title, button_text, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(title)

        self.label = QtGui.QLabel()
        self.label.setText(title)

        self.lineedit = completion.GitRefLineEdit(self)
        self.setFocusProxy(self.lineedit)

        self.ok_button = QtGui.QPushButton()
        self.ok_button.setText(button_text)
        self.ok_button.setIcon(qtutils.apply_icon())

        self.close_button = QtGui.QPushButton()
        self.close_button.setText(N_('Close'))

        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.setMargin(defs.no_margin)
        self.button_layout.setSpacing(defs.button_spacing)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.close_button)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.spacing)

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.lineedit)
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.ok_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

        self.connect(self.lineedit, SIGNAL('textChanged(QString)'),
                     self.text_changed)

        self.setWindowModality(Qt.WindowModal)
        self.ok_button.setEnabled(False)

    def text(self):
        return unicode(self.lineedit.text())

    def text_changed(self, txt):
        self.ok_button.setEnabled(bool(self.text()))

    def set_text(self, ref):
        self.lineedit.setText(ref)

    @staticmethod
    def ref(title, button_text, parent, default=None):
        dlg = GitRefDialog(title, button_text, parent)
        if default:
            dlg.set_text(default)
        dlg.show()
        dlg.raise_()
        dlg.setFocus()
        if dlg.exec_() == GitRefDialog.Accepted:
            return dlg.text()
        else:
            return None

# Syntax highlighting

def TERMINAL(pattern):
    """
    Denotes that a pattern is the final pattern that should
    be matched.  If this pattern matches no other formats
    will be applied, even if they would have matched.
    """
    return '__TERMINAL__:%s' % pattern

# Cache the results of re.compile so that we don't keep
# rebuilding the same regexes whenever stylesheets change
_RGX_CACHE = {}

def rgba(r, g, b, a=255):
    c = QColor()
    c.setRgb(r, g, b)
    c.setAlpha(a)
    return c

default_colors = {
    'color_text':           rgba(0x00, 0x00, 0x00),
    'color_add':            rgba(0xcd, 0xff, 0xe0),
    'color_remove':         rgba(0xff, 0xd0, 0xd0),
    'color_header':         rgba(0xbb, 0xbb, 0xbb),
}


class GenericSyntaxHighligher(QSyntaxHighlighter):
    def __init__(self, doc, *args, **kwargs):
        QSyntaxHighlighter.__init__(self, doc)
        for attr, val in default_colors.items():
            setattr(self, attr, val)
        self._rules = []
        self.enabled = True
        self.generate_rules()

    def generate_rules(self):
        pass

    def set_enabled(self, enabled):
        self.enabled = enabled

    def create_rules(self, *rules):
        if len(rules) % 2:
            raise Exception('create_rules requires an even '
                            'number of arguments.')
        for idx, rule in enumerate(rules):
            if idx % 2:
                continue
            formats = rules[idx+1]
            terminal = rule.startswith(TERMINAL(''))
            if terminal:
                rule = rule[len(TERMINAL('')):]
            try:
                regex = _RGX_CACHE[rule]
            except KeyError:
                regex = _RGX_CACHE[rule] = re.compile(rule)
            self._rules.append((regex, formats, terminal,))

    def formats(self, line):
        matched = []
        for regex, fmts, terminal in self._rules:
            match = regex.match(line)
            if not match:
                continue
            matched.append([match, fmts])
            if terminal:
                return matched
        return matched

    def mkformat(self, fg=None, bg=None, bold=False):
        fmt = QTextCharFormat()
        if fg:
            fmt.setForeground(fg)
        if bg:
            fmt.setBackground(bg)
        if bold:
            fmt.setFontWeight(QFont.Bold)
        return fmt

    def highlightBlock(self, qstr):
        if not self.enabled:
            return
        ascii = unicode(qstr)
        if not ascii:
            return
        formats = self.formats(ascii)
        if not formats:
            return
        for match, fmts in formats:
            start = match.start()
            groups = match.groups()

            # No groups in the regex, assume this is a single rule
            # that spans the entire line
            if not groups:
                self.setFormat(0, len(ascii), fmts)
                continue

            # Groups exist, rule is a tuple corresponding to group
            for grpidx, group in enumerate(groups):
                # allow empty matches
                if not group:
                    continue
                # allow None as a no-op format
                length = len(group)
                if fmts[grpidx]:
                    self.setFormat(start, start+length,
                            fmts[grpidx])
                start += length

    def set_colors(self, colordict):
        for attr, val in colordict.items():
            setattr(self, attr, val)


class DiffSyntaxHighlighter(GenericSyntaxHighligher):
    """Implements the diff syntax highlighting

    This class is used by widgets that display diffs.

    """
    def __init__(self, doc, whitespace=True):
        self.whitespace = whitespace
        GenericSyntaxHighligher.__init__(self, doc)

    def generate_rules(self):
        diff_head = self.mkformat(fg=self.color_header)
        diff_head_bold = self.mkformat(fg=self.color_header, bold=True)

        diff_add = self.mkformat(fg=self.color_text, bg=self.color_add)
        diff_remove = self.mkformat(fg=self.color_text, bg=self.color_remove)

        if self.whitespace:
            bad_ws = self.mkformat(fg=Qt.black, bg=Qt.red)

        # We specify the whitespace rule last so that it is
        # applied after the diff addition/removal rules.
        # The rules for the header
        diff_old_rgx = TERMINAL(r'^--- ')
        diff_new_rgx = TERMINAL(r'^\+\+\+ ')
        diff_ctx_rgx = TERMINAL(r'^@@ ')

        diff_hd1_rgx = TERMINAL(r'^diff --git a/.*b/.*')
        diff_hd2_rgx = TERMINAL(r'^index \S+\.\.\S+')
        diff_hd3_rgx = TERMINAL(r'^new file mode')
        diff_hd4_rgx = TERMINAL(r'^deleted file mode')
        diff_add_rgx = TERMINAL(r'^\+')
        diff_rmv_rgx = TERMINAL(r'^-')
        diff_bar_rgx = TERMINAL(r'^([ ]+.*)(\|[ ]+\d+[ ]+[+-]+)$')
        diff_sts_rgx = (r'(.+\|.+?)(\d+)(.+?)([\+]*?)([-]*?)$')
        diff_sum_rgx = (r'(\s+\d+ files changed[^\d]*)'
                        r'(:?\d+ insertions[^\d]*)'
                        r'(:?\d+ deletions.*)$')

        self.create_rules(diff_old_rgx,     diff_head,
                          diff_new_rgx,     diff_head,
                          diff_ctx_rgx,     diff_head_bold,
                          diff_bar_rgx,     (diff_head_bold, diff_head),
                          diff_hd1_rgx,     diff_head,
                          diff_hd2_rgx,     diff_head,
                          diff_hd3_rgx,     diff_head,
                          diff_hd4_rgx,     diff_head,
                          diff_add_rgx,     diff_add,
                          diff_rmv_rgx,     diff_remove,
                          diff_sts_rgx,     (None, diff_head,
                                             None, diff_head,
                                             diff_head),
                          diff_sum_rgx,     (diff_head,
                                             diff_head,
                                             diff_head))
        if self.whitespace:
            self.create_rules('(..*?)(\s+)$', (None, bad_ws))


if __name__ == '__main__':
    import sys
    class SyntaxTestDialog(QtGui.QDialog):
        def __init__(self, parent):
            QtGui.QDialog.__init__(self, parent)
            self.resize(720, 512)
            self.vboxlayout = QtGui.QVBoxLayout(self)
            self.vboxlayout.setObjectName('vboxlayout')
            self.output_text = QtGui.QTextEdit(self)
            font = QtGui.QFont()
            if utils.is_darwin():
                family = 'Monaco'
            else:
                family = 'Monospace'
            font.setFamily(family)
            font.setPointSize(12)
            self.output_text.setFont(font)
            self.output_text.setAcceptDrops(False)
            self.vboxlayout.addWidget(self.output_text)
            self.syntax = DiffSyntaxHighlighter(self.output_text.document())

    app = QtGui.QApplication(sys.argv)
    dialog = SyntaxTestDialog(qtutils.active_window())
    dialog.show()
    dialog.raise_()
    app.exec_()
