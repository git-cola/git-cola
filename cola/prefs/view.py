import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import qtutils
from cola import gitcfg
from cola.views import standard
from cola.qtutils import relay_signal
from cola.utils import is_darwin
from cola.widgets import defs


class FormWidget(QtGui.QWidget):
    def __init__(self, model, parent, source='user'):
        QtGui.QWidget.__init__(self, parent)
        self.model = model
        self.config_to_widget = {}
        self.widget_to_config = {}
        self.source = source
        self.config = gitcfg.instance()
        self.defaults = {}
        self.setLayout(QtGui.QFormLayout())

    def add_row(self, label, widget):
        self.layout().addRow(label, widget)

    def set_config(self, config_dict):
        self.config_to_widget.update(config_dict)
        for config, (widget, default) in config_dict.items():
            self.widget_to_config[config] = widget
            self.defaults[config] = default
            self.connect_widget_to_config(widget, config)

    def connect_widget_to_config(self, widget, config):
        if isinstance(widget, QtGui.QSpinBox):
            widget.connect(widget, SIGNAL('valueChanged(int)'),
                           self._int_config_changed(config))

        elif isinstance(widget, QtGui.QCheckBox):
            widget.connect(widget, SIGNAL('toggled(bool)'),
                           self._bool_config_changed(config))

        elif isinstance(widget, QtGui.QLineEdit):
            widget.connect(widget, SIGNAL('editingFinished()'),
                           self._text_config_changed(config))
            widget.connect(widget, SIGNAL('returnPressed()'),
                           self._text_config_changed(config))

    def _int_config_changed(self, config):
        def emitter(value):
            self.emit(SIGNAL(self.model.message_set_config),
                      self.source, config, value)
        return emitter

    def _bool_config_changed(self, config):
        def emitter(value):
            self.emit(SIGNAL(self.model.message_set_config),
                      self.source, config, value)
        return emitter

    def _text_config_changed(self, config):
        def emitter():
            value = unicode(self.sender().text())
            self.emit(SIGNAL(self.model.message_set_config),
                      self.source, config, value)
        return emitter

    def update_from_config(self):
        if self.source == 'repo':
            getter = self.config.get_repo
        elif self.source == 'user':
            getter = self.config.get_user
        else:
            getter = self.config.get

        for config, widget in self.widget_to_config.items():
            value = getter(config)
            if value is None:
                value = self.defaults[config]
            self.set_widget_value(widget, value)

    def set_widget_value(self, widget, value):
        widget.blockSignals(True)
        if isinstance(widget, QtGui.QSpinBox):
            widget.setValue(value)
        elif isinstance(widget, QtGui.QLineEdit):
            widget.setText(value)
        elif isinstance(widget, QtGui.QCheckBox):
            widget.setChecked(value)
        widget.blockSignals(False)


class RepoFormWidget(FormWidget):
    def __init__(self, model, parent, source):
        FormWidget.__init__(self, model, parent, source=source)

        self.name = QtGui.QLineEdit()
        self.email = QtGui.QLineEdit()
        self.merge_verbosity = QtGui.QSpinBox()
        self.merge_verbosity.setMinimum(0)
        self.merge_verbosity.setMaximum(5)
        self.merge_verbosity.setProperty('value', QtCore.QVariant(5))

        self.diff_context = QtGui.QSpinBox()
        self.diff_context.setMinimum(2)
        self.diff_context.setMaximum(99)
        self.diff_context.setProperty('value', QtCore.QVariant(5))

        self.merge_summary = QtGui.QCheckBox()
        self.merge_summary.setChecked(True)

        self.merge_diffstat = QtGui.QCheckBox()
        self.merge_diffstat.setChecked(True)

        self.add_row('User Name', self.name)
        self.add_row('Email Address', self.email)
        self.add_row('Merge Verbosity', self.merge_verbosity)
        self.add_row('Number of Diff Context Lines', self.diff_context)
        self.add_row('Summarize Merge Commits', self.merge_summary)
        self.add_row('Show Diffstat After Merge', self.merge_diffstat)

        self.set_config({
            'gui.diffcontext': (self.diff_context, 5),
            'user.name': (self.name, ''),
            'user.email': (self.email, ''),
            'merge.diffstat': (self.merge_diffstat, True),
            'merge.summary': (self.merge_summary, True),
            'merge.verbosity': (self.merge_verbosity, 5),
        })


