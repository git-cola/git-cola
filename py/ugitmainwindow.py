import os

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import SIGNAL

from qobserver import QObserver
from ugitWindow import Ui_ugitWindow

class ugitMainWindow(QObserver, Ui_ugitWindow, QtGui.QMainWindow):
	def __init__(self, parent=None):
		QObserver.__init__(self)
		QtGui.QMainWindow.__init__(self, parent)
		Ui_ugitWindow.__init__(self)
		self.setupUi(self)
	

	def setupUi(self, window):
		Ui_ugitWindow.setupUi(self, window)
		self.setup_signals( SIGNAL('pressed()'),
				self.rescanButton,
				self.pushButton,
				self.signOffButton,
				)
		
		self.setup_signals( SIGNAL('textChanged()'),
				self.commitText,
				)

	def rescan_callback(self, *args):
		print self.model

	def setup_notifications(self, model):
		self.model = model
		self.setup_callbacks(model, {
				'commitText':  self.committext_callback,
				'rescanButton': self.rescan_callback,
				'signOffButton': self.signoff_callback,
				})
		
		self.setup_widgets(model, 'commitmsg', 'commitText')

		model.add_observer(self)
	
	def committext_callback(self, model, *args):
		# Accessing the model attributes directly avoids
		# calling notify_observers()
		model.commitmsg = str(self.commitText.toPlainText())


	def signoff_callback(self, model, *args):
		model.set_commitmsg('%s\n\nSigned-off by: %s <%s>' % (
				model.get_commitmsg(),
				model.get_name(),
				model.get_email() ))
	
