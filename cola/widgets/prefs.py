import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import qtutils
from cola import gitcfg
from cola.i18n import N_
from cola.models import prefs
from cola.models.prefs import PreferencesModel
from cola.models.prefs import SetConfig
from cola.models.prefs import FONTDIFF
from cola.qtutils import diff_font
from cola.widgets import defs
from cola.widgets import standard


def preferences(model=None, parent=None):
    if model is None:
        model = PreferencesModel()
    view = PreferencesView(model, parent=parent)
    view.show()
    view.raise_()
    return view


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
        def runner(value):
            cmds.do(SetConfig, self.model, self.source, config, value)
        return runner

    def _bool_config_changed(self, config):
        def runner(value):
            cmds.do(SetConfig, self.model, self.source, config, value)
        return runner

    def _text_config_changed(self, config):
        def runner():
            value = unicode(self.sender().text())
            cmds.do(SetConfig, self.model, self.source, config, value)
        return runner

    def update_from_config(self):
        if self.source == 'user':
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

        self.display_untracked = QtGui.QCheckBox()
        self.display_untracked.setChecked(True)

        self.add_row(N_('User Name'), self.name)
        self.add_row(N_('Email Address'), self.email)
        self.add_row(N_('Merge Verbosity'), self.merge_verbosity)
        self.add_row(N_('Number of Diff Context Lines'), self.diff_context)
        self.add_row(N_('Summarize Merge Commits'), self.merge_summary)
        self.add_row(N_('Show Diffstat After Merge'), self.merge_diffstat)
        self.add_row(N_('Display Untracked Files'), self.display_untracked)

        self.set_config({
            prefs.DIFFCONTEXT: (self.diff_context, 5),
            prefs.DISPLAY_UNTRACKED: (self.display_untracked, True),
            prefs.USER_NAME: (self.name, ''),
            prefs.USER_EMAIL: (self.email, ''),
            prefs.MERGE_DIFFSTAT: (self.merge_diffstat, True),
            prefs.MERGE_SUMMARY: (self.merge_summary, True),
            prefs.MERGE_VERBOSITY: (self.merge_verbosity, 5),
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

        self.tabwidth = QtGui.QSpinBox()
        self.tabwidth.setWrapping(True)
        self.tabwidth.setMaximum(42)

        self.textwidth = QtGui.QSpinBox()
        self.textwidth.setWrapping(True)
        self.textwidth.setMaximum(150)

        self.linebreak = QtGui.QCheckBox()
        self.editor = QtGui.QLineEdit()
        self.historybrowser = QtGui.QLineEdit()
        self.difftool = QtGui.QLineEdit()
        self.mergetool = QtGui.QLineEdit()
        self.keep_merge_backups = QtGui.QCheckBox()
        self.save_gui_settings = QtGui.QCheckBox()

        self.add_row(N_('Fixed-Width Font'), self.fixed_font)
        self.add_row(N_('Font Size'), self.font_size)
        self.add_row(N_('Tab Width'), self.tabwidth)
        self.add_row(N_('Text Width'), self.textwidth)
        self.add_row(N_('Auto-Wrap Lines'), self.linebreak)
        self.add_row(N_('Editor'), self.editor)
        self.add_row(N_('History Browser'), self.historybrowser)
        self.add_row(N_('Diff Tool'), self.difftool)
        self.add_row(N_('Merge Tool'), self.mergetool)
        self.add_row(N_('Keep *.orig Merge Backups'), self.keep_merge_backups)
        self.add_row(N_('Save GUI Settings'), self.save_gui_settings)

        self.set_config({
            prefs.SAVEWINDOWSETTINGS: (self.save_gui_settings, True),
            prefs.TABWIDTH: (self.tabwidth, 8),
            prefs.TEXTWIDTH: (self.textwidth, 72),
            prefs.LINEBREAK: (self.linebreak, True),
            prefs.DIFFTOOL: (self.difftool, 'xxdiff'),
            prefs.EDITOR: (self.editor, os.getenv('VISUAL', 'gvim')),
            prefs.HISTORY_BROWSER: (self.historybrowser, 'gitk'),
            prefs.MERGE_KEEPBACKUP: (self.keep_merge_backups, True),
            prefs.MERGETOOL: (self.mergetool, 'xxdiff'),
        })

        self.connect(self.fixed_font, SIGNAL('currentFontChanged(const QFont &)'),
                     self.current_font_changed)

        self.connect(self.font_size, SIGNAL('valueChanged(int)'),
                     self.font_size_changed)

    def update_from_config(self):
        FormWidget.update_from_config(self)

        block = self.fixed_font.blockSignals(True)
        font = diff_font()
        self.fixed_font.setCurrentFont(font)
        self.fixed_font.blockSignals(block)

        block = self.font_size.blockSignals(True)
        font_size = font.pointSize()
        self.font_size.setValue(font_size)
        self.font_size.blockSignals(block)

    def font_size_changed(self, size):
        font = self.fixed_font.currentFont()
        font.setPointSize(size)
        cmds.do(SetConfig, self.model,
                'user', prefs.FONTDIFF, unicode(font.toString()))

    def current_font_changed(self, font):
        cmds.do(SetConfig, self.model,
                'user', prefs.FONTDIFF, unicode(font.toString()))


class PreferencesView(standard.Dialog):
    def __init__(self, model, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.setWindowTitle(N_('Preferences'))
        self.setWindowModality(QtCore.Qt.WindowModal)

        self.resize(600, 360)

        self._tabbar = QtGui.QTabBar()
        self._tabbar.setDrawBase(False)
        self._tabbar.addTab(N_('All Repositories'))
        self._tabbar.addTab(N_('Current Repository'))
        self._tabbar.addTab(N_('Settings'))

        self._user_form = RepoFormWidget(model, self, source='user')
        self._repo_form = RepoFormWidget(model, self, source='repo')
        self._options_form = SettingsFormWidget(model, self)

        self._stackedwidget = QtGui.QStackedWidget()
        self._stackedwidget.addWidget(self._user_form)
        self._stackedwidget.addWidget(self._repo_form)
        self._stackedwidget.addWidget(self._options_form)

        self.close_button = QtGui.QPushButton(self)
        self.close_button.setText(N_('Close'))
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

        qtutils.connect_button(self.close_button, self.accept)
        qtutils.add_close_action(self)

        self.update_widget(0)

    def update_widget(self, idx):
        widget = self._stackedwidget.widget(idx)
        widget.update_from_config()
