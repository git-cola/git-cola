# Copyright (c) 2008 David Aguilar
"""This module provides miscellaneous Qt utility functions.
"""
from __future__ import division, absolute_import, unicode_literals

import mimetypes
import os
import subprocess

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
from cola.compat import ustr


KNOWN_FILE_MIME_TYPES = [
    ('text',    'script.png'),
    ('image',   'image.png'),
    ('python',  'script.png'),
    ('ruby',    'script.png'),
    ('shell',   'script.png'),
    ('perl',    'script.png'),
    ('octet',   'binary.png'),
]

KNOWN_FILE_EXTENSIONS = {
    '.java':    'script.png',
    '.groovy':  'script.png',
    '.cpp':     'script.png',
    '.c':       'script.png',
    '.h':       'script.png',
    '.cxx':     'script.png',
}


def connect_action(action, fn):
    """Connectc an action to a function"""
    action.connect(action, SIGNAL('triggered()'), fn)


def connect_action_bool(action, fn):
    """Connect a triggered(bool) action to a function"""
    action.connect(action, SIGNAL('triggered(bool)'), fn)


def connect_button(button, fn):
    """Connect a button to a function"""
    button.connect(button, SIGNAL('clicked()'), fn)


def button_action(button, action):
    """Make a button trigger an action"""
    connect_button(button, action.trigger)


def connect_toggle(toggle, fn):
    toggle.connect(toggle, SIGNAL('toggled(bool)'), fn)


def active_window():
    return QtGui.QApplication.activeWindow()


def hbox(margin, spacing, *items):
    return box(QtGui.QHBoxLayout, margin, spacing, *items)


def vbox(margin, spacing, *items):
    return box(QtGui.QVBoxLayout, margin, spacing, *items)


STRETCH = object()
SKIPPED = object()


def box(cls, margin, spacing, *items):
    stretch = STRETCH
    skipped = SKIPPED
    layout = cls()
    layout.setMargin(margin)
    layout.setSpacing(spacing)

    for i in items:
        if i is stretch:
            layout.addStretch()
        elif i is skipped:
            continue
        elif isinstance(i, QtGui.QWidget):
            layout.addWidget(i)
        elif isinstance(i, (QtGui.QHBoxLayout, QtGui.QVBoxLayout,
                            QtGui.QFormLayout, QtGui.QLayout)):
            layout.addLayout(i)
        elif isinstance(i, (int, long)):
            layout.addSpacing(i)

    return layout


def form(margin, spacing, *widgets):
    layout = QtGui.QFormLayout()
    layout.setMargin(margin)
    layout.setSpacing(spacing)
    layout.setFieldGrowthPolicy(QtGui.QFormLayout.ExpandingFieldsGrow)

    for idx, (label, widget) in enumerate(widgets):
        if isinstance(label, (str, ustr)):
            layout.addRow(label, widget)
        else:
            layout.setWidget(idx, QtGui.QFormLayout.LabelRole, label)
            layout.setWidget(idx, QtGui.QFormLayout.FieldRole, widget)

    return layout


def grid(margin, spacing, *widgets):
    layout = QtGui.QGridLayout()
    layout.setMargin(defs.no_margin)
    layout.setSpacing(defs.spacing)

    for row in widgets:
        item = row[0]
        if isinstance(item, QtGui.QWidget):
            layout.addWidget(*row)
        elif isinstance(item, QtGui.QLayoutItem):
            layout.addItem(*row)

    return layout


def splitter(orientation, *widgets):
    layout = QtGui.QSplitter()
    layout.setOrientation(orientation)
    layout.setHandleWidth(defs.handle_width)
    layout.setChildrenCollapsible(True)
    for idx, widget in enumerate(widgets):
        layout.addWidget(widget)
        layout.setStretchFactor(idx, 1)

    return layout

def prompt(msg, title=None, text=''):
    """Presents the user with an input widget and returns the input."""
    if title is None:
        title = msg
    result = QtGui.QInputDialog.getText(active_window(), msg, title,
                                        QtGui.QLineEdit.Normal, text)
    return (ustr(result[0]), result[1])


def create_listwidget_item(text, filename):
    """Creates a QListWidgetItem with text and the icon at filename."""
    item = QtGui.QListWidgetItem()
    item.setIcon(QtGui.QIcon(filename))
    item.setText(text)
    return item


class TreeWidgetItem(QtGui.QTreeWidgetItem):

    TYPE = QtGui.QStandardItem.UserType + 101

    def __init__(self, path, icon, deleted):
        QtGui.QTreeWidgetItem.__init__(self)
        self.path = path
        self.deleted = deleted
        self.setIcon(0, cached_icon_from_path(icon))
        self.setText(0, path)

    def type(self):
        return self.TYPE


def paths_from_indexes(model, indexes,
                       item_type=TreeWidgetItem.TYPE,
                       item_filter=None):
    """Return paths from a list of QStandardItemModel indexes"""
    items = [model.itemFromIndex(i) for i in indexes]
    return paths_from_items(items, item_type=item_type, item_filter=item_filter)


