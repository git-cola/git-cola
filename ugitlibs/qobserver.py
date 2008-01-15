#!/usr/bin/env python
from PyQt4.QtCore import QObject
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QSpinBox
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QTextEdit
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QListWidget
from PyQt4.QtGui import QCheckBox
from PyQt4.QtGui import QFontComboBox
from PyQt4.QtGui import QAbstractButton
from PyQt4.QtGui import QSplitter
from PyQt4.QtGui import QAction

from observer import Observer

class QObserver(Observer, QObject):

	def __init__(self, model, view):
		Observer.__init__(self, model)
		QObject.__init__(self)

		self.view = view

		self.__actions = {}
		self.__callbacks = {}
		self.__model_to_view = {}
		self.__view_to_model = {}
		self.__connected = []

	def SLOT(self, *args):
		'''Default slot to handle all Qt callbacks.
		This method delegates to callbacks from add_signals.'''

		widget = self.sender()
		sender = str(widget.objectName())

		if sender in self.__callbacks:
			self.__callbacks[sender](*args)

		elif sender in self.__view_to_model:
			model = self.model
			model_param = self.__view_to_model[sender]
			if isinstance(widget, QTextEdit):
				value = unicode(widget.toPlainText())
				model.set_param(model_param, value,
						notify=False)
			elif isinstance(widget, QLineEdit):
				value = unicode(widget.text())
				model.set_param(model_param, value)
			elif isinstance(widget, QCheckBox):
				model.set_param(model_param, widget.isChecked())
			elif isinstance(widget, QSpinBox):
				model.set_param(model_param, widget.value())
			elif isinstance(widget, QFontComboBox):
				value = unicode(widget.currentFont().toString())
				model.set_param(model_param, value)
			else:
				print("SLOT(): Unknown widget:", sender, widget)

	def connect(self, obj, signal_str, *args):
		'''Convenience function so that subclasses do not have
		to import QtCore.SIGNAL.'''
		signal = signal_str
		if type(signal) is str:
			signal = SIGNAL(signal)
		return QObject.connect(obj, signal, *args)

	def add_signals(self, signal_str, *objects):
		'''Connects object's signal to the QObserver.'''
		for obj in objects:
			self.connect(obj, signal_str, self.SLOT)

	def add_callbacks(self, **callbacks):
		'''Registers callbacks that are called in response to GUI events.'''
		for sender, callback in callbacks.iteritems():
			self.__callbacks[sender] = callback
			self.autoconnect(getattr(self.view, sender))

	def model_to_view(self, model_param, *widget_names):
		'''Binds model params to qt widgets(model->view)'''
		self.__model_to_view[model_param] = widget_names
		for widget_name in widget_names:
			self.__view_to_model[widget_name] = model_param
			self.__autoconnect(getattr(self.view, widget_name))

	def __autoconnect(self, widget):
		'''Automatically connects widgets registered using
		model_to_view to QObserver.SLOT'''

		if widget in self.__connected: return
		self.__connected.append(widget)

		if isinstance(widget, QTextEdit):
			self.add_signals(
				'textChanged()', widget)
		elif isinstance(widget, QLineEdit):
			self.add_signals(
				'textChanged(const QString&)', widget)
		elif isinstance(widget, QListWidget):
			self.add_signals(
				'itemSelectionChanged()', widget)
			self.add_signals(
				'itemClicked(QListWidgetItem *)', widget)
			self.add_signals(
				'itemDoubleClicked(QListWidgetItem*)', widget)
		elif isinstance(widget, QAbstractButton):
			self.add_signals(
				'released()', widget)
		elif isinstance(widget, QAction):
			self.add_signals(
				'triggered()', widget)
		elif isinstance(widget, QCheckBox):
			self.add_signals(
				'stateChanged(int)', widget)
		elif isinstance(widget, QSpinBox):
			self.add_signals(
				'valueChanged(int)', widget)
		elif isinstance(widget, QFontComboBox):
			self.add_signals(
				'currentFontChanged(const QFont&)', widget)
		elif isinstance(widget, QSplitter):
			self.add_signals(
				'splitterMoved(int,int)', widget)
		else:
			raise Exception(
				"Asked to connect unknown widget:\n\t"
				"%s => %s" %( type(widget),
						str(widget.objectName()) ))

	def autoconnect(self, *widgets):
		for widget in widgets:
			self.__autoconnect(widget)

	def add_actions(self, model_param, callback):
		'''Register view actions that are called in response to
		view changes.(view->model)'''
		self.__actions[model_param] = callback

	def subject_changed(self, param, value):
		'''Sends a model param to the view(model->view)'''

		if param in self.__model_to_view:
			notify = self.model.get_notify()
			self.model.set_notify(False)
			for widget_name in self.__model_to_view[param]:
				widget = getattr(self.view, widget_name)
				if isinstance(widget, QSpinBox):
					widget.setValue(value)
				elif isinstance(widget, QPixmap):
					widget.load(value)
				elif isinstance(widget, QTextEdit):
					widget.setText(value)
				elif isinstance(widget, QLineEdit):
					widget.setText(value)
				elif isinstance(widget, QListWidget):
					widget.clear()
					for i in value: widget.addItem(i)
				elif isinstance(widget, QCheckBox):
					widget.setChecked(value)
				elif isinstance(widget, QFontComboBox):
					font = widget.currentFont()
					font.fromString(value)
				else:
					print('subject_changed(): '
						+ 'Unknown widget:',
						widget_name, widget, value)
			self.model.set_notify(notify)

		if param not in self.__actions: return
		widgets = []
		if param in self.__model_to_view:
			for widget_name in self.__model_to_view[param]:
				widget = getattr(self.view, widget_name)
				widgets.append(widget)
		# Call the model callback w/ the view's widgets as the args
		self.__actions[param](*widgets)

	def refresh_view(self):
		params= list(self.__model_to_view.keys()
				+ self.__actions.keys())
		notified = []
		for param in params:
			if param not in notified:
				notified.append(param)
		self.model.notify_observers(*notified)
