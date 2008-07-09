#!/usr/bin/env python
from PyQt4.QtCore import Qt
from PyQt4.QtCore import QObject
from PyQt4.QtCore import SIGNAL
from PyQt4.QtCore import QDate
from PyQt4.QtGui import QDateEdit
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

from cola.observer import Observer

class QObserver(Observer, QObject):

    def __init__(self, model, view, *args, **kwargs):
        Observer.__init__(self, model)
        QObject.__init__(self)

        self.view = view

        self.__actions = {}
        self.__callbacks = {}
        self.__model_to_view = {}
        self.__view_to_model = {}
        self.__connected = []

        # Call the subclass's startup routine
        self.init(model, view, *args, **kwargs)

    def init(self, model, view, *args, **kwargs):
        pass

    def SLOT(self, *args):
        """Default slot to handle all Qt callbacks.
        This method delegates to callbacks from add_signals."""

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
            elif isinstance(widget, QDateEdit):
                fmt = Qt.ISODate
                value = str(widget.date().toString(fmt))
                model.set_param(model_param, value)
            elif isinstance(widget, QListWidget):
                pass
            else:
                print("SLOT(): Unknown widget:", sender, widget)

    def connect(self, obj, signal_str, *args):
        """Convenience function so that subclasses do not have
        to import QtCore.SIGNAL."""
        signal = signal_str
        if type(signal) is str:
            signal = SIGNAL(signal)
        return QObject.connect(obj, signal, *args)

    def add_signals(self, signal_str, *objects):
        """Connects object's signal to the QObserver."""
        for obj in objects:
            self.connect(obj, signal_str, self.SLOT)

    def add_callbacks(self, **callbacks):
        """Registers callbacks that are called in response to GUI events."""
        for sender, callback in callbacks.iteritems():
            self.__callbacks[sender] = callback
            self.autoconnect(getattr(self.view, sender))

    def add_observables(self, *params):
        """This method assumes that widgets and model params
        share the same name."""
        for param in params:
            self.model_to_view(param, getattr(self.view, param))

    def model_to_view(self, model_param, *widgets):
        """Binds model params to qt widgets(model->view)"""
        self.__model_to_view[model_param] = widgets
        for w in widgets:
            view = str(w.objectName())
            self.__view_to_model[view] = model_param
            self.__autoconnect(w)

    def autoconnect(self, *widgets):
        for w in widgets:
            self.__autoconnect(w)

    def __autoconnect(self, widget):
        """Automagically connects Qt widgets to QObserver.SLOT"""

        if widget in self.__connected: return
        self.__connected.append(widget)

        if isinstance(widget, QTextEdit):
            self.add_signals('textChanged()', widget)
        elif isinstance(widget, QLineEdit):
            self.add_signals('textChanged(const QString&)', widget)
        elif isinstance(widget, QListWidget):
            self.add_signals('itemSelectionChanged()', widget)
            self.add_signals('itemClicked(QListWidgetItem *)', widget)
            self.add_signals('itemDoubleClicked(QListWidgetItem*)', widget)
        elif isinstance(widget, QAbstractButton):
            self.add_signals('released()', widget)
        elif isinstance(widget, QAction):
            self.add_signals('triggered()', widget)
        elif isinstance(widget, QCheckBox):
            self.add_signals('stateChanged(int)', widget)
        elif isinstance(widget, QSpinBox):
            self.add_signals('valueChanged(int)', widget)
        elif isinstance(widget, QFontComboBox):
            self.add_signals('currentFontChanged(const QFont&)', widget)
        elif isinstance(widget, QSplitter):
            self.add_signals('splitterMoved(int,int)', widget)
        elif isinstance(widget, QDateEdit):
            self.add_signals('dateChanged(const QDate&)', widget)
        else:
            raise Exception('Asked to connect unknown widget:\n\t%s => %s'
                            % (type(widget), str(widget.objectName())))

    def add_actions(self, **kwargs):
        """Register view actions that are called in response to
        view changes.(view->model)"""
        for model_param, callback in kwargs.iteritems():
            if type(callback) is list:
                self.__actions[model_param] = callback
            else:
                self.__actions[model_param] = [callback]

    def subject_changed(self, param, value):
        """Sends a model param to the view(model->view)"""

        if param in self.__model_to_view:
            notify = self.model.get_notify()
            self.model.set_notify(False)
            for widget in self.__model_to_view[param]:
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
                    for i in value:
                        widget.addItem(i)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(value)
                elif isinstance(widget, QFontComboBox):
                    font = widget.currentFont()
                    font.fromString(value)
                elif isinstance(widget, QDateEdit):
                    if not value: return
                    fmt = Qt.ISODate
                    date = QDate.fromString(value, fmt)
                    if date:
                        widget.setDate(date)
                else:
                    print('subject_changed(): Unknown widget:',
                          str(widget.objectName()), widget, value)
            self.model.set_notify(notify)

        if param not in self.__actions:
            return
        widgets = []
        if param in self.__model_to_view:
            for widget in self.__model_to_view[param]:
                widgets.append(widget)
        # Call the model callback w/ the view's widgets as the args
        for action in self.__actions[param]:
            action(*widgets)

    def refresh_view(self, *params):
        if not params:
            params= tuple(self.__model_to_view.keys()
                         +self.__actions.keys())
        notified = []
        for param in params:
            if param not in notified:
                notified.append(param)
        self.model.notify_observers(*notified)
