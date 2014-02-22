# Copyright (c) 2008 David Aguilar
"""This module provides miscellaneous Qt utility functions.
"""
from __future__ import division

import os
import re

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import gitcfg
from cola import utils
from cola import resources
from cola.decorators import memoize
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models.prefs import FONTDIFF
from cola.widgets import defs


def connect_action(action, fn):
    action.connect(action, SIGNAL('triggered()'), fn)


def connect_action_bool(action, fn):
    action.connect(action, SIGNAL('triggered(bool)'), fn)


def connect_button(button, fn):
    button.connect(button, SIGNAL('clicked()'), fn)


def connect_toggle(toggle, fn):
    toggle.connect(toggle, SIGNAL('toggled(bool)'), fn)


def active_window():
    return QtGui.QApplication.activeWindow()


def prompt(msg, title=None, text=''):
    """Presents the user with an input widget and returns the input."""
    if title is None:
        title = msg
    result = QtGui.QInputDialog.getText(active_window(), msg, title,
                                        QtGui.QLineEdit.Normal, text)
    return (unicode(result[0]), result[1])


def create_listwidget_item(text, filename):
    """Creates a QListWidgetItem with text and the icon at filename."""
    item = QtGui.QListWidgetItem()
    item.setIcon(QtGui.QIcon(filename))
    item.setText(text)
    return item


def create_treewidget_item(text, filename):
    """Creates a QTreeWidgetItem with text and the icon at filename."""
    icon = cached_icon_from_path(filename)
    item = QtGui.QTreeWidgetItem()
    item.setIcon(0, icon)
    item.setText(0, text)
    return item


@memoize
def cached_icon_from_path(filename):
    return QtGui.QIcon(filename)


def confirm(title, text, informative_text, ok_text,
            icon=None, default=True):
    """Confirm that an action should take place"""
    if icon is None:
        icon = ok_icon()
    elif icon and isinstance(icon, basestring):
        icon = QtGui.QIcon(icon)
    msgbox = QtGui.QMessageBox(active_window())
    msgbox.setWindowModality(Qt.WindowModal)
    msgbox.setWindowTitle(title)
    msgbox.setText(text)
    msgbox.setInformativeText(informative_text)
    ok = msgbox.addButton(ok_text, QtGui.QMessageBox.ActionRole)
    ok.setIcon(icon)
    cancel = msgbox.addButton(QtGui.QMessageBox.Cancel)
    if default:
        msgbox.setDefaultButton(ok)
    else:
        msgbox.setDefaultButton(cancel)
    msgbox.exec_()
    return msgbox.clickedButton() == ok


class ResizeableMessageBox(QtGui.QMessageBox):

    def __init__(self, parent):
        QtGui.QMessageBox.__init__(self, parent)
        self.setMouseTracking(True)
        self.setSizeGripEnabled(True)

    def event(self, event):
        res = QtGui.QMessageBox.event(self, event)
        event_type = event.type()
        if (event_type == QtCore.QEvent.MouseMove or
                event_type == QtCore.QEvent.MouseButtonPress):
            maxi = QtCore.QSize(1024*4, 1024*4)
            self.setMaximumSize(maxi)
            text = self.findChild(QtGui.QTextEdit)
            if text is not None:
                expand = QtGui.QSizePolicy.Expanding
                text.setSizePolicy(QtGui.QSizePolicy(expand, expand))
                text.setMaximumSize(maxi)
        return res


def critical(title, message=None, details=None):
    """Show a warning with the provided title and message."""
    if message is None:
        message = title
    mbox = ResizeableMessageBox(active_window())
    mbox.setWindowTitle(title)
    mbox.setTextFormat(Qt.PlainText)
    mbox.setText(message)
    mbox.setIcon(QtGui.QMessageBox.Critical)
    mbox.setStandardButtons(QtGui.QMessageBox.Close)
    mbox.setDefaultButton(QtGui.QMessageBox.Close)
    if details:
        mbox.setDetailedText(details)
    mbox.exec_()


def information(title, message=None, details=None, informative_text=None):
    """Show information with the provided title and message."""
    if message is None:
        message = title
    mbox = QtGui.QMessageBox(active_window())
    mbox.setStandardButtons(QtGui.QMessageBox.Close)
    mbox.setDefaultButton(QtGui.QMessageBox.Close)
    mbox.setWindowTitle(title)
    mbox.setWindowModality(Qt.WindowModal)
    mbox.setTextFormat(Qt.PlainText)
    mbox.setText(message)
    if informative_text:
        mbox.setInformativeText(informative_text)
    if details:
        mbox.setDetailedText(details)
    # Render git.svg into a 1-inch wide pixmap
    pixmap = QtGui.QPixmap(resources.icon('git.svg'))
    xres = pixmap.physicalDpiX()
    pixmap = pixmap.scaledToHeight(xres, Qt.SmoothTransformation)
    mbox.setIconPixmap(pixmap)
    mbox.exec_()


