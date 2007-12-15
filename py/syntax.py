#!/usr/bin/python
import re
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QSyntaxHighlighter
from PyQt4.QtGui import QTextCharFormat

BEGIN = 0
ADD = 1
REMOVE = 2
TEXT = 3

class GitSyntaxHighlighter (QSyntaxHighlighter):

	def __init__ (self, doc):
		QSyntaxHighlighter.__init__ (self, doc)

		begin = self._mkformat (QFont.Bold, Qt.cyan)
		addition = self._mkformat (QFont.Bold, Qt.green)
		removal = self._mkformat (QFont.Bold, Qt.red)
		message = self._mkformat (QFont.Bold, Qt.yellow, Qt.black)

		self._rules = (
			( re.compile ('^(@@|\+\+\+|---)'), begin ),
			( re.compile ('^\+'), addition ),
			( re.compile ('^-'), removal ),
			( re.compile ('^:'), message ),
		)
	
	def getFormat (self, line):
		for regex, rule in self._rules:
			if regex.match (line):
				return rule
		return None
	
	def highlightBlock (self, qstr):
		ascii = qstr.toAscii().data()
		if not ascii: return
		format = self.getFormat (ascii)
		if format: self.setFormat (0, len (ascii), format)

	def _mkformat (self, weight, color, bgcolor=None):
		format = QTextCharFormat()
		format.setFontWeight (weight)
		format.setForeground (color)
		if bgcolor: format.setBackground (bgcolor)
		return format


if __name__ == '__main__':
	import sys
	from PyQt4 import QtCore, QtGui, QTextEdit

	class SyntaxTestDialog(QtGui.QDialog):
		def __init__ (self, parent):
			QtGui.QDialog.__init__ (self, parent)
			self.setupUi (self)
	
		def setupUi(self, CommandDialog):
			CommandDialog.resize(QtCore.QSize(QtCore.QRect(0,0,720,512).size()).expandedTo(CommandDialog.minimumSizeHint()))

			self.vboxlayout = QtGui.QVBoxLayout(CommandDialog)
			self.vboxlayout.setObjectName("vboxlayout")

			self.commandText = QTextEdit(CommandDialog)

			font = QtGui.QFont()
			font.setFamily("Monospace")
			font.setPointSize(13)
			self.commandText.setFont(font)
			self.commandText.setAcceptDrops(False)
			#self.commandText.setReadOnly(True)
			self.vboxlayout.addWidget(self.commandText)

			GitSyntaxHighlighter (self.commandText.document())

	
	app = QtGui.QApplication (sys.argv)
	dialog = SyntaxTestDialog (app.activeWindow())
	dialog.show()
	dialog.exec_()