def paths_from_items(items,
                     item_type=TreeWidgetItem.TYPE,
                     item_filter=None):
    """Return a list of paths from a list of items"""
    if item_filter is None:
        item_filter = lambda x: True
    return [i.path for i in items
            if i.type() == item_type and item_filter(i)]


@memoize
def cached_icon_from_path(filename):
    return QtGui.QIcon(filename)


def mkicon(icon, default=None):
    if icon is None and default is not None:
        icon = default()
    elif icon and isinstance(icon, (str, ustr)):
        icon = QtGui.QIcon(icon)
    return icon


def confirm(title, text, informative_text, ok_text,
            icon=None, default=True,
            cancel_text=None, cancel_icon=None):
    """Confirm that an action should take place"""
    msgbox = QtGui.QMessageBox(active_window())
    msgbox.setWindowModality(Qt.WindowModal)
    msgbox.setWindowTitle(title)
    msgbox.setText(text)
    msgbox.setInformativeText(informative_text)

    icon = mkicon(icon, ok_icon)
    ok = msgbox.addButton(ok_text, QtGui.QMessageBox.ActionRole)
    ok.setIcon(icon)

    cancel = msgbox.addButton(QtGui.QMessageBox.Cancel)
    cancel_icon = mkicon(cancel_icon, discard_icon)
    cancel.setIcon(cancel_icon)
    if cancel_text:
        cancel.setText(cancel_text)

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
    # Render git-cola.svg into a 1-inch wide pixmap
    pixmap = git_icon().pixmap(96)
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


def tree_selection(tree_item, items):
    """Returns an array of model items that correspond to the selected
    QTreeWidgetItem children"""
    selected = []
    count = min(tree_item.childCount(), len(items))
    for idx in range(count):
        if tree_item.child(idx).isSelected():
            selected.append(items[idx])

    return selected


def tree_selection_items(tree_item):
    """Returns selected widget items"""
    selected = []
    for idx in range(tree_item.childCount()):
        child = tree_item.child(idx)
        if child.isSelected():
            selected.append(child)

    return selected


def selected_item(list_widget, items):
    """Returns the model item that corresponds to the selected QListWidget
    row."""
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
    """Returns an array of model items that correspond to the selected
    QListWidget rows."""
    item_count = len(items)
    selected = []
    for widget_item in list_widget.selectedItems():
        row = list_widget.row(widget_item)
        if row < item_count:
            selected.append(items[row])
    return selected


def open_file(title, directory=None):
    """Creates an Open File dialog and returns a filename."""
    return ustr(QtGui.QFileDialog
                        .getOpenFileName(active_window(), title, directory))


def open_files(title, directory=None, filter=None):
    """Creates an Open File dialog and returns a list of filenames."""
    return (QtGui.QFileDialog
            .getOpenFileNames(active_window(), title, directory, filter))


def opendir_dialog(title, path):
    """Prompts for a directory path"""

    flags = (QtGui.QFileDialog.ShowDirsOnly |
             QtGui.QFileDialog.DontResolveSymlinks)
    return ustr(QtGui.QFileDialog
                     .getExistingDirectory(active_window(),
                                           title, path, flags))


def save_as(filename, title='Save As...'):
    """Creates a Save File dialog and returns a filename."""
    return ustr(QtGui.QFileDialog
                        .getSaveFileName(active_window(), title, filename))


def icon(basename):
    """Given a basename returns a QIcon from the corresponding cola icon."""
    return QtGui.QIcon(resources.icon(basename))


def copy_path(filename, absolute=True):
    """Copy a filename to the clipboard"""
    if filename is None:
        return
    if absolute:
        filename = core.abspath(filename)
    set_clipboard(filename)


def set_clipboard(text):
    """Sets the copy/paste buffer to text."""
    if not text:
        return
    clipboard = QtGui.QApplication.clipboard()
    clipboard.setText(text, QtGui.QClipboard.Clipboard)
    clipboard.setText(text, QtGui.QClipboard.Selection)
    persist_clipboard()


def persist_clipboard():
    """Persist the clipboard

    X11 stores only a reference to the clipboard data.
    Send a clipboard event to force a copy of the clipboard to occur.
    This ensures that the clipboard is present after git-cola exits.
    Otherwise, the reference is destroyed on exit.

    C.f. https://stackoverflow.com/questions/2007103/how-can-i-disable-clear-of-clipboard-on-exit-of-pyqt4-application

    """
    clipboard = QtGui.QApplication.clipboard()
    event = QtCore.QEvent(QtCore.QEvent.Clipboard)
    QtGui.QApplication.sendEvent(clipboard, event)


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


def icon_name_for_filename(filename):
    """Returns an icon name based on the filename."""
    mimetype = mimetypes.guess_type(filename)[0]
    if mimetype is not None:
        mimetype = mimetype.lower()
        for filetype, icon_name in KNOWN_FILE_MIME_TYPES:
            if filetype in mimetype:
                return icon_name
    extension = os.path.splitext(filename)[1]
    return KNOWN_FILE_EXTENSIONS.get(extension.lower(), 'generic.png')


