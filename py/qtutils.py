from PyQt4 import QtGui
from PyQt4.QtGui import QClipboard
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QListWidgetItem
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QPixmap
from views import GitCommandDialog

def create_listwidget_item (text, filename):
	icon = QIcon (QPixmap (filename))
	item = QListWidgetItem()
	item.setIcon (icon)
	item.setText (text)
	return item

def information (parent, title, message):
	'''Launches a QMessageBox information with the
	provided title and message.'''
	QMessageBox.information(parent, title, message)

def get_selected_row (list_widget):
	'''Returns a (row_number, is_selected) tuple for a QListWidget.'''
	row = list_widget.currentRow()
	item = list_widget.item (row)
	selected = item is not None and item.isSelected()
	return (row, selected)

def get_selection_from_list (list_widget, items):
	'''Returns an array of model items that correspond to
	the selected QListWidget indices.'''
	selected = []
	for idx in range (list_widget.count()):
		item = list_widget.item (idx)
		if item.isSelected():
			selected.append (items[idx])
	return selected


def question (parent, title, message, default=True):
	'''Launches a QMessageBox question with the provided title and message.
	Passing "default=False" will make "No" the default choice.'''
	yes = QMessageBox.Yes
	no = QMessageBox.No
	buttons = yes | no

	if default:
		default = yes
	else:
		default = no

	result = QMessageBox.question (parent,
			title, message, buttons, default)
	return result == QMessageBox.Yes

def set_clipboard (text):
	QtGui.qApp.clipboard().setText (text, QClipboard.Clipboard)
	QtGui.qApp.clipboard().setText (text, QClipboard.Selection)

def show_command (parent, output):
	dialog = GitCommandDialog (parent, output=output)
	dialog.show()
	dialog.exec_()
