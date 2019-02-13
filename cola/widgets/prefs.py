from __future__ import division, absolute_import, unicode_literals
import os

from qtpy import QtCore
from qtpy import QtWidgets

from . import defs
from . import standard
from .. import cmds
from .. import hidpi
from .. import qtutils
from .. import themes
from ..i18n import N_
from ..models import prefs
from ..models.prefs import Defaults


def preferences(context, model=None, parent=None):
    if model is None:
        model = prefs.PreferencesModel(context)
    view = PreferencesView(context, model, parent=parent)
    view.show()
    view.raise_()
    return view


class FormWidget(QtWidgets.QWidget):

    def __init__(self, context, model, parent, source='user'):
        QtWidgets.QWidget.__init__(self, parent)
        self.context = context
        self.cfg = context.cfg
        self.model = model
        self.config_to_widget = {}
        self.widget_to_config = {}
        self.source = source
        self.defaults = {}
        self.setLayout(QtWidgets.QFormLayout())

    def add_row(self, label, widget):
        self.layout().addRow(label, widget)

    def set_config(self, config_dict):
        self.config_to_widget.update(config_dict)
        for config, (widget, default) in config_dict.items():
            self.widget_to_config[config] = widget
            self.defaults[config] = default
            self.connect_widget_to_config(widget, config)

    def connect_widget_to_config(self, widget, config):
        if isinstance(widget, QtWidgets.QSpinBox):
            widget.valueChanged.connect(self._int_config_changed(config))

        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.toggled.connect(self._bool_config_changed(config))

        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.editingFinished.connect(
                self._text_config_changed(config, widget))
            widget.returnPressed.connect(
                self._text_config_changed(config, widget))

        elif isinstance(widget, QtWidgets.QComboBox):
            widget.currentIndexChanged.connect(
                self._item_config_changed(config, widget))

    def _int_config_changed(self, config):
        def runner(value):
            cmds.do(prefs.SetConfig, self.model, self.source, config, value)
        return runner

    def _bool_config_changed(self, config):
        def runner(value):
            cmds.do(prefs.SetConfig, self.model, self.source, config, value)
        return runner

    def _text_config_changed(self, config, widget):
        def runner():
            value = widget.text()
            cmds.do(prefs.SetConfig, self.model, self.source, config, value)
        return runner

    def _item_config_changed(self, config, widget):
        def runner():
            value = widget.currentData()
            cmds.do(prefs.SetConfig, self.model, self.source, config, value)
        return runner

    def update_from_config(self):
        if self.source == 'user':
            getter = self.cfg.get_user_or_system
        else:
            getter = self.cfg.get

        for config, widget in self.widget_to_config.items():
            value = getter(config)
            if value is None:
                value = self.defaults[config]
            set_widget_value(widget, value)


def set_widget_value(widget, value):
    widget.blockSignals(True)
    if isinstance(widget, QtWidgets.QSpinBox):
        widget.setValue(value)
    elif isinstance(widget, QtWidgets.QLineEdit):
        widget.setText(value)
    elif isinstance(widget, QtWidgets.QCheckBox):
        widget.setChecked(value)
    elif isinstance(widget, QtWidgets.QComboBox):
        index = widget.findData(value)
        widget.setCurrentIndex(index)
    widget.blockSignals(False)


