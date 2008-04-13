#!/usr/bin/env python
import os
import re
import time
from PyQt4 import QtGui

from ugit.observer import Observer
from ugit.qobserver import QObserver
from ugit import qtutils
from ugit.views import SearchView


class SearchEngine(object):
	def __init__(self, model):
		self.model = model
		self.parse = self.model.parse_rev_list
		self.init()
	def init(self):
		pass
	def get_rev_args(self):
		max = self.model.get_max_results()
		return { "max-count": max, "pretty": "oneline" }
	def get_common_args(self):
		return (self.model.get_input(),
			self.get_rev_args())
	def search(self):
		if not self.validate():
			return
		return self.get_results()
	def validate(self):
		return len(self.model.get_input()) > 1
	def get_results(self):
		pass

class RevisionSearch(SearchEngine):
	def get_results(self):
		input, args = self.get_common_args()
		expr = re.compile(input)
		revs = self.parse(self.model.rev_list(all=True, **args))
		return [ r for r in revs if expr.match(r[0]) ]

class RevisionRangeSearch(SearchEngine):
	def init(self):
		self.RE = re.compile(r'[^.]+\.\..+')
	def validate(self):
		return bool(self.RE.match(self.model.get_input()))
	def get_results(self):
		input, args = self.get_common_args()
		return self.parse(self.model.rev_list(input, **args))

class PathSearch(SearchEngine):
	def get_results(self):
		input, args = self.get_common_args()
		paths = ['--'] + input.split(':')
		return self.parse(self.model.rev_list(all=True,*paths,**args))

class MessageSearch(SearchEngine):
	def get_results(self):
		input, args = self.get_common_args()
		return self.parse(
			self.model.rev_list(grep=input, all=True, **args))

class DiffSearch(SearchEngine):
	def get_results(self):
		input, args = self.get_common_args()
		return self.parse(
			self.model.log('-S'+input, all=True, **args))

class DateRangeSearch(SearchEngine):
	def validate(self):
		return True
	def get_results(self):
		args = self.get_rev_args()
		return self.parse(
			self.model.rev_list(
				date='iso',
				after=self.model.get_start_date(),
				before=self.model.get_end_date(),
				all=True,
				**args))

# Modes for this controller.
# Note: names correspond to radio button names for convenience
REVISION_ID    = 'radio_revision'
REVISION_RANGE = 'radio_range'
PATH           = 'radio_path'
MESSAGE        = 'radio_message'
DIFF           = 'radio_diff'
DATE_RANGE     = 'radio_daterange'

# Each search type is handled by a distinct SearchEngine subclass
SEARCH_ENGINES = {
	REVISION_ID:    RevisionSearch,
	REVISION_RANGE: RevisionRangeSearch,
	PATH:           PathSearch,
	MESSAGE:        MessageSearch,
	DIFF:           DiffSearch,
	DATE_RANGE:     DateRangeSearch,
}

class SearchController(QObserver):
	def __init__(self, model, view, mode):
		QObserver.__init__(self, model, view)
		self.add_observables(
			'input',
			'max_results',
			'start_date',
			'end_date',
			)
		self.add_actions(
			input = self.search_callback,
			max_results = self.search_callback,
			start_date = self.search_callback,
			end_date = self.search_callback,
			)
		self.add_callbacks(
			# Standard buttons
			button_search = self.search_callback,
			button_browse = self.browse_callback,
			commit_list = self.display_callback,
			# Radio buttons trigger a search
			radio_revision = self.search_callback,
			radio_range = self.search_callback,
			radio_message = self.search_callback,
			radio_path = self.search_callback,
			radio_diff = self.search_callback,
			radio_daterange = self.search_callback,
			)
		self.set_mode(mode)
		self.update_fonts()

	def update_fonts(self):
		font = self.model.get_global_ugit_fontui()
		if font:
			qfont = QtGui.QFont()
			qfont.fromString(font)
			self.view.commit_list.setFont(qfont)
		font = self.model.get_global_ugit_fontdiff()
		if font:
			qfont = QtGui.QFont()
			qfont.fromString(font)
			self.view.commit_text.setFont(qfont)

	def set_mode(self, mode):
		radio = getattr(self.view, mode)
		radio.setChecked(True)

	def radio_to_mode(self, radio_button):
		return str(radio_button.objectName())

	def get_mode(self):
		for name in SEARCH_ENGINES:
			radiobutton = getattr(self.view, name)
			if radiobutton.isChecked():
				return name

	def search_callback(self, *args):
		engineclass = SEARCH_ENGINES.get(self.get_mode())
		if not engineclass:
			print ("mode: '%s' is currently unimplemented"
				% self.get_mode())
			return
		self.results = engineclass(self.model).search()
		if self.results:
			self.display_results()
		else:
			self.view.commit_list.clear()
			self.view.commit_text.setText('')

	def browse_callback(self):
		paths = QtGui.QFileDialog.getOpenFileNames(
				self.view,
				self.tr("Choose Path(s)"))
		if not paths:
			return
		filepaths = []
		lenprefix = len(os.getcwd()) + 1
		for path in map(lambda x: unicode(x), paths):
			if not path.startswith(os.getcwd()):
				continue
			filepaths.append(path[lenprefix:])
		input = ':'.join(filepaths)
		self.model.set_input('')
		self.set_mode(PATH)
		self.model.set_input(input)

	def display_results(self):
		commit_list = map(lambda x: x[1], self.results)
		self.model.set_commit_list(commit_list)
		qtutils.set_listwidget_strings(
			self.view.commit_list,
			commit_list)

	def display_callback(self, *args):
		widget = self.view.commit_list
		row, selected = qtutils.get_selected_row(widget)
		if not selected or len(self.results) < row:
			return
		revision = self.results[row][0]
		qtutils.set_clipboard(revision)
		diff = self.model.get_commit_diff(revision)
		self.view.commit_text.setText(diff)

def search_commits(model, mode, browse):
	def get_date(timespec):
		return '%04d-%02d-%02d' % time.localtime(timespec)[:3]

	model = model.clone()
	model.create(
		input='',
		max_results=500,
		start_date='',
		end_date='',
		commit_list=None,
		)
	view = SearchView(None)
	ctl = SearchController(model, view, mode)
	model.set_start_date(get_date(time.time()-(87640*7)))
	model.set_end_date(get_date(time.time()+87640))
	view.show()
	if browse:
		ctl.browse_callback()