def icon_from_filename(filename):
    icon_name = icon_name_for_filename(filename)
    return cached_icon_from_path(resources.icon(icon_name))


def create_treeitem(filename, staged=False, deleted=False, untracked=False):
    """Given a filename, return a TreeListItem suitable for adding to a
    QListWidget.  "staged", "deleted, and "untracked" control whether to use
    the appropriate icons."""
    if deleted:
        icon_name = 'removed.png'
    elif staged:
        icon_name = 'staged-item.png'
    elif untracked:
        icon_name = 'untracked.png'
    else:
        icon_name = icon_name_for_filename(filename)
    return TreeWidgetItem(filename, resources.icon(icon_name), deleted=deleted)


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
    return theme_icon('list-add', fallback='add.svg')


def remove_icon():
    return theme_icon('list-remove', fallback='remove.svg')


def open_file_icon():
    return theme_icon('document-open', fallback='open.svg')


def options_icon():
    """Return a standard open directory icon"""
    return theme_icon('configure', fallback='options.svg')


def filter_icon():
    """Return a filter icon"""
    return theme_icon('view-filter.png')


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
    """
    Return git-cola icon from X11 theme if it exists.
    Else fallback to default hardcoded icon.
    """
    return theme_icon('git-cola.svg')


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


def default_size(parent, width, height):
    """Return the parent's size, or the provided defaults"""
    if parent is not None:
        width = parent.width()
        height = parent.height()
    return (width, height)

@memoize
def theme_icon(name, fallback=None):
    """Grab an icon from the current theme with a fallback

    Support older versions of Qt checking for fromTheme's availability.

    """
    if hasattr(QtGui.QIcon, 'fromTheme'):
        base, ext = os.path.splitext(name)
        if fallback:
            qicon = QtGui.QIcon.fromTheme(base, icon(fallback))
        else:
            qicon = QtGui.QIcon.fromTheme(base)
        if not qicon.isNull():
            return qicon
    return icon(fallback or name)


def default_monospace_font():
    font = QtGui.QFont()
    family = 'Monospace'
    if utils.is_darwin():
        family = 'Monaco'
    font.setFamily(family)
    return font


def diff_font_str():
    font_str = gitcfg.current().get(FONTDIFF)
    if font_str is None:
        font = default_monospace_font()
        font_str = ustr(font.toString())
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
    if icon is not None:
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
        font.setBold(True)
        label.setFont(font)
        label.setText(title)

        self.setCursor(Qt.OpenHandCursor)

        self.close_button = create_action_button(
                tooltip=N_('Close'), icon=titlebar_close_icon())

        self.toggle_button = create_action_button(
                tooltip=N_('Detach'), icon=titlebar_normal_icon())

        self.corner_layout = hbox(defs.no_margin, defs.spacing)

        if stretch:
            separator = STRETCH
        else:
            separator = SKIPPED

        self.main_layout = hbox(defs.small_margin, defs.spacing,
                                label, separator, self.corner_layout,
                                self.toggle_button, self.close_button)
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


def mimedata_from_paths(paths):
    """Return mimedata with a list of absolute path URLs"""

    abspaths = [core.abspath(path) for path in paths]
    urls = [QtCore.QUrl.fromLocalFile(path) for path in abspaths]

    mimedata = QtCore.QMimeData()
    mimedata.setUrls(urls)

    # The text/x-moz-list format is always included by Qt, and doing
    # mimedata.removeFormat('text/x-moz-url') has no effect.
    # C.f. http://www.qtcentre.org/threads/44643-Dragging-text-uri-list-Qt-inserts-garbage
    #
    # gnome-terminal expects utf-16 encoded text, but other terminals,
    # e.g. terminator, prefer utf-8, so allow cola.dragencoding
    # to override the default.
    paths_text = subprocess.list2cmdline(abspaths)
    encoding = gitcfg.current().get('cola.dragencoding', 'utf-16')
    moz_text = core.encode(paths_text, encoding=encoding)
    mimedata.setData('text/x-moz-url', moz_text)

    return mimedata


def path_mimetypes():
    return ['text/uri-list', 'text/x-moz-url']


class BlockSignals(object):
    """Context manager for blocking a signals on a widget"""

    def __init__(self, *widgets):
        self.widgets = widgets
        self.values = {}

    def __enter__(self):
        for w in self.widgets:
            self.values[w] = w.blockSignals(True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for w in self.widgets:
            w.blockSignals(self.values[w])


# Syntax highlighting

def rgba(r, g, b, a=255):
    c = QtGui.QColor()
    c.setRgb(r, g, b)
    c.setAlpha(a)
    return c


def RGB(args):
    return rgba(*args)


def make_format(fg=None, bg=None, bold=False):
    fmt = QtGui.QTextCharFormat()
    if fg:
        fmt.setForeground(fg)
    if bg:
        fmt.setBackground(bg)
    if bold:
        fmt.setFontWeight(QtGui.QFont.Bold)
    return fmt


def install():
    Interaction.critical = staticmethod(critical)
    Interaction.confirm = staticmethod(confirm)
    Interaction.question = staticmethod(question)
    Interaction.information = staticmethod(information)
