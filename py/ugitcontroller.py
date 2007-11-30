from qobserver import QObserver

class GitController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self, model, view)
		model.add_observer(self)

		self.add_signals( 'textChanged()', view.commitText, )
		self.model_to_view(model, 'commitmsg', 'commitText')

		self.add_signals( 'pressed()',
				view.rescanButton, view.pushButton,
				view.signOffButton,)

		self.add_callbacks(model, {
				'rescanButton':  self.rescan_callback,
				'signOffButton': self.signoff_callback,
				})

	def rescan_callback(self, *args):
		print self.model

	def signoff_callback(self, model, *args):
		msg = model.get_commitmsg()
		signoff = 'Signed-off by: %s <%s>' % (
				model.get_name(), model.get_email() )

		if signoff not in msg:
			model.set_commitmsg( '%s\n\n%s' % ( msg, signoff ) )
