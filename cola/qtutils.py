# Copyright (c) 2008 David Aguilar
import os
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QClipboard
from PyQt4.QtGui import QFileDialog
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QTreeWidget
from PyQt4.QtGui import QListWidgetItem
from PyQt4.QtGui import QMessageBox

from cola import utils

LOGGER = None

def log(output, quiet=True, doraise=False):
    if not LOGGER: return
    LOGGER.log(output)
    if quiet: return
    LOGGER.show()
    if not doraise: return
    raise_logger()

def raise_logger():
    LOGGER.raise_()

def input(msg, title=None):
    if title is None:
        title = msg
    parent = QtGui.qApp.activeWindow()
    result = QtGui.QInputDialog.getText(parent, msg, title)
    return (unicode(result[0]), result[1])

def close_log_window():
    LOGGER.hide()
    LOGGER.done(0)

def show_output(output, **kwargs):
    if not output: return
    log(output, quiet=False)

def toggle_log_window():
    if not LOGGER: return
    if LOGGER.isVisible():
        LOGGER.hide()
    else:
        LOGGER.show()
        LOGGER.raise_()

def create_listwidget_item(text, filename):
    icon = QIcon(filename)
    item = QListWidgetItem()
    item.setIcon(icon)
    item.setText(text)
    return item

def information(title, message=None):
    """Launches a QMessageBox information with the
    provided title and message."""
    if message is None:
        message = title
    QMessageBox.information(QtGui.qApp.activeWindow(), title, message)

def get_selected_treeitem(tree_widget):
    """Returns a(id_number, is_selected) for a QTreeWidget."""
    id_number = None
    selected = False
    item = tree_widget.currentItem()
    if item:
        id_number = item.data(0, Qt.UserRole).toInt()[0]
        selected = True
    return(id_number, selected)

def get_selected_row(list_widget):
    """Returns a(row_number, is_selected) tuple for a QListWidget."""
    row = list_widget.currentRow()
    item = list_widget.item(row)
    selected = item is not None and item.isSelected()
    return(row, selected)

def get_selection_list(listwidget, items):
    """Returns an array of model items that correspond to
    the selected QListWidget indices."""
    selected = []
    itemcount = listwidget.count()
    widgetitems = [ listwidget.item(idx) for idx in range(itemcount) ]

    for item, widgetitem in zip(items, widgetitems):
        if widgetitem.isSelected():
            selected.append(item)
    return selected

def get_selected_item(list_widget, items):
    row, selected = get_selected_row(list_widget)
    if selected and row < len(items):
        return items[row]
    else:
        return None

def open_dialog(parent, title, filename=None):
    qstr = QFileDialog.getOpenFileName(parent, parent.tr(title), filename)
    return unicode(qstr)

def opendir_dialog(parent, title, directory):
    flags = QtGui.QFileDialog.ShowDirsOnly | QtGui.QFileDialog.DontResolveSymlinks
    qstr = QFileDialog.getExistingDirectory(parent, directory,
                                            parent.tr(title),
                                            flags)
    return unicode(qstr)

def save_dialog(parent, title, filename=''):
    return unicode(QFileDialog.getSaveFileName(parent,
                                               parent.tr(title),
                                               filename))

def new_dir_dialog(parent, title, filename=''):
    return unicode(QFileDialog.getSaveFileName(parent,
                                               parent.tr(title),
                                               filename,
                                               os.getcwd(),
                                               parent.tr('New Directory ()')))

def dir_dialog(parent, title, directory):
    directory = QFileDialog.getExistingDirectory(parent, parent.tr(title), directory)
    return unicode(directory)

def get_qicon(filename):
    icon = utils.get_icon(filename)
    return QIcon(icon)

def question(parent, title, message, default=True):
    """Launches a QMessageBox question with the provided title and message.
    Passing "default=False" will make "No" the default choice."""
    yes = QMessageBox.Yes
    no = QMessageBox.No
    buttons = yes | no
    if default:
        default = yes
    else:
        default = no
    result = QMessageBox.question(parent, title, message, buttons, default)
    return result == QMessageBox.Yes

def set_clipboard(text):
    QtGui.qApp.clipboard().setText(text, QClipboard.Clipboard)
    QtGui.qApp.clipboard().setText(text, QClipboard.Selection)

def set_selected_item(widget, idx):
    if type(widget) is QTreeWidget:
        item = widget.topLevelItem(idx)
        if item:
            widget.setItemSelected(item, True)
            widget.setCurrentItem(item)

def add_items(widget, items):
    for item in items: widget.addItem(item)

def set_items(widget, items):
    widget.clear()
    add_items(widget, items)

def tr(txt):
    return unicode(QtGui.qApp.translate('', txt))

def create_item(filename, staged, untracked=False):
    """Given a filename, return a QListWidgetItem suitable
    for adding to a QListWidget.  "staged" and "untracked"
    controls whether to use the appropriate icons."""
    if staged:
        if os.path.exists(filename):
            icon_file = utils.get_icon('staged.png')
        else:
            icon_file = utils.get_icon('removed.png')
    elif untracked:
        icon_file = utils.get_icon('untracked.png')
    else:
        icon_file = utils.get_file_icon(filename)
    return create_listwidget_item(filename, icon_file)

def create_txt_item(txt):
    item = QListWidgetItem()
    item.setText(txt)
    return item

def update_listwidget(widget, items, staged=True,
            untracked=False, append=False):
    """Populate a QListWidget with custom icon items."""
    if not append: widget.clear()
    add_items(widget, [ create_item(i, staged, untracked) for i in items ])

def set_listwidget_strings(widget, items):
    widget.clear()
    add_items(widget, [ create_txt_item(i) for i in items ])