def question(title, msg, default=True):
    """Launches a QMessageBox question with the provided title and message.
    Passing "default=False" will make "No" the default choice."""
    yes = QtGui.QMessageBox.Yes
    no = QtGui.QMessageBox.No
    buttons = yes | no
    if default:
        default = yes
    else:
        default = no
    result = (QtGui.QMessageBox
                   .question(active_window(), title, msg, buttons, default))
    return result == QtGui.QMessageBox.Yes


def selected_treeitem(tree_widget):
    """Returns a(id_number, is_selected) for a QTreeWidget."""
    id_number = None
    selected = False
    item = tree_widget.currentItem()
    if item:
        id_number = item.data(0, Qt.UserRole).toInt()[0]
        selected = True
    return(id_number, selected)


def selected_row(list_widget):
    """Returns a(row_number, is_selected) tuple for a QListWidget."""
    items = list_widget.selectedItems()
    if not items:
        return (-1, False)
    item = items[0]
    return (list_widget.row(item), True)


def selection_list(listwidget, items):
    """Returns an array of model items that correspond to
    the selected QListWidget indices."""
    selected = []
    itemcount = listwidget.count()
    widgetitems = [ listwidget.item(idx) for idx in range(itemcount) ]

    for item, widgetitem in zip(items, widgetitems):
        if widgetitem.isSelected():
            selected.append(item)
    return selected


def tree_selection(treeitem, items):
    """Returns model items that correspond to selected widget indices"""
    itemcount = treeitem.childCount()
    widgetitems = [ treeitem.child(idx) for idx in range(itemcount) ]
    selected = []
    for item, widgetitem in zip(items[:len(widgetitems)], widgetitems):
        if widgetitem.isSelected():
            selected.append(item)

    return selected


def selected_item(list_widget, items):
    """Returns the selected item in a QListWidget."""
    widget_items = list_widget.selectedItems()
    if not widget_items:
        return None
    widget_item = widget_items[0]
    row = list_widget.row(widget_item)
    if row < len(items):
        return items[row]
    else:
        return None


def selected_items(list_widget, items):
    """Returns the selected item in a QListWidget."""
    selection = []
    widget_items = list_widget.selectedItems()
    if not widget_items:
        return selection
    for widget_item in widget_items:
        row = list_widget.row(widget_item)
        if row < len(items):
            selection.append(items[row])
    return selection


def open_file(title, directory=None):
    """Creates an Open File dialog and returns a filename."""
    return unicode(QtGui.QFileDialog
                        .getOpenFileName(active_window(), title, directory))


def open_files(title, directory=None, filter=None):
    """Creates an Open File dialog and returns a list of filenames."""
    return (QtGui.QFileDialog
            .getOpenFileNames(active_window(), title, directory, filter))


def opendir_dialog(title, path):
    """Prompts for a directory path"""

    flags = (QtGui.QFileDialog.ShowDirsOnly |
             QtGui.QFileDialog.DontResolveSymlinks)
    return unicode(QtGui.QFileDialog
                        .getExistingDirectory(active_window(),
                                              title, path, flags))


def save_as(filename, title='Save As...'):
    """Creates a Save File dialog and returns a filename."""
    return unicode(QtGui.QFileDialog
                        .getSaveFileName(active_window(), title, filename))


def icon(basename):
    """Given a basename returns a QIcon from the corresponding cola icon."""
    return QtGui.QIcon(resources.icon(basename))


def set_clipboard(text):
    """Sets the copy/paste buffer to text."""
    if not text:
        return
    clipboard = QtGui.QApplication.instance().clipboard()
    clipboard.setText(text, QtGui.QClipboard.Clipboard)
    clipboard.setText(text, QtGui.QClipboard.Selection)


def add_action_bool(widget, text, fn, checked, *shortcuts):
    action = _add_action(widget, text, fn, connect_action_bool, *shortcuts)
    action.setCheckable(True)
    action.setChecked(checked)
    return action


def add_action(widget, text, fn, *shortcuts):
    return _add_action(widget, text, fn, connect_action, *shortcuts)


def _add_action(widget, text, fn, connect, *shortcuts):
    action = QtGui.QAction(text, widget)
    connect(action, fn)
    if shortcuts:
        shortcuts = list(set(shortcuts))
        action.setShortcuts(shortcuts)
        action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        widget.addAction(action)
    return action

