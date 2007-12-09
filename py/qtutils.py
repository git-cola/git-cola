from PyQt4 import QtGui
from PyQt4.QtGui import QClipboard
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QListWidgetItem
from PyQt4.QtGui import QPixmap

def create_listwidget_item (text, filename):
	icon = QIcon (QPixmap (filename))
	item = QListWidgetItem()
	item.setIcon (icon)
	item.setText (text)
	return item

def set_clipboard (text):
	QtGui.qApp.clipboard().setText (text, QClipboard.Clipboard)
	QtGui.qApp.clipboard().setText (text, QClipboard.Selection)