class RepoFormWidget(FormWidget):

    def __init__(self, context, model, parent, source):
        FormWidget.__init__(self, context, model, parent, source=source)
        self.name = QtWidgets.QLineEdit()
        self.email = QtWidgets.QLineEdit()

        self.diff_context = standard.SpinBox(value=5, mini=2, maxi=9995)
        self.merge_verbosity = standard.SpinBox(value=5, maxi=5)
        self.merge_summary = qtutils.checkbox(checked=True)
        self.merge_diffstat = qtutils.checkbox(checked=True)
        self.display_untracked = qtutils.checkbox(checked=True)
        self.show_path = qtutils.checkbox(checked=True)
        self.tabwidth = standard.SpinBox(value=8, maxi=42)
        self.textwidth = standard.SpinBox(value=72, maxi=150)

        tooltip = N_('Detect conflict markers in unmerged files')
        self.check_conflicts = qtutils.checkbox(checked=True, tooltip=tooltip)

        tooltip = N_(
            'Prevent "Stage" from staging all files when nothing is selected')
        self.safe_mode = qtutils.checkbox(checked=False, tooltip=tooltip)

        self.add_row(N_('User Name'), self.name)
        self.add_row(N_('Email Address'), self.email)
        self.add_row(N_('Tab Width'), self.tabwidth)
        self.add_row(N_('Text Width'), self.textwidth)
        self.add_row(N_('Merge Verbosity'), self.merge_verbosity)
        self.add_row(N_('Number of Diff Context Lines'), self.diff_context)
        self.add_row(N_('Summarize Merge Commits'), self.merge_summary)
        self.add_row(N_('Show Full Paths in the Window Title'), self.show_path)
        self.add_row(N_('Show Diffstat After Merge'), self.merge_diffstat)
        self.add_row(N_('Display Untracked Files'), self.display_untracked)
        self.add_row(N_('Detect Conflict Markers'), self.check_conflicts)
        self.add_row(N_('Safe Mode'), self.safe_mode)

        self.set_config({
            prefs.CHECKCONFLICTS:
                (self.check_conflicts, Defaults.check_conflicts),
            prefs.DIFFCONTEXT: (self.diff_context, Defaults.diff_context),
            prefs.DISPLAY_UNTRACKED:
                (self.display_untracked, Defaults.display_untracked),
            prefs.USER_NAME: (self.name, ''),
            prefs.USER_EMAIL: (self.email, ''),
            prefs.MERGE_DIFFSTAT:
                (self.merge_diffstat, Defaults.merge_diffstat),
            prefs.MERGE_SUMMARY: (self.merge_summary, Defaults.merge_summary),
            prefs.MERGE_VERBOSITY:
                (self.merge_verbosity, Defaults.merge_verbosity),
            prefs.SAFE_MODE: (self.safe_mode, Defaults.safe_mode),
            prefs.SHOW_PATH: (self.show_path, Defaults.show_path),
            prefs.TABWIDTH: (self.tabwidth, Defaults.tabwidth),
            prefs.TEXTWIDTH: (self.textwidth, Defaults.textwidth),
        })


class SettingsFormWidget(FormWidget):

    def __init__(self, context, model, parent):
        FormWidget.__init__(self, context, model, parent)

        self.fixed_font = QtWidgets.QFontComboBox()
        self.font_size = standard.SpinBox(value=12, mini=8, maxi=192)

        self.maxrecent = standard.SpinBox(maxi=99)
        self.tabwidth = standard.SpinBox(maxi=42)
        self.textwidth = standard.SpinBox(maxi=150)

        self.editor = QtWidgets.QLineEdit()
        self.historybrowser = QtWidgets.QLineEdit()
        self.blameviewer = QtWidgets.QLineEdit()
        self.difftool = QtWidgets.QLineEdit()
        self.mergetool = QtWidgets.QLineEdit()

        self.linebreak = qtutils.checkbox()
        self.keep_merge_backups = qtutils.checkbox()
        self.sort_bookmarks = qtutils.checkbox()
        self.bold_headers = qtutils.checkbox()
        self.save_window_settings = qtutils.checkbox()
        self.check_spelling = qtutils.checkbox()
        self.expandtab = qtutils.checkbox()

        self.add_row(N_('Fixed-Width Font'), self.fixed_font)
        self.add_row(N_('Font Size'), self.font_size)
        self.add_row(N_('Editor'), self.editor)
        self.add_row(N_('History Browser'), self.historybrowser)
        self.add_row(N_('Blame Viewer'), self.blameviewer)
        self.add_row(N_('Diff Tool'), self.difftool)
        self.add_row(N_('Merge Tool'), self.mergetool)
        self.add_row(N_('Recent repository count'), self.maxrecent)
        self.add_row(N_('Auto-Wrap Lines'), self.linebreak)
        self.add_row(N_('Insert spaces instead of tabs'), self.expandtab)
        self.add_row(N_('Sort bookmarks alphabetically'), self.sort_bookmarks)
        self.add_row(N_('Keep *.orig Merge Backups'), self.keep_merge_backups)
        self.add_row(N_('Bold on dark headers instead of italic '
                        '(restart required)'), self.bold_headers)
        self.add_row(N_('Save GUI Settings'), self.save_window_settings)
        self.add_row(N_('Check spelling'), self.check_spelling)

        self.set_config({
            prefs.SAVEWINDOWSETTINGS:
                (self.save_window_settings, Defaults.save_window_settings),
            prefs.TABWIDTH: (self.tabwidth, Defaults.tabwidth),
            prefs.EXPANDTAB: (self.expandtab, Defaults.expandtab),
            prefs.TEXTWIDTH: (self.textwidth, Defaults.textwidth),
            prefs.LINEBREAK: (self.linebreak, Defaults.linebreak),
            prefs.MAXRECENT: (self.maxrecent, Defaults.maxrecent),
            prefs.SORT_BOOKMARKS:
                (self.sort_bookmarks, Defaults.sort_bookmarks),
            prefs.BOLD_HEADERS: (self.bold_headers, Defaults.bold_headers),
            prefs.DIFFTOOL: (self.difftool, Defaults.difftool),
            prefs.EDITOR:
                (self.editor, os.getenv('VISUAL', Defaults.editor)),
            prefs.HISTORY_BROWSER:
                (self.historybrowser, prefs.default_history_browser()),
            prefs.BLAME_VIEWER: (self.blameviewer, Defaults.blame_viewer),
            prefs.MERGE_KEEPBACKUP:
                (self.keep_merge_backups, Defaults.merge_keep_backup),
            prefs.MERGETOOL: (self.mergetool, Defaults.mergetool),
            prefs.SPELL_CHECK: (self.check_spelling, Defaults.spellcheck),
        })

        self.fixed_font.currentFontChanged.connect(self.current_font_changed)
        self.font_size.valueChanged.connect(self.font_size_changed)

    def update_from_config(self):
        FormWidget.update_from_config(self)
        context = self.context
        block = self.fixed_font.blockSignals(True)
        font = qtutils.diff_font(context)
        self.fixed_font.setCurrentFont(font)
        self.fixed_font.blockSignals(block)

        block = self.font_size.blockSignals(True)
        font_size = font.pointSize()
        self.font_size.setValue(font_size)
        self.font_size.blockSignals(block)

    def font_size_changed(self, size):
        font = self.fixed_font.currentFont()
        font.setPointSize(size)
        cmds.do(prefs.SetConfig, self.model,
                'user', prefs.FONTDIFF, font.toString())

    def current_font_changed(self, font):
        cmds.do(prefs.SetConfig, self.model,
                'user', prefs.FONTDIFF, font.toString())