class SettingsFormWidget(FormWidget):
    def __init__(self, model, parent):
        FormWidget.__init__(self, model, parent)

        self.fixed_font = QtGui.QFontComboBox()
        self.fixed_font.setFontFilters(QtGui.QFontComboBox.MonospacedFonts)

        self.font_size = QtGui.QSpinBox()
        self.font_size.setMinimum(8)
        self.font_size.setProperty('value', QtCore.QVariant(12))
        self._font_str = None

        self.tab_width = QtGui.QSpinBox()
        self.tab_width.setWrapping(True)
        self.tab_width.setMaximum(42)

        self.editor = QtGui.QLineEdit()
        self.historybrowser = QtGui.QLineEdit()
        self.difftool = QtGui.QLineEdit()
        self.mergetool = QtGui.QLineEdit()
        self.keep_merge_backups = QtGui.QCheckBox()
        self.save_gui_settings = QtGui.QCheckBox()

        self.add_row('Fixed-Width Font', self.fixed_font)
        self.add_row('Font Size', self.font_size)
        self.add_row('Tab Width', self.tab_width)
        self.add_row('Editor', self.editor)
        self.add_row('History Browser', self.historybrowser)
        self.add_row('Diff Tool', self.difftool)
        self.add_row('Merge Tool', self.mergetool)
        self.add_row('Keep *.orig Merge Backups', self.keep_merge_backups)
        self.add_row('Save GUI Settings', self.save_gui_settings)

        self.set_config({
            'cola.savewindowsettings': (self.save_gui_settings, True),
            'cola.tabwidth': (self.tab_width, 8),
            'diff.tool': (self.difftool, 'xxdiff'),
            'gui.editor': (self.editor, os.getenv('VISUAL', 'gvim')),
            'gui.historybrowser': (self.historybrowser, 'gitk'),
            'merge.keepbackup': (self.keep_merge_backups, True),
            'merge.tool': (self.mergetool, 'xxdiff'),
        })

        self.connect(self.fixed_font, SIGNAL('currentFontChanged(const QFont &)'),
                     self.current_font_changed)

        self.connect(self.font_size, SIGNAL('valueChanged(int)'),
                     self.font_size_changed)

    def update_from_config(self):
        FormWidget.update_from_config(self)
        self.fixed_font.blockSignals(True)
        self.font_size.blockSignals(True)

        font = diff_font()
        font_size = font.pointSize()

        self.fixed_font.setCurrentFont(font)
        self.font_size.setValue(font_size)

        self.fixed_font.blockSignals(False)
        self.font_size.blockSignals(False)

    def font_size_changed(self, size):
        font = self.fixed_font.currentFont()
        font.setPointSize(size)
        self.emit(SIGNAL(self.model.message_set_config),
                  'user', 'cola.fontdiff', unicode(font.toString()))

    def current_font_changed(self, font):
        self.emit(SIGNAL(self.model.message_set_config),
                  'user', 'cola.fontdiff', unicode(font.toString()))


class PreferencesView(standard.Dialog):
    def __init__(self, model, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.setWindowTitle(self.tr('Preferences'))

        self.resize(600, 360)

        self._tabbar = QtGui.QTabBar()
        self._tabbar.setDrawBase(False)
        self._tabbar.addTab('All Repositories')
        self._tabbar.addTab('Current Repository')
        self._tabbar.addTab('Settings')

        self._user_form = RepoFormWidget(model, self, source='user')
        self._repo_form = RepoFormWidget(model, self, source='all')
        self._options_form = SettingsFormWidget(model, self)

        relay_signal(self, self._user_form, SIGNAL(model.message_set_config))
        relay_signal(self, self._repo_form, SIGNAL(model.message_set_config))
        relay_signal(self, self._options_form, SIGNAL(model.message_set_config))

        self._stackedwidget = QtGui.QStackedWidget()
        self._stackedwidget.addWidget(self._user_form)
        self._stackedwidget.addWidget(self._repo_form)
        self._stackedwidget.addWidget(self._options_form)

        self.close_button = QtGui.QPushButton(self)
        self.close_button.setText(qtutils.tr('Close'))
        self.close_button.setIcon(qtutils.close_icon())

        self._button_layt = QtGui.QHBoxLayout()
        self._button_layt.setMargin(0)
        self._button_layt.setSpacing(defs.spacing)
        self._button_layt.addStretch()
        self._button_layt.addWidget(self.close_button)

        self._layt = QtGui.QVBoxLayout()
        self._layt.setMargin(defs.margin)
        self._layt.setSpacing(defs.spacing)
        self._layt.addWidget(self._tabbar)
        self._layt.addWidget(self._stackedwidget)
        self._layt.addLayout(self._button_layt)
        self.setLayout(self._layt)

        self.connect(self._tabbar, SIGNAL('currentChanged(int)'),
                     self._stackedwidget.setCurrentIndex)

        self.connect(self._stackedwidget, SIGNAL('currentChanged(int)'),
                     self.update_widget)

        self.connect(self.close_button, SIGNAL('clicked()'), self.accept)

        qtutils.add_close_action(self)

        self.update_widget(0)

    def update_widget(self, idx):
        widget = self._stackedwidget.widget(idx)
        widget.update_from_config()


def tab_width():
    return gitcfg.instance().get('cola.tabwidth', 8)


def diff_font_str():
    font_str = gitcfg.instance().get('cola.fontdiff')
    if font_str is None:
        font = qtutils.default_monospace_font()
        font_str = unicode(font.toString())
    return font_str


def diff_font():
    font_str = diff_font_str()
    font = QtGui.QFont()
    font.fromString(font_str)
    return font


if __name__ == "__main__":
    import sys
    from cola.prefs import preferences

    app = QtGui.QApplication(sys.argv)
    preferences()
    sys.exit(app.exec_())
