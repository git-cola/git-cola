#!/usr/bin/python
import re
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QSyntaxHighlighter
from PyQt4.QtGui import QTextCharFormat

class GenericSyntaxHighligher(QSyntaxHighlighter):

	def __init__(self, doc):
		QSyntaxHighlighter.__init__(self, doc)
		self.__rules = []

	FINAL_STR = '__FINAL__:'
	def final(self, pattern=''):
		'''Denotes that a pattern is the final pattern that should
		be matched.  If this pattern matches no other formats
		will be applied, even if they would have matched.'''
		return GenericSyntaxHighligher.FINAL_STR + pattern

	def create_rules(self, *rules):
		if len(rules) % 2:
			raise Exception("create_rules requires an even "
					"number of arguments.")
		for idx, rule in enumerate(rules):
			if idx % 2: continue
			formats = rules[idx+1]
			terminal = rule.startswith(self.final())
			if terminal:
				rule = rule[len(self.final()):]
			regex = re.compile(rule)
			self.__rules.append((regex, formats, terminal,))

	def get_formats(self, line):
		matched = []
		for regex, fmts, terminal in self.__rules:
			match = regex.match(line)
			if match:
				matched.append([match, fmts])
				if terminal: return matched
		return matched

	def mkformat(self, fg, bg=None, bold=False):
		format = QTextCharFormat()
		if bold: format.setFontWeight(QFont.Bold)
		format.setForeground(fg)
		if bg: format.setBackground(bg)
		return format

	def highlightBlock(self, qstr):
		ascii = qstr.toAscii().data()
		if not ascii: return
		formats = self.get_formats(ascii)
		if not formats: return
		for match, fmts in formats:
			start = match.start()
			end = match.end()
			groups = match.groups()

			# No groups in the regex, assume this is a single rule
			# that spans the entire line
			if not groups:
				self.setFormat(0, len(ascii), fmts)
				continue

			# Groups exist, rule is a tuple corresponding to group
			for grpidx, group in enumerate(groups):
				# allow empty matches
				if not group: continue
				# allow None as a no-op format
				length = len(group)
				if fmts[grpidx]:
					self.setFormat(start, start+length,
							fmts[grpidx])
				start += length

class DiffSyntaxHighlighter(GenericSyntaxHighligher):
	def __init__(self, doc,whitespace=True):
		GenericSyntaxHighligher.__init__(self,doc)

		diffstat = self.mkformat(Qt.blue, bold=True)
		diffstat_add = self.mkformat(Qt.darkGreen, bold=True)
		diffstat_remove = self.mkformat(Qt.red, bold=True)

		diff_begin = self.mkformat(Qt.darkCyan, bold=True)
		diff_head = self.mkformat(Qt.darkYellow)
		diff_add = self.mkformat(Qt.darkGreen)
		diff_remove = self.mkformat(Qt.red)

		if whitespace:
			bad_ws = self.mkformat(Qt.black, Qt.red)

		# We specify the whitespace rule last so that it is
		# applied after the diff addition/removal rules.
		# The rules for the header
		self.create_rules(
			self.final('^@@|^\+\+\+|^---'), diff_begin,
			self.final('^diff --git'), diff_head,
			self.final('^index \S+\.\.\S+'), diff_head,
			self.final('^new file mode'), diff_head,
			self.final('^\+'), diff_add,
			self.final('^-'), diff_remove,

			'(.+\|.+?)(\d+)(.+?)([\+]*?)([-]*?)$',
			(None, diffstat, None, diffstat_add, diffstat_remove),

			'(\s+\d+ files changed[^\d]*)'
			'(:?\d+ insertions[^\d]*)'
			'(:?\d+ deletions.*)$',
			(diffstat, diffstat_add, diffstat_remove),
			)
		if whitespace:
			self.create_rules('(.+)(\s+)$', (None, bad_ws,))

class LogSyntaxHighlighter(GenericSyntaxHighligher):
	def __init__(self, doc):
		GenericSyntaxHighligher.__init__(self,doc)

		black = self.mkformat(Qt.black, bold=True)
		blue = self.mkformat(Qt.blue, bold=True)
		dark_cyan = self.mkformat(Qt.darkCyan, bold=True)

		self.create_rules(
			self.final('^\w{3}\W+\w{3}\W+\d+\W+'
					'[:0-9]+\W+\d{4}$'),
			dark_cyan,
			'^([^:]+:)(.*)$',
			(blue, black),
			)

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
			self.output_text = QtGui.QTextEdit(dialog)
			font = QtGui.QFont()
			font.setFamily("Monospace")
			font.setPointSize(13)
			self.output_text.setFont(font)
			self.output_text.setAcceptDrops(False)
			self.vboxlayout.addWidget(self.output_text)
			DiffSyntaxHighlighter(self.output_text.document())
	app = QtGui.QApplication(sys.argv)
	dialog = SyntaxTestDialog(app.activeWindow())
	dialog.show()
	dialog.exec_()
