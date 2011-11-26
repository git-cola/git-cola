import re
import subprocess

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QSyntaxHighlighter
from PyQt4.QtGui import QTextCharFormat
from PyQt4.QtGui import QColor

import cola
from cola import utils
from cola import qtutils
from cola.compat import set
from cola.qtutils import tr
from cola.widgets import defs


def create_button(text, layout=None, tooltip=None, icon=None):
    """Create a button, set its title, and add it to the parent."""
    button = QtGui.QPushButton()
    button.setText(tr(text))
    if icon:
        button.setIcon(icon)
    if layout is not None:
        layout.addWidget(button)
    return button


class DockTitleBarWidget(QtGui.QWidget):
    def __init__(self, parent, title):
        QtGui.QWidget.__init__(self, parent)
        label = QtGui.QLabel()
        font = label.font()
        font.setCapitalization(QtGui.QFont.SmallCaps)
        label.setFont(font)
        label.setText(title)

        self.close_button = QtGui.QPushButton()
        self.close_button.setFlat(True)
        self.close_button.setFixedSize(QtCore.QSize(16, 16))
        self.close_button.setIcon(qtutils.titlebar_close_icon())

        self.toggle_button = QtGui.QPushButton()
        self.toggle_button.setFlat(True)
        self.toggle_button.setFixedSize(QtCore.QSize(16, 16))
        self.toggle_button.setIcon(qtutils.titlebar_normal_icon())

        layout = QtGui.QHBoxLayout()
        layout.setMargin(2)
        layout.setSpacing(defs.spacing)
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.close_button)
        self.setLayout(layout)

        self.connect(self.toggle_button, SIGNAL('clicked()'),
                     self.toggle_floating)

        self.connect(self.close_button, SIGNAL('clicked()'),
                     self.parent().toggleViewAction().trigger)

    def toggle_floating(self):
        self.parent().setFloating(not self.parent().isFloating())


def create_dock(title, parent):
    """Create a dock widget and set it up accordingly."""
    dock = QtGui.QDockWidget(parent)
    dock.setWindowTitle(tr(title))
    dock.setObjectName(title)
    titlebar = DockTitleBarWidget(dock, title)
    dock.setTitleBarWidget(titlebar)
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

    def resizeEvent(self, event):
        size = event.size()
        if size.width() * 0.8 < size.height():
            dxn = self._vertical
        else:
            dxn = self._horizontal

        if dxn != self._direction:
            self._direction = dxn
            self.layout().setDirection(dxn)


class QCollapsibleGroupBox(QtGui.QGroupBox):
    def __init__(self, parent=None):
        QtGui.QGroupBox.__init__(self, parent)
        self.setFlat(True)
        self.collapsed = False
        self.click_pos = None
        self.collapse_icon_size = 16

    def set_collapsed(self, collapsed):
        self.collapsed = collapsed
        for widget in self.findChildren(QtGui.QWidget):
            widget.setHidden(collapsed)
        self.emit(SIGNAL('toggled(bool)'), collapsed)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            option = QtGui.QStyleOptionGroupBox()
            self.initStyleOption(option)
            icon_size = self.collapse_icon_size
            button_area = QtCore.QRect(0, 0, icon_size, icon_size)
            top_left = option.rect.adjusted(0, 0, -10, 0).topLeft()
            button_area.moveTopLeft(QtCore.QPoint(top_left))
            self.click_pos = event.pos()
        QtGui.QGroupBox.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if (event.button() == QtCore.Qt.LeftButton and
            self.click_pos == event.pos()):
            self.set_collapsed(not self.collapsed)
        QtGui.QGroupBox.mouseReleaseEvent(self, event)

    def paintEvent(self, event):
        painter = QtGui.QStylePainter(self)
        option = QtGui.QStyleOptionGroupBox()
        self.initStyleOption(option)
        painter.save()
        painter.translate(self.collapse_icon_size + 4, 0)
        painter.drawComplexControl(QtGui.QStyle.CC_GroupBox, option)
        painter.restore()

        style = QtGui.QStyle
        point = option.rect.adjusted(0, 0, -10, 0).topLeft()
        icon_size = self.collapse_icon_size
        option.rect = QtCore.QRect(point.x(), point.y(), icon_size, icon_size)
        if self.collapsed:
            painter.drawPrimitive(style.PE_IndicatorArrowRight, option)
        else:
            painter.drawPrimitive(style.PE_IndicatorArrowDown, option)


class GitRefCompleter(QtGui.QCompleter):
    """Provides completion for branches and tags"""
    def __init__(self, parent):
        QtGui.QCompleter.__init__(self, parent)
        self._model = GitRefModel(parent)
        self.setModel(self._model)
        self.setCompletionMode(self.UnfilteredPopupCompletion)
        self.setCaseSensitivity(QtCore.Qt.CaseInsensitive)

    def __del__(self):
        self.dispose()

    def dispose(self):
        self._model.dispose()


class GitRefLineEdit(QtGui.QLineEdit):
    def __init__(self, parent=None):
        QtGui.QLineEdit.__init__(self, parent)
        self.refcompleter = GitRefCompleter(self)
        self.setCompleter(self.refcompleter)