def set_selected_item(widget, idx):
    """Sets a the currently selected item to the item at index idx."""
    if type(widget) is QtGui.QTreeWidget:
        item = widget.topLevelItem(idx)
        if item:
            widget.setItemSelected(item, True)
            widget.setCurrentItem(item)


def add_items(widget, items):
    """Adds items to a widget."""
    for item in items:
        widget.addItem(item)


def set_items(widget, items):
    """Clear the existing widget contents and set the new items."""
    widget.clear()
    add_items(widget, items)


def icon_file(filename, staged=False, untracked=False):
    """Returns a file path representing a corresponding file path."""
    if staged:
        if core.exists(filename):
            ifile = resources.icon('staged-item.png')
        else:
            ifile = resources.icon('removed.png')
    elif untracked:
        ifile = resources.icon('untracked.png')
    else:
        ifile = utils.file_icon(filename)
    return ifile


def icon_for_file(filename, staged=False, untracked=False):
    """Returns a QIcon for a particular file path."""
    ifile = icon_file(filename, staged=staged, untracked=untracked)
    return icon(ifile)


def create_treeitem(filename, staged=False, untracked=False, check=True):
    """Given a filename, return a QListWidgetItem suitable
    for adding to a QListWidget.  "staged" and "untracked"
    controls whether to use the appropriate icons."""
    if check:
        ifile = icon_file(filename, staged=staged, untracked=untracked)
    else:
        ifile = resources.icon('staged.png')
    return create_treewidget_item(filename, ifile)


def update_file_icons(widget, items, staged=True,
                      untracked=False, offset=0):
    """Populate a QListWidget with custom icon items."""
    for idx, model_item in enumerate(items):
        item = widget.item(idx+offset)
        if item:
            item.setIcon(icon_for_file(model_item, staged, untracked))

@memoize
def cached_icon(key):
    """Maintain a cache of standard icons and return cache entries."""
    style = QtGui.QApplication.instance().style()
    return style.standardIcon(key)


def dir_icon():
    """Return a standard icon for a directory."""
    return cached_icon(QtGui.QStyle.SP_DirIcon)


def file_icon():
    """Return a standard icon for a file."""
    return cached_icon(QtGui.QStyle.SP_FileIcon)


def apply_icon():
    """Return a standard Apply icon"""
    return cached_icon(QtGui.QStyle.SP_DialogApplyButton)


def new_icon():
    return cached_icon(QtGui.QStyle.SP_FileDialogNewFolder)


def save_icon():
    """Return a standard Save icon"""
    return cached_icon(QtGui.QStyle.SP_DialogSaveButton)


def ok_icon():
    """Return a standard Ok icon"""
    return cached_icon(QtGui.QStyle.SP_DialogOkButton)


def open_icon():
    """Return a standard open directory icon"""
    return cached_icon(QtGui.QStyle.SP_DirOpenIcon)


def help_icon():
    """Return a standard open directory icon"""
    return cached_icon(QtGui.QStyle.SP_DialogHelpButton)


def add_icon():
    return icon('add.svg')


def remove_icon():
    return icon('remove.svg')


def open_file_icon():
    return icon('open.svg')


def options_icon():
    """Return a standard open directory icon"""
    return icon('options.svg')


def dir_close_icon():
    """Return a standard closed directory icon"""
    return cached_icon(QtGui.QStyle.SP_DirClosedIcon)


def titlebar_close_icon():
    """Return a dock widget close icon"""
    return cached_icon(QtGui.QStyle.SP_TitleBarCloseButton)


def titlebar_normal_icon():
    """Return a dock widget close icon"""
    return cached_icon(QtGui.QStyle.SP_TitleBarNormalButton)


def git_icon():
    return icon('git.svg')


def reload_icon():
    """Returna  standard Refresh icon"""
    return cached_icon(QtGui.QStyle.SP_BrowserReload)


def discard_icon():
    """Return a standard Discard icon"""
    return cached_icon(QtGui.QStyle.SP_DialogDiscardButton)


def close_icon():
    """Return a standard Close icon"""
    return cached_icon(QtGui.QStyle.SP_DialogCloseButton)


def add_close_action(widget):
    """Adds close action and shortcuts to a widget."""
    return add_action(widget, N_('Close...'),
                      widget.close, QtGui.QKeySequence.Close, 'Ctrl+Q')


