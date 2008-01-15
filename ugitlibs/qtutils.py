import os
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtGui import QClipboard
from PyQt4.QtGui import QFileDialog
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QListWidgetItem
from PyQt4.QtGui import QMessageBox

import views
import utils

LOGGER = None

def log(output, quiet=True, doraise=False):
	if not LOGGER: return
	LOGGER.log(output)
	if quiet: return
	LOGGER.show()
	if not doraise: return
	LOGGER.raise_()

def close_log_window():
	LOGGER.hide()
	LOGGER.done(0)

def show_output(output):
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

def information(parent, title, message):
	'''Launches a QMessageBox information with the
	provided title and message.'''
	QMessageBox.information(parent, title, message)

def get_selected_row(list_widget):
	'''Returns a(row_number, is_selected) tuple for a QListWidget.'''
	row = list_widget.currentRow()
	item = list_widget.item(row)
	selected = item is not None and item.isSelected()
	return(row, selected)

def get_selection_list(list_widget, items):
	'''Returns an array of model items that correspond to
	the selected QListWidget indices.'''
	selected = []
	for idx in range(list_widget.count()):
		item = list_widget.item(idx)
		if item.isSelected():
			selected.append(items[idx])
	return selected

def get_selected_item(list_widget, items):
	selected = get_selection_list(list_widget, items)
	if not selected: return None
	return selected[0]

def open_dialog(parent, title, filename=None):
	qstr = QFileDialog.getOpenFileName(
			parent, parent.tr(title), filename)
	return unicode(qstr)

def save_dialog(parent, title, filename=None):
	qstr = QFileDialog.getSaveFileName(
			parent, parent.tr(title), filename)
	return unicode(qstr)

def dir_dialog(parent, title, directory):
	directory = QFileDialog.getExistingDirectory(
			parent, title, directory)
	return unicode(directory)

def get_qicon(filename):
	icon = utils.get_icon(filename)
	return QIcon(icon)

def question(parent, title, message, default=True):
	'''Launches a QMessageBox question with the provided title and message.
	Passing "default=False" will make "No" the default choice.'''
	yes = QMessageBox.Yes
	no = QMessageBox.No
	buttons = yes | no
	if default:
		default = yes
	else:
		default = no
	result = QMessageBox.question(parent,
			title, message, buttons, default)
	return result == QMessageBox.Yes

def set_clipboard(text):
	QtGui.qApp.clipboard().setText(text, QClipboard.Clipboard)
	QtGui.qApp.clipboard().setText(text, QClipboard.Selection)

def add_items(widget, items):
	for item in items: widget.addItem(item)

def set_items(widget, items):
	widget.clear()
	add_items(widget, items)

def tr(txt):
	trtext = unicode(QtGui.qApp.tr(txt))
	if trtext.endswith('@@verb'):
		trtext = trtext.replace('@@verb','')
	if trtext.endswith('@@noun'):
		trtext = trtext.replace('@@noun','')
	return trtext

def create_item(filename, staged, untracked=False):
	'''Given a filename, return a QListWidgetItem suitable
	for adding to a QListWidget.  "staged" controls whether
	to use icons for the staged or unstaged list widget.'''
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

def update_listwidget(widget, items, staged=True,
			untracked=False, append=False):
	'''Populate a QListWidget with custom icon items.'''
	if not append: widget.clear()
	add_items( widget, [ create_item(i, staged, untracked) for i in items ])
