# Copyright (c) 2008 David Aguilar
"""This module provides miscellaneous Qt utility functions.
"""
import os

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import gitcfg
from cola import utils
from cola import settings
from cola import resources
from cola.compat import set
from cola.decorators import memoize
from cola.i18n import N_
from cola.interaction import Interaction


def connect_action(action, callback):
    action.connect(action, SIGNAL('triggered()'), callback)


def connect_action_bool(action, callback):
    action.connect(action, SIGNAL('triggered(bool)'), callback)


def connect_button(button, callback):
    button.connect(button, SIGNAL('clicked()'), callback)


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


def critical(title, message=None, details=None):
    """Show a warning with the provided title and message."""
    if message is None:
        message = title
    mbox = QtGui.QMessageBox(active_window())
    mbox.setWindowTitle(title)
    mbox.setTextFormat(QtCore.Qt.PlainText)
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
    mbox.setWindowModality(QtCore.Qt.WindowModal)
    mbox.setTextFormat(QtCore.Qt.PlainText)
    mbox.setText(message)
    if informative_text:
        mbox.setInformativeText(informative_text)
    if details:
        mbox.setDetailedText(details)
    # Render git.svg into a 1-inch wide pixmap
    pixmap = QtGui.QPixmap(resources.icon('git.svg'))
    xres = pixmap.physicalDpiX()
    pixmap = pixmap.scaledToHeight(xres, QtCore.Qt.SmoothTransformation)
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
        id_number = item.data(0, QtCore.Qt.UserRole).toInt()[0]
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


def open_dialog(title, filename=None):
    """Creates an Open File dialog and returns a filename."""
    return unicode(QtGui.QFileDialog
                        .getOpenFileName(active_window(), title, filename))


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


def add_action(widget, text, fn, *shortcuts):
    action = QtGui.QAction(text, widget)
    connect_action(action, fn)
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
        if os.path.exists(core.encode(filename)):
            ifile = resources.icon('staged-item.png')
        else:
            ifile = resources.icon('removed.png')
    elif untracked:
        ifile = resources.icon('untracked.png')
    else:
        ifile = utils.file_icon(core.encode(filename))
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

def sync_icon():
    """Return a Sync Code Icon"""
    return cached_icon(QtGui.QStyle.SP_DriveNetIcon)



def ok_icon():
    """Return a standard Ok icon"""
    return cached_icon(QtGui.QStyle.SP_DialogOkButton)


def open_icon():
    """Return a standard open directory icon"""
    return cached_icon(QtGui.QStyle.SP_DirOpenIcon)


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
    cy = rect.height()/2
    cx = rect.width()/2
    widget.move(cx - widget.width()/2, cy - widget.height()/2)


def save_state(widget, handler=None):
    if handler is None:
        handler = settings.Settings()
    if gitcfg.instance().get('cola.savewindowsettings', True):
        handler.save_gui_state(widget)


def export_window_state(widget, state, version):
    # Save the window state
    windowstate = widget.saveState(version)
    state['windowstate'] = unicode(windowstate.toBase64().data())
    return state


def apply_window_state(widget, state, version):
    # Restore the dockwidget, etc. window state
    try:
        windowstate = state['windowstate']
        return widget.restoreState(QtCore.QByteArray.fromBase64(str(windowstate)),
                                   version)
    except KeyError:
        return False


def apply_state(widget):
    state = settings.Settings().get_gui_state(widget)
    return bool(state) and widget.apply_state(state)


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


def install():
    Interaction.critical = staticmethod(critical)
    Interaction.confirm = staticmethod(confirm)
    Interaction.question = staticmethod(question)
    Interaction.information = staticmethod(information)
