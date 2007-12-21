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

		begin = self.__mkformat (QFont.Bold, Qt.cyan)
		addition = self.__mkformat (QFont.Bold, Qt.green)
		removal = self.__mkformat (QFont.Bold, Qt.red)
		message = self.__mkformat (QFont.Bold, Qt.yellow, Qt.black)

		# Catch trailing whitespace
		bad_ws_format = self.__mkformat (QFont.Bold, Qt.black, Qt.red)
		self._bad_ws_regex = re.compile ('(.*?)(\s+)$')
		self._bad_ws_format = bad_ws_format

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
		fmt = self.getFormat (ascii)
		if fmt:
			match = self._bad_ws_regex.match (ascii)
			if match and match.group (2):
				start = len (match.group (1))
				self.setFormat (0, start, fmt)
				self.setFormat (start, len (ascii),
						self._bad_ws_format)
			else:
				self.setFormat (0, len (ascii), fmt)

	def __mkformat (self, weight, color, bgcolor=None):
		format = QTextCharFormat()
		format.setFontWeight (weight)
		format.setForeground (color)
		if bgcolor: format.setBackground (bgcolor)
		return format


if __name__ == '__main__':
	import sys
	from PyQt4 import QtCore, QtGui

	class SyntaxTestDialog(QtGui.QDialog):
		def __init__ (self, parent):
			QtGui.QDialog.__init__ (self, parent)
			self.setupUi (self)
	
		def setupUi(self, CommandDialog):
			CommandDialog.resize(QtCore.QSize(QtCore.QRect(0,0,720,512).size()).expandedTo(CommandDialog.minimumSizeHint()))

			self.vboxlayout = QtGui.QVBoxLayout(CommandDialog)
			self.vboxlayout.setObjectName("vboxlayout")

			self.commandText = QtGui.QTextEdit(CommandDialog)

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