class GitRefModel(QtGui.QStandardItemModel):
    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.cmodel = cola.model()
        msg = self.cmodel.message_updated
        self.cmodel.add_message_observer(msg, self.update_matches)
        self.update_matches()

    def dispose(self):
        self.cmodel.remove_observer(self.update_matches)

    def update_matches(self):
        model = self.cmodel
        matches = model.local_branches + model.remote_branches + model.tags
        QStandardItem = QtGui.QStandardItem
        self.clear()
        for match in matches:
            item = QStandardItem()
            item.setIcon(qtutils.git_icon())
            item.setText(match)
            self.appendRow(item)


class UpdateGitLogCompletionModelThread(QtCore.QThread):
    def __init__(self, model):
        QtCore.QThread.__init__(self)
        self.model = model
        self.case_insensitive = False

    def run(self):
        text = None
        # Loop when the matched text changes between the start and end time.
        # This happens when gather_matches() takes too long and the
        # model's matched_text changes in-between.
        while text != self.model.matched_text:
            text = self.model.matched_text
            items = self.model.gather_matches(self.case_insensitive)
        self.emit(SIGNAL('items_gathered'), *items)


class GitLogCompletionModel(QtGui.QStandardItemModel):
    def __init__(self, parent):
        self.matched_text = None
        QtGui.QStandardItemModel.__init__(self, parent)
        self.cmodel = cola.model()
        self.update_thread = UpdateGitLogCompletionModelThread(self)
        self.connect(self.update_thread, SIGNAL('items_gathered'),
                     self.apply_matches)

    def lower_cmp(self, a, b):
        return cmp(a.replace('.','').lower(), b.replace('.','').lower())

    def update_matches(self, case_insensitive):
        self.update_thread.case_insensitive = case_insensitive
        if not self.update_thread.isRunning():
            self.update_thread.start()

    def gather_matches(self, case_sensitive):
        file_list = self.cmodel.everything()
        files = set(file_list)
        files_and_dirs = utils.add_parents(set(files))

        dirs = files_and_dirs.difference(files)

        model = self.cmodel
        refs = model.local_branches + model.remote_branches + model.tags
        matched_text = self.matched_text

        if matched_text:
            if case_sensitive:
                matched_refs = [r for r in refs if matched_text in r]
            else:
                matched_refs = [r for r in refs
                                    if matched_text.lower() in r.lower()]
        else:
            matched_refs = refs

        matched_refs.sort(cmp=self.lower_cmp)

        if matched_text:
            if case_sensitive:
                matched_paths = [f for f in files_and_dirs
                                        if matched_text in f]
            else:
                matched_paths = [f for f in files_and_dirs
                                    if matched_text.lower() in f.lower()]
        else:
            matched_paths = list(files_and_dirs)

        matched_paths.sort(cmp=self.lower_cmp)

        return (matched_refs, matched_paths, dirs)


    def apply_matches(self, matched_refs, matched_paths, dirs):
        QStandardItem = QtGui.QStandardItem
        file_icon = qtutils.file_icon()
        dir_icon = qtutils.dir_icon()
        git_icon = qtutils.git_icon()

        matched_text = self.matched_text
        items = []
        for ref in matched_refs:
            item = QStandardItem()
            item.setText(ref)
            item.setIcon(git_icon)
            items.append(item)

        if matched_paths and (not matched_text or matched_text in '--'):
            item = QStandardItem()
            item.setText('--')
            item.setIcon(file_icon)
            items.append(item)

        for match in matched_paths:
            item = QStandardItem()
            item.setText(match)
            if match in dirs:
                item.setIcon(dir_icon)
            else:
                item.setIcon(file_icon)
            items.append(item)

        self.clear()
        self.invisibleRootItem().appendRows(items)

    def set_match_text(self, text, case_sensitive):
        self.matched_text = text
        self.update_matches(case_sensitive)


