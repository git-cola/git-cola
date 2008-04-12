#!/usr/bin/env python
import re
from PyQt4 import QtGui

from ugit.observer import Observer
from ugit.qobserver import QObserver
from ugit import qtutils
from ugit.views import SearchView

REVISION_ID       = 'Search Revision'
REVISION_RANGE    = 'Search Revision Range'
COMMIT_PATHS      = 'Search Paths'
COMMIT_MESSAGES   = 'Search Messages'
COMMIT_DIFFS      = 'Search Diffs'
DATE              = 'Search Date'
DATE_RANGE        = 'Search Date Range'

class SearchEngine(Observer):
	def __init__(self, model):
		self.model = model
		self.init()
	def init(self):
		pass
	def validate(self, input):
		return False
	def get_results(self, text):
		pass
	def search(self):
		input = self.model.get_input()
		if not self.validate(input):
			return
		return self.get_results(input)

class RevisionRangeSearchEngine(SearchEngine):
	def init(self):
		self.RE = re.compile(r'\w+\.\.\w+')
	def validate(self, input):
		return bool(self.RE.match(input))
	def get_results(self, input):
		return self.model.parsed_rev_range(input)
	

ENGINES = {
	REVISION_ID:    SearchEngine,
	REVISION_RANGE: RevisionRangeSearchEngine,
}

class SearchController(QObserver):
	def __init__(self, model, view, mode):
		QObserver.__init__(self, model, view)
		self.add_actions(input = self.search)
		self.add_callbacks(
			button_search = self.search,
			commit_list = self.display_commit
			)
		self.add_observables('input')
		self.radio_buttons = {
			REVISION_RANGE: self.view.radio_range,
		}
		button = self.get_radio_button(mode)
		button.setChecked(True)

		self.update_fonts()

	def update_fonts(self):
		font = self.model.get_global_ugit_fontdiff()
		if not font:
			return
		qfont = QtGui.QFont()
		qfont.fromString(font)
		self.view.commit_text.setFont(qfont)

	def get_radio_button(self, mode):
		return self.radio_buttons.get(mode)
	
	def radio_to_mode(self, radio_button):
		for mode, radio in self.radio_buttons.iteritems():
			if radio == radio_button:
				return mode
	
	def get_mode(self):
		for name, attr in self.view.__dict__.iteritems():
			if isinstance(attr, QtGui.QRadioButton):
				if attr.isChecked():
					return self.radio_to_mode(attr)

	def search(self, *args):
		engineclass = ENGINES.get(self.get_mode())
		if not engineclass:
			print ("mode: '%s' is currently unimplemented"
				% self.get_mode())
			return
		self.results = engineclass(self.model).search()
		if self.results:
			self.display_results()

	def display_results(self):
		commit_list = map(lambda x: x[1], self.results)
		self.model.set_commit_list(commit_list)
		qtutils.set_listwidget_strings(
			self.view.commit_list,
			commit_list)

	def display_commit(self, *args):
		widget = self.view.commit_list
		row, selected = qtutils.get_selected_row(widget)
		if not selected or len(self.results) < row:
			return
		revision = self.results[row][0]
		qtutils.set_clipboard(revision)
		diff = self.model.get_commit_diff(revision)
		self.view.commit_text.setText(diff)

def search_commits(model, parent, mode):
	model = model.clone()
	model.create(input='', commit_list=[])
	view = SearchView(parent)
	ctl = SearchController(model, view, mode)
	view.show()
