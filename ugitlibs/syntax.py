#!/usr/bin/python
import re
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QSyntaxHighlighter
from PyQt4.QtGui import QTextCharFormat

class DiffSyntaxHighlighter(QSyntaxHighlighter):
	def __init__(self, doc):
		QSyntaxHighlighter.__init__(self, doc)

		begin = self.__mkformat(QFont.Bold, Qt.darkCyan)
		diffhead = self.__mkformat(QFont.Bold, Qt.darkYellow)
		addition = self.__mkformat(QFont.Bold, Qt.green)
		removal = self.__mkformat(QFont.Bold, Qt.red)

		# Catch trailing whitespace
		bad_ws_format = self.__mkformat(QFont.Bold, Qt.black, Qt.red)
		self._bad_ws_regex = re.compile('(.*?)(\s+)$')
		self._bad_ws_format = bad_ws_format

		self._rules =(
			( re.compile('^(@@|\+\+\+|---)'), begin ),
			( re.compile('^\+'), addition ),
			( re.compile('^-'), removal ),
			( re.compile('^(diff --git|index \S+\.\.\S+|new file mode)'),
					diffhead ),
		)
	
	def getFormat(self, line):
		for regex, rule in self._rules:
			if regex.match(line):
				return rule
		return None
	
	def highlightBlock(self, qstr):
		ascii = qstr.toAscii().data()
		if not ascii: return
		fmt = self.getFormat(ascii)
		if fmt:
			match = self._bad_ws_regex.match(ascii)
			if match and match.group(2):
				start = len(match.group(1))
				self.setFormat(0, start, fmt)
				self.setFormat(start, len(ascii),
						self._bad_ws_format)
			else:
				self.setFormat(0, len(ascii), fmt)

	def __mkformat(self, weight, color, bgcolor=None):
		format = QTextCharFormat()
		format.setFontWeight(weight)
		format.setForeground(color)
		if bgcolor: format.setBackground(bgcolor)
		return format

if __name__ == '__main__':
	import sys
	from PyQt4 import QtCore, QtGui
	class SyntaxTestDialog(QtGui.QDialog):
		def __init__(self, parent):
			QtGui.QDialog.__init__(self, parent)
			self.setupUi(self)
		def setupUi(self, dialog):
			dialog.resize(QtCore.QSize(QtCore.QRect(0,0,720,512).size()).expandedTo(dialog.minimumSizeHint()))
			self.vboxlayout = QtGui.QVBoxLayout(dialog)
			self.vboxlayout.setObjectName("vboxlayout")
			self.outputText = QtGui.QTextEdit(dialog)
			font = QtGui.QFont()
			font.setFamily("Monospace")
			font.setPointSize(13)
			self.outputText.setFont(font)
			self.outputText.setAcceptDrops(False)
			self.vboxlayout.addWidget(self.outputText)
			DiffSyntaxHighlighter(self.outputText.document())
	app = QtGui.QApplication(sys.argv)
	dialog = SyntaxTestDialog(app.activeWindow())
	dialog.show()
	dialog.exec_()
