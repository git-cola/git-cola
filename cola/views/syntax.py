# Copyright (c) 2008 David Aguilar
"""This module provides SyntaxHighlighter classes.
These classes are installed onto specific cola widgets and
implement the diff syntax highlighting.

"""

import re
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
            if rule in _RGX_CACHE:
                regex = _RGX_CACHE[rule]
            else:
                regex = re.compile(rule)
                _RGX_CACHE[rule] = regex
            self._rules.append((regex, formats, terminal,))

    def formats(self, line):
        matched = []
        for regex, fmts, terminal in self._rules:
            match = regex.match(line)
            if match:
                matched.append([match, fmts])
                if terminal:
                    return matched
        return matched

    def mkformat(self, fg=None, bg=None, bold=False):
        format = QTextCharFormat()
        if fg: format.setForeground(fg)
        if bg: format.setBackground(bg)
        if bold: format.setFontWeight(QFont.Bold)
        return format

    def highlightBlock(self, qstr):
        ascii = qstr.toAscii().data()
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
                if not group: continue
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
        if private_attr in self.__dict__:
            return self.__dict__[private_attr]
        else:
            return None
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
    from PyQt4 import QtCore, QtGui
    class SyntaxTestDialog(QtGui.QDialog):
        def __init__(self, parent):
            QtGui.QDialog.__init__(self, parent)
            self.setupUi(self)
        def setupUi(self, dialog):
            dialog.resize(QtCore.QSize(QtCore.QRect(0,0,720,512).size()).expandedTo(dialog.minimumSizeHint()))
            self.vboxlayout = QtGui.QVBoxLayout(dialog)
            self.vboxlayout.setObjectName('vboxlayout')
            self.output_text = QtGui.QTextEdit(dialog)
            font = QtGui.QFont()
            font.setFamily('Monospace')
            font.setPointSize(13)
            self.output_text.setFont(font)
            self.output_text.setAcceptDrops(False)
            self.vboxlayout.addWidget(self.output_text)
            self.syntax = DiffSyntaxHighlighter(self.output_text.document())

    app = QtGui.QApplication(sys.argv)
    dialog = SyntaxTestDialog(app.activeWindow())
    dialog.show()
    dialog.exec_()
