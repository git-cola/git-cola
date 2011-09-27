import re

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QSyntaxHighlighter
from PyQt4.QtGui import QTextCharFormat
from PyQt4.QtGui import QColor
try:
    from PyQt4.QtCore import pyqtProperty
except ImportError:
    pyqtProperty = None

import cola
from cola import utils
from cola.qtutils import tr


def create_button(text, layout=None, tooltip=None, icon=None):
    """Create a button, set its title, and add it to the parent."""
    button = QtGui.QPushButton()
    button.setText(tr(text))
    if icon:
        button.setIcon(icon)
    if layout is not None:
        layout.addWidget(button)
    return button


def create_dock(title, parent):
    """Create a dock widget and set it up accordingly."""
    dock = QtGui.QDockWidget(parent)
    dock.setWindowTitle(tr(title))
    dock.setObjectName(title)
    return dock


def create_menu(title, parent):
    """Create a menu and set its title."""
    qmenu = QtGui.QMenu(parent)
    qmenu.setTitle(tr(title))
    return qmenu


def create_toolbutton(parent, text=None, layout=None, tooltip=None, icon=None):
    button = QtGui.QToolButton(parent)
    button.setAutoRaise(True)
    button.setAutoFillBackground(True)
    if icon:
        button.setIcon(icon)
    if text:
        button.setText(tr(text))
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    if tooltip:
        button.setToolTip(tr(tooltip))
    if layout is not None:
        layout.addWidget(button)
    return button


class QFlowLayoutWidget(QtGui.QWidget):

    _horizontal = QtGui.QBoxLayout.LeftToRight
    _vertical = QtGui.QBoxLayout.TopToBottom

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self._direction = self._vertical
        self._layout = layout = QtGui.QBoxLayout(self._direction)
        layout.setSpacing(2)
        layout.setMargin(2)
        self.setLayout(layout)
        self.setContentsMargins(2, 2, 2, 2)
        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                   QtGui.QSizePolicy.Minimum)
        self.setSizePolicy(policy)
        self.setMinimumSize(QtCore.QSize(1, 1))

    def resizeEvent(self, event):
        size = event.size()
        if size.width() * 0.8 < size.height():
            dxn = self._vertical
        else:
            dxn = self._horizontal

        if dxn != self._direction:
            self._direction = dxn
            self.layout().setDirection(dxn)


class GitRefCompleter(QtGui.QCompleter):
    """Provides completion for branches and tags"""
    def __init__(self, parent):
        QtGui.QCompleter.__init__(self, parent)
        self.model = GitRefStringListModel(parent)
        self.setModel(self.model)
        self.setCompletionMode(self.UnfilteredPopupCompletion)

    def __del__(self):
        self.dispose()

    def dispose(self):
        self.model.dispose()


class GitRefStringListModel(QtGui.QStringListModel):
    def __init__(self, parent=None):
        QtGui.QStringListModel.__init__(self, parent)
        self.model = cola.model()
        msg = self.model.message_updated
        self.model.add_message_observer(msg, self.update_git_refs)
        self.update_git_refs()

    def update_git_refs(self):
        model = self.model
        revs = model.local_branches + model.remote_branches + model.tags
        self.setStringList(revs)

    def dispose(self):
        self.model.remove_observer(self.update_git_refs)

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

default_colors = {}
def _install_default_colors():
    def color(c, a=255):
        qc = QColor(c)
        qc.setAlpha(a)
        return qc
    default_colors.update({
        'color_add':            color(Qt.green, 128),
        'color_remove':         color(Qt.red,   128),
        'color_begin':          color(Qt.darkCyan),
        'color_header':         color(Qt.darkYellow),
        'color_stat_add':       color(QColor(32, 255, 32)),
        'color_stat_info':      color(QColor(32, 32, 255)),
        'color_stat_remove':    color(QColor(255, 32, 32)),
        'color_emphasis':       color(Qt.black),
        'color_info':           color(Qt.blue),
        'color_date':           color(Qt.darkCyan),
    })