def center_on_screen(widget):
    """Move widget to the center of the default screen"""
    desktop = QtGui.QApplication.instance().desktop()
    rect = desktop.screenGeometry(QtGui.QCursor().pos())
    cy = rect.height()//2
    cx = rect.width()//2
    widget.move(cx - widget.width()//2, cy - widget.height()//2)


@memoize
def theme_icon(name):
    """Grab an icon from the current theme with a fallback

    Support older versions of Qt by catching AttributeError and
    falling back to our default icons.

    """
    try:
        base, ext = os.path.splitext(name)
        qicon = QtGui.QIcon.fromTheme(base)
        if not qicon.isNull():
            return qicon
    except AttributeError:
        pass
    return icon(name)


def default_monospace_font():
    font = QtGui.QFont()
    family = 'Monospace'
    if utils.is_darwin():
        family = 'Monaco'
    font.setFamily(family)
    return font


def diff_font_str():
    font_str = gitcfg.instance().get(FONTDIFF)
    if font_str is None:
        font = default_monospace_font()
        font_str = unicode(font.toString())
    return font_str


def diff_font():
    font_str = diff_font_str()
    font = QtGui.QFont()
    font.fromString(font_str)
    return font


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


def create_action_button(tooltip=None, icon=None):
    button = QtGui.QPushButton()
    button.setFixedSize(QtCore.QSize(16, 16))
    button.setCursor(Qt.PointingHandCursor)
    button.setFlat(True)
    if tooltip is not None:
        button.setToolTip(tooltip)
    if icon is not None:
        pixmap = icon.pixmap(QtCore.QSize(16, 16))
        button.setIcon(QtGui.QIcon(pixmap))
    return button


def hide_button_menu_indicator(button):
    cls = type(button)
    name = cls.__name__
    stylesheet = """
        %(name)s::menu-indicator {
            image: none;
        }
    """
    if name == 'QPushButton':
        stylesheet += """
            %(name)s {
                border-style: none;
            }
        """
    button.setStyleSheet(stylesheet % {'name': name})


class DockTitleBarWidget(QtGui.QWidget):

    def __init__(self, parent, title, stretch=True):
        QtGui.QWidget.__init__(self, parent)
        self.label = label = QtGui.QLabel()
        font = label.font()
        font.setCapitalization(QtGui.QFont.SmallCaps)
        label.setFont(font)
        label.setText(title)

        self.setCursor(Qt.OpenHandCursor)

        self.close_button = create_action_button(
                tooltip=N_('Close'), icon=titlebar_close_icon())

        self.toggle_button = create_action_button(
                tooltip=N_('Detach'), icon=titlebar_normal_icon())

        self.corner_layout = QtGui.QHBoxLayout()
        self.corner_layout.setMargin(defs.no_margin)
        self.corner_layout.setSpacing(defs.spacing)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.setMargin(defs.small_margin)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addWidget(label)
        self.main_layout.addSpacing(defs.spacing)
        if stretch:
            self.main_layout.addStretch()
        self.main_layout.addLayout(self.corner_layout)
        self.main_layout.addSpacing(defs.spacing)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.close_button)

        self.setLayout(self.main_layout)

        connect_button(self.toggle_button, self.toggle_floating)
        connect_button(self.close_button, self.toggle_visibility)

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


def create_dock(title, parent, stretch=True):
    """Create a dock widget and set it up accordingly."""
    dock = QtGui.QDockWidget(parent)
    dock.setWindowTitle(title)
    dock.setObjectName(title)
    titlebar = DockTitleBarWidget(dock, title, stretch=stretch)
    dock.setTitleBarWidget(titlebar)
    if hasattr(parent, 'dockwidgets'):
        parent.dockwidgets.append(dock)
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
    if icon is not None:
        button.setIcon(icon)
    if text is not None:
        button.setText(text)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    if tooltip is not None:
        button.setToolTip(tooltip)
    if layout is not None:
        layout.addWidget(button)
    return button


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
    c = QtGui.QColor()
    c.setRgb(r, g, b)
    c.setAlpha(a)
    return c

default_colors = {
    'color_text':           rgba(0x00, 0x00, 0x00),
    'color_add':            rgba(0xcd, 0xff, 0xe0),
    'color_remove':         rgba(0xff, 0xd0, 0xd0),
    'color_header':         rgba(0xbb, 0xbb, 0xbb),
}


class GenericSyntaxHighligher(QtGui.QSyntaxHighlighter):
    def __init__(self, doc, *args, **kwargs):
        QtGui.QSyntaxHighlighter.__init__(self, doc)
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
        fmt = QtGui.QTextCharFormat()
        if fg:
            fmt.setForeground(fg)
        if bg:
            fmt.setBackground(bg)
        if bold:
            fmt.setFontWeight(QtGui.QFont.Bold)
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
            self.create_rules(r'(..*?)(\s+)$', (None, bad_ws))


def install():
    Interaction.critical = staticmethod(critical)
    Interaction.confirm = staticmethod(confirm)
    Interaction.question = staticmethod(question)
    Interaction.information = staticmethod(information)
