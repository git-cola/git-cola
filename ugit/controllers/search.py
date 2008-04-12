#!/usr/bin/env python

from ugit.qobserver import QObserver
from ugit.views import SearchView

def Search(parent, model, view):
	model = model.clone()
	view = SearchView(parent)
	ctl = SearchController(model, view)

class SearchController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self, model, view)