class AppearanceFormWidget(FormWidget):

    def __init__(self, context, model, parent):
        FormWidget.__init__(self, context, model, parent)

        self.theme = qtutils.combo_mapped(themes.themes_map(), False)
        self.high_dpi = qtutils.combo_mapped(hidpi.choices_map(), False)
        self.high_dpi.setEnabled(hidpi.is_supported())

        self.add_row(N_('GUI theme'), self.theme)
        self.add_row(N_('High DPI'), self.high_dpi)
        self.add_row('<br/><b>' +
                     N_("Appearance preferences requires application restart")
                     + '</b>', None)

        self.set_config({
            prefs.THEME: (self.theme, Defaults.theme),
            prefs.HIDPI: (self.high_dpi, Defaults.hidpi)
        })

    def update_from_config(self):
        FormWidget.update_from_config(self)


class PreferencesView(standard.Dialog):

    def __init__(self, context, model, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.context = context
        self.setWindowTitle(N_('Preferences'))
        if parent is not None:
            self.setWindowModality(QtCore.Qt.WindowModal)

        self.resize(600, 360)

        self.tab_bar = QtWidgets.QTabBar()
        self.tab_bar.setDrawBase(False)
        self.tab_bar.addTab(N_('All Repositories'))
        self.tab_bar.addTab(N_('Current Repository'))
        self.tab_bar.addTab(N_('Settings'))
        self.tab_bar.addTab(N_('Appearance'))

        self.user_form = RepoFormWidget(context, model, self, source='user')
        self.repo_form = RepoFormWidget(context, model, self, source='repo')
        self.options_form = SettingsFormWidget(context, model, self)
        self.appearance = AppearanceFormWidget(context, model, self)

        self.stack_widget = QtWidgets.QStackedWidget()
        self.stack_widget.addWidget(self.user_form)
        self.stack_widget.addWidget(self.repo_form)
        self.stack_widget.addWidget(self.options_form)
        self.stack_widget.addWidget(self.appearance)

        self.close_button = qtutils.close_button()

        self.button_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                          qtutils.STRETCH, self.close_button)

        self.main_layout = qtutils.vbox(defs.margin, defs.spacing,
                                        self.tab_bar, self.stack_widget,
                                        self.button_layout)
        self.setLayout(self.main_layout)

        self.tab_bar.currentChanged.connect(self.stack_widget.setCurrentIndex)
        self.stack_widget.currentChanged.connect(self.update_widget)

        qtutils.connect_button(self.close_button, self.accept)
        qtutils.add_close_action(self)

        self.update_widget(0)

    def update_widget(self, idx):
        widget = self.stack_widget.widget(idx)
        widget.update_from_config()