class GitLogLineEdit(QtGui.QLineEdit):
    def __init__(self, parent=None):
        QtGui.QLineEdit.__init__(self, parent)
        # used to hide the completion popup after a drag-select
        self._drag = 0

        self._model = GitLogCompletionModel(self)
        self._delegate = HighlightCompletionDelegate(self)

        self._completer = QtGui.QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setModel(self._model)
        self._completer.setCompletionMode(
                QtGui.QCompleter.UnfilteredPopupCompletion)
        self._completer.popup().setItemDelegate(self._delegate)

        self.connect(self._completer, SIGNAL('activated(QString)'),
                     self._complete)
        self.connect(self, SIGNAL('textChanged(QString)'), self._text_changed)
        self._keys_to_ignore = set([QtCore.Qt.Key_Enter,
                                    QtCore.Qt.Key_Return,
                                    QtCore.Qt.Key_Escape])

    def is_case_sensitive(self, text):
        return bool([char for char in text if char.isupper()])

    def _text_changed(self, text):
        text = self.last_word()
        case_sensitive = self.is_case_sensitive(text)
        if case_sensitive:
            self._completer.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        else:
            self._completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._delegate.set_highlight_text(text, case_sensitive)
        self._model.set_match_text(text, case_sensitive)

    def update_matches(self):
        text = self.last_word()
        case_sensitive = self.is_case_sensitive(text)
        self._model.update_matches(case_sensitive)

    def _complete(self, completion):
        """
        This is the event handler for the QCompleter.activated(QString) signal,
        it is called when the user selects an item in the completer popup.
        """
        if not completion:
            return
        words = self.words()
        if words:
            words.pop()
        words.append(unicode(completion))
        self.setText(subprocess.list2cmdline(words))
        self.emit(SIGNAL('ref_changed'))

    def words(self):
        return utils.shell_usplit(unicode(self.text()))

    def last_word(self):
        words = self.words()
        if not words:
            return unicode(self.text())
        if not words[-1]:
            return u''
        return words[-1]

    def event(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if (event.key() == QtCore.Qt.Key_Tab and
                self._completer.popup().isVisible()):
                    event.ignore()
                    return True
        return QtGui.QLineEdit.event(self, event)

    def do_completion(self):
        self._completer.popup().setCurrentIndex(
                self._completer.completionModel().index(0,0))
        self._completer.complete()

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() in self._keys_to_ignore:
                event.ignore()
                self._complete(self.last_word())
                return

        elif (event.key() == QtCore.Qt.Key_Down and
              self._completer.completionCount() > 0):
                event.accept()
                self.do_completion()
                return

        QtGui.QLineEdit.keyPressEvent(self, event)

        prefix = self.last_word()
        if prefix != unicode(self._completer.completionPrefix()):
            self._update_popup_items(prefix)
        if len(event.text()) > 0 and len(prefix) > 0:
            self._completer.complete()
        if len(prefix) == 0:
            self._completer.popup().hide()

    #: _drag: 0 - unclicked, 1 - clicked, 2 - dragged
    def mousePressEvent(self, event):
        self._drag = 1
        return QtGui.QLineEdit.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self._drag == 1:
            self._drag = 2
        return QtGui.QLineEdit.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self._drag != 2 and event.buttons() != QtCore.Qt.RightButton:
            self.do_completion()
        self._drag = 0
        return QtGui.QLineEdit.mouseReleaseEvent(self, event)

    def close_popup(self):
        self._completer.popup().close()

    def _update_popup_items(self, prefix):
        """
        Filters the completer's popup items to only show items
        with the given prefix.
        """
        self._completer.setCompletionPrefix(prefix)
        self._completer.popup().setCurrentIndex(
                self._completer.completionModel().index(0,0))


class HighlightCompletionDelegate(QtGui.QStyledItemDelegate):
    """A delegate used for auto-completion to give formatted completion"""
    def __init__(self, parent=None): # model, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.highlight_text = ''
        self.case_sensitive = False

        self.doc = QtGui.QTextDocument()
        self.doc.setDocumentMargin(0)

    def set_highlight_text(self, text, case_sensitive):
        """Sets the text that will be made bold in the term name when displayed"""
        self.highlight_text = text
        self.case_sensitive = case_sensitive

    def paint(self, painter, option, index):
        """Overloaded Qt method for custom painting of a model index"""
        if not self.highlight_text:
            return QtGui.QStyledItemDelegate.paint(self, painter, option, index)

        text = unicode(index.data().toPyObject())
        if self.case_sensitive:
            html = text.replace(self.highlight_text,
                                '<strong>%s</strong>' % self.highlight_text)
        else:
            match = re.match('(.*)(' + self.highlight_text + ')(.*)',
                             text, re.IGNORECASE)
            if match:
                start = match.group(1) or ''
                middle = match.group(2) or ''
                end = match.group(3) or ''
                html = (start + ('<strong>%s</strong>' % middle) + end)
            else:
                html = text
        self.doc.setHtml(html)

        # Painting item without text, Text Document will paint the text
        optionV4 = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, index)
        optionV4.text = QtCore.QString()

        style = QtGui.QApplication.style()
        style.drawControl(QtGui.QStyle.CE_ItemViewItem, optionV4, painter)
        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        # Highlighting text if item is selected
        if (optionV4.state & QtGui.QStyle.State_Selected):
            ctx.palette.setColor(QtGui.QPalette.Text, optionV4.palette.color(QtGui.QPalette.Active, QtGui.QPalette.HighlightedText))

        # translate the painter to where the text is drawn
        textRect = style.subElementRect(QtGui.QStyle.SE_ItemViewItemText, optionV4)
        painter.save()

        start = textRect.topLeft() + QtCore.QPoint(3, 0)
        painter.translate(start)
        painter.setClipRect(textRect.translated(-start))

        # tell the text document to draw the html for us
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()

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

def color(c, a=255):
    qc = QColor(c)
    qc.setAlpha(a)
    return qc

default_colors = {
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
}


class GenericSyntaxHighligher(QSyntaxHighlighter):
    def __init__(self, doc, *args, **kwargs):
        QSyntaxHighlighter.__init__(self, doc)
        for attr, val in default_colors.items():
            setattr(self, attr, val)
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
    dialog = SyntaxTestDialog(qtutils.active_window())
    dialog.show()
    dialog.raise_()
    app.exec_()
