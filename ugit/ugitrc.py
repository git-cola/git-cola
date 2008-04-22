#!/usr/bin/env python
HAS_SIMPLEJSON = False
try:
	import simplejson
	HAS_SIMPLEJSON = True
except ImportError:
	pass

import os
import user
from ugit.model import Model

class SettingsModel(Model):

	def init(self):
		self.create( bookmarks = [] )
		if not HAS_SIMPLEJSON:
			return
		ugitrc = self.path()
		if os.path.exists(ugitrc):
			self.load(ugitrc)

	def path(self):
		return os.path.join(user.home, '.ugitrc')
	
	def save_all_settings(self):
		if not HAS_SIMPLEJSON:
			return
		self.save(self.path())