_install_default_colors()


class GenericSyntaxHighligher(QSyntaxHighlighter):
    def __init__(self, doc, *args, **kwargs):
        QSyntaxHighlighter.__init__(self, doc)
        for attr, val in default_colors.items():
            setattr(self, attr, val)
        self._rules = []
        self.generate_rules()
        self.reset()

    def reset(self):
        self._rules = []
        self.generate_rules()

    def generate_rules(self):
        pass

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
        ascii = unicode(qstr)
        if not ascii:
            return
        formats = self.formats(ascii)
        if not formats:
            return
        for match, fmts in formats:
            start = match.start()
            end = match.end()
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
        diff_begin = self.mkformat(self.color_begin, bold=True)
        diff_head = self.mkformat(self.color_header)
        diff_add = self.mkformat(bg=self.color_add)
        diff_remove = self.mkformat(bg=self.color_remove)

        diffstat_info = self.mkformat(self.color_stat_info, bold=True)
        diffstat_add = self.mkformat(self.color_stat_add, bold=True)
        diffstat_remove = self.mkformat(self.color_stat_remove, bold=True)

        if self.whitespace:
            bad_ws = self.mkformat(Qt.black, Qt.red)

        # We specify the whitespace rule last so that it is
        # applied after the diff addition/removal rules.
        # The rules for the header
        diff_bgn_rgx = TERMINAL('^@@|^\+\+\+|^---')
        diff_hd1_rgx = TERMINAL('^diff --git')
        diff_hd2_rgx = TERMINAL('^index \S+\.\.\S+')
        diff_hd3_rgx = TERMINAL('^new file mode')
        diff_add_rgx = TERMINAL('^\+')
        diff_rmv_rgx = TERMINAL('^-')
        diff_sts_rgx = ('(.+\|.+?)(\d+)(.+?)([\+]*?)([-]*?)$')
        diff_sum_rgx = ('(\s+\d+ files changed[^\d]*)'
                        '(:?\d+ insertions[^\d]*)'
                        '(:?\d+ deletions.*)$')

        self.create_rules(diff_bgn_rgx,     diff_begin,
                          diff_hd1_rgx,     diff_head,
                          diff_hd2_rgx,     diff_head,
                          diff_hd3_rgx,     diff_head,
                          diff_add_rgx,     diff_add,
                          diff_rmv_rgx,     diff_remove,
                          diff_sts_rgx,     (None, diffstat_info,
                                             None, diffstat_add,
                                             diffstat_remove),
                          diff_sum_rgx,     (diffstat_info,
                                             diffstat_add,
                                             diffstat_remove))
        if self.whitespace:
            self.create_rules('(..*?)(\s+)$', (None, bad_ws))


# This is used as a mixin to generate property callbacks
def accessors(attr):
    private_attr = '_'+attr

    def getter(self):
        return self.__dict__.get(private_attr, None)

    def setter(self, value):
        self.__dict__[private_attr] = value
        self.reset_syntax()
    return (getter, setter)

def install_style_properties(cls):
    # Diff GUI colors -- this is controllable via the style sheet
    if pyqtProperty is None:
        return
    for name in default_colors:
        setattr(cls, name, pyqtProperty('QColor', *accessors(name)))

def set_theme_properties(widget):
    for name, color in default_colors.items():
        widget.setProperty(name, QVariant(color))


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
            font.setPointSize(13)
            self.output_text.setFont(font)
            self.output_text.setAcceptDrops(False)
            self.vboxlayout.addWidget(self.output_text)
            self.syntax = DiffSyntaxHighlighter(self.output_text.document())

    app = QtGui.QApplication(sys.argv)
    dialog = SyntaxTestDialog(app.activeWindow())
    dialog.show()
    dialog.raise_()
    app.exec_()
