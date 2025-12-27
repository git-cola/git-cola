from qtpy import QtCore
from qtpy import QtWidgets

from . import defs
from . import standard
from .. import cmds
from .. import hidpi
from .. import icons
from .. import qtutils
from .. import spellcheck
from .. import themes
from ..compat import ustr
from ..i18n import N_
from ..models import prefs
from ..models.prefs import Defaults
from ..models.prefs import fallback_editor


def preferences(context, model=None, parent=None):
    if model is None:
        model = prefs.PreferencesModel(context)
    view = PreferencesView(context, model, parent=parent)
    view.show()
    view.raise_()
    return view


class FormWidget(QtWidgets.QWidget):
    def __init__(self, context, model, parent, source='global'):
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
            widget.editingFinished.connect(self._text_config_changed(config, widget))
            widget.returnPressed.connect(self._text_config_changed(config, widget))

        elif isinstance(widget, qtutils.ComboBox):
            widget.currentIndexChanged.connect(
                self._item_config_changed(config, widget)
            )

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
            value = widget.value()
            cmds.do(prefs.SetConfig, self.model, self.source, config, value)

        return runner

    def update_from_config(self):
        if self.source == 'global':
            getter = self.cfg.get_user_or_system
        else:
            getter = self.cfg.get

        for config, widget in self.widget_to_config.items():
            value = getter(config)
            if value is None:
                value = self.defaults[config]
            set_widget_value(widget, value)


def set_widget_value(widget, value):
    """Set a value on a widget without emitting notifications"""
    with qtutils.BlockSignals(widget):
        if isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(value)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(value)
        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(value)
        elif hasattr(widget, 'set_value'):
            widget.set_value(value)


class RepoFormWidget(FormWidget):
    def __init__(self, context, model, parent, source):
        FormWidget.__init__(self, context, model, parent, source=source)
        self.name = QtWidgets.QLineEdit()
        self.email = QtWidgets.QLineEdit()

        tooltip = N_(
            'Default directory when exporting patches.\n'
            'Relative paths are relative to the current repository.\n'
            'Absolute path are used as-is.'
        )
        patches_directory = prefs.patches_directory(context)
        self.patches_directory = standard.DirectoryPathLineEdit(patches_directory, self)
        self.patches_directory.setToolTip(tooltip)

        tooltip = N_(
            """
This option determines how the supplied commit message should be
cleaned up before committing.

The <mode> can be strip, whitespace, verbatim, scissors or default.

strip
    Strip leading and trailing empty lines, trailing whitespace,
    commentary and collapse consecutive empty lines.

whitespace
    Same as strip except #commentary is not removed.

verbatim
    Do not change the message at all.

scissors
    Same as whitespace except that everything from (and including) the line
    found below is truncated, if the message is to be edited.
    "#" can be customized with core.commentChar.

    # ------------------------ >8 ------------------------"""
        )
        self.commit_cleanup = qtutils.combo(
            prefs.commit_cleanup_modes(), tooltip=tooltip
        )
        self.diff_context = standard.SpinBox(value=5, mini=2, maxi=9995)
        self.merge_verbosity = standard.SpinBox(value=5, maxi=5)
        self.merge_summary = qtutils.checkbox(checked=True)
        self.autotemplate = qtutils.checkbox(checked=False)
        self.merge_diffstat = qtutils.checkbox(checked=True)
        self.display_untracked = qtutils.checkbox(checked=True)
        self.rebase_update_refs = qtutils.checkbox(checked=False)
        self.show_path = qtutils.checkbox(checked=True)
        self.update_index = qtutils.checkbox(checked=True)
        self.http_proxy = QtWidgets.QLineEdit()

        tooltip = N_(
            'Enable file system change monitoring using '
            'inotify on Linux and win32event on Windows'
        )
        self.inotify = qtutils.checkbox(checked=True)
        self.inotify.setToolTip(tooltip)

        tooltip = N_(
            'Milliseconds to wait between filesystem change events.\n'
            'Hint: 5000 ms is 5 seconds. 60000 ms is one minute. 360000 ms is 1 hour.'
        )
        # 360000 milliseconds is 1 hour (60mins * 60secs * 1000ms)
        self.inotify_delay = standard.SpinBox(mini=100, maxi=3600000, tooltip=tooltip)

        self.logdate = qtutils.combo(prefs.date_formats())
        tooltip = N_(
            'The date-time format used when displaying dates in Git DAG.\n'
            'This value is passed to git log --date=<format>'
        )
        self.logdate.setToolTip(tooltip)

        tooltip = N_('Use gravatar.com to lookup icons for author emails')
        self.enable_gravatar = qtutils.checkbox(checked=True, tooltip=tooltip)

        tooltip = N_('Display desktop notifications using popup dialogs')
        self.enable_popups = qtutils.checkbox(checked=False, tooltip=tooltip)

        tooltip = N_('Enable path autocompletion in tools')
        self.autocomplete_paths = qtutils.checkbox(checked=True, tooltip=tooltip)

        tooltip = N_('Enable detection and configuration of HTTP proxy settings')
        self.autodetect_proxy = qtutils.checkbox(checked=True, tooltip=tooltip)

        self.add_row(N_('Name'), self.name)
        self.add_row(N_('Email'), self.email)

        self.add_row('', QtWidgets.QLabel())
        self.add_row(N_('Patches Directory'), self.patches_directory)
        self.add_row(N_('Number of Diff Context Lines'), self.diff_context)
        self.add_row(N_('Log Date Format'), self.logdate)

        self.add_row('', QtWidgets.QLabel())
        self.add_row(
            N_('Automatically Load Commit Message Template'), self.autotemplate
        )
        self.add_row(N_('Commit Message Cleanup'), self.commit_cleanup)

        self.add_row('', QtWidgets.QLabel())
        self.add_row(
            N_('Update stacked branches/refs when rebasing'),
            self.rebase_update_refs,
        )
        self.add_row(N_('Show Diffstat After Merge'), self.merge_diffstat)
        self.add_row(N_('Summarize Merge Commits'), self.merge_summary)
        self.add_row(N_('Merge Verbosity'), self.merge_verbosity)

        self.add_row('', QtWidgets.QLabel())
        self.add_row(N_('Display Untracked Files'), self.display_untracked)
        self.add_row(N_('Enable Filesystem Monitoring'), self.inotify)
        self.add_row(N_('Filesystem Monitoring Event Delay'), self.inotify_delay)
        self.add_row(N_('Enable Gravatar Icons'), self.enable_gravatar)
        self.add_row(N_('Update Index on Startup'), self.update_index)
        self.add_row(N_('Autocomplete Paths'), self.autocomplete_paths)
        self.add_row(N_('Show Full Paths in the Window Title'), self.show_path)
        self.add_row(
            N_('Display desktop notifications using popup dialogs'), self.enable_popups
        )

        self.add_row('', QtWidgets.QLabel())
        self.add_row(
            N_('Automatically Detect and Configure Proxy Settings'),
            self.autodetect_proxy,
        )
        self.add_row(N_('HTTP Proxy URL'), self.http_proxy)

        self.set_config({
            prefs.AUTOTEMPLATE: (self.autotemplate, Defaults.autotemplate),
            prefs.AUTOCOMPLETE_PATHS: (
                self.autocomplete_paths,
                Defaults.autocomplete_paths,
            ),
            prefs.AUTODETECT_PROXY: (
                self.autodetect_proxy,
                Defaults.autodetect_proxy,
            ),
            prefs.COMMIT_CLEANUP: (self.commit_cleanup, Defaults.commit_cleanup),
            prefs.DIFFCONTEXT: (self.diff_context, Defaults.diff_context),
            prefs.DISPLAY_UNTRACKED: (
                self.display_untracked,
                Defaults.display_untracked,
            ),
            prefs.ENABLE_GRAVATAR: (self.enable_gravatar, Defaults.enable_gravatar),
            prefs.ENABLE_POPUPS: (self.enable_popups, Defaults.enable_popups),
            prefs.HTTP_PROXY: (self.http_proxy, Defaults.http_proxy),
            prefs.INOTIFY: (self.inotify, Defaults.inotify),
            prefs.INOTIFY_DELAY: (self.inotify_delay, Defaults.inotify_delay),
            prefs.LOGDATE: (self.logdate, Defaults.logdate),
            prefs.MERGE_DIFFSTAT: (self.merge_diffstat, Defaults.merge_diffstat),
            prefs.MERGE_SUMMARY: (self.merge_summary, Defaults.merge_summary),
            prefs.MERGE_VERBOSITY: (self.merge_verbosity, Defaults.merge_verbosity),
            prefs.PATCHES_DIRECTORY: (
                self.patches_directory,
                Defaults.patches_directory,
            ),
            prefs.REBASE_UPDATE_REFS: (
                self.rebase_update_refs,
                Defaults.rebase_update_refs,
            ),
            prefs.SHOW_PATH: (self.show_path, Defaults.show_path),
            prefs.USER_NAME: (self.name, ''),
            prefs.USER_EMAIL: (self.email, ''),
            prefs.UPDATE_INDEX: (self.update_index, Defaults.update_index),
        })


class SettingsFormWidget(FormWidget):
    def __init__(self, context, model, parent):
        FormWidget.__init__(self, context, model, parent)
        self.maxrecent = standard.SpinBox(maxi=99)
        self.tabwidth = standard.SpinBox(maxi=42)
        self.textwidth = standard.SpinBox(maxi=150)

        self.editor = QtWidgets.QLineEdit()
        self.editor.setToolTip(N_('The main GUI editor that must block until it exits'))

        self.background_editor = QtWidgets.QLineEdit()
        self.background_editor.setToolTip(
            N_('A non-blocking GUI editor that is launched in the background')
        )
        self.historybrowser = QtWidgets.QLineEdit()
        self.blameviewer = QtWidgets.QLineEdit()
        self.difftool = QtWidgets.QLineEdit()
        self.mergetool = QtWidgets.QLineEdit()

        self.linebreak = qtutils.checkbox()
        self.mouse_zoom = qtutils.checkbox()
        self.keep_merge_backups = qtutils.checkbox()
        self.sort_bookmarks = qtutils.checkbox()
        self.save_window_settings = qtutils.checkbox()
        tooltip = N_('Detect conflict markers in unmerged files')
        self.check_conflicts = qtutils.checkbox(checked=True, tooltip=tooltip)
        self.expandtab = qtutils.checkbox(tooltip=N_('Insert tabs instead of spaces'))
        tooltip = N_('Prevent "Stage" from staging all files when nothing is selected')
        self.safe_mode = qtutils.checkbox(checked=False, tooltip=tooltip)
        tooltip = N_('Check whether a commit has been published when amending')
        self.check_published_commits = qtutils.checkbox(checked=True, tooltip=tooltip)
        tooltip = N_(
            'Refresh repository state whenever the window is focused or un-minimized'
        )
        self.refresh_on_focus = qtutils.checkbox(checked=False, tooltip=tooltip)
        self.resize_browser_columns = qtutils.checkbox(checked=False)
        tooltip = N_('Emit notifications when commits are pushed.')
        self.notifyonpush = qtutils.checkbox(checked=False, tooltip=tooltip)

        tooltip = N_('Use "aspell" as the spelling dictionary source')
        self.aspell_enabled = qtutils.checkbox(tooltip=tooltip)
        self.check_spelling = qtutils.checkbox()
        tooltip = N_('Additional spellcheck dictionary files (requires restart)')
        self.spelling_dictionaries = DictionaryList(context)
        self.spelling_dictionaries.setToolTip(tooltip)

        tooltip = N_('Set the verbosity level to 1 or higher to log Git commands')
        self.verbosity = standard.SpinBox(value=0, mini=0, maxi=2)

        self.add_row(N_('Text Width'), self.textwidth)
        self.add_row(N_('Tab Width'), self.tabwidth)
        self.add_row(N_('Insert Spaces Instead of Tabs'), self.expandtab)
        self.add_row(N_('Auto-Wrap Lines'), self.linebreak)

        self.add_row('', QtWidgets.QLabel())
        self.add_row(N_('Editor'), self.editor)
        self.add_row(N_('Background Editor'), self.background_editor)
        self.add_row(N_('History Browser'), self.historybrowser)
        self.add_row(N_('Blame Viewer'), self.blameviewer)
        self.add_row(N_('Diff Tool'), self.difftool)
        self.add_row(N_('Merge Tool'), self.mergetool)
        self.add_row(N_('Recent Repository Count'), self.maxrecent)

        self.add_row('', QtWidgets.QLabel())
        self.add_row(N_('Detect Conflict Markers'), self.check_conflicts)
        self.add_row(N_('Keep *.orig Merge Backups'), self.keep_merge_backups)

        self.add_row('', QtWidgets.QLabel())
        self.add_row(N_('Save GUI Settings'), self.save_window_settings)
        self.add_row(N_('Ctrl + MouseWheel to Zoom'), self.mouse_zoom)
        self.add_row(N_('Refresh on Focus'), self.refresh_on_focus)
        self.add_row(N_('Sort Bookmarks Alphabetically'), self.sort_bookmarks)
        self.add_row(N_('Resize File Browser columns'), self.resize_browser_columns)

        self.add_row('', QtWidgets.QLabel())
        self.add_row(N_('Safe Mode'), self.safe_mode)
        self.add_row(
            N_('Check Published Commits when Amending'), self.check_published_commits
        )
        self.add_row(N_('Notify on Push'), self.notifyonpush)
        self.add_row(N_('Verbosity Level'), self.verbosity)

        self.add_row('', QtWidgets.QLabel())
        self.add_row(N_('Check Spelling'), self.check_spelling)
        self.add_row(N_('Enable "aspell" Spelling Dictionaries'), self.aspell_enabled)
        self.add_row(N_('Additional Spelling Dictionaries'), self.spelling_dictionaries)

        self.set_config({
            prefs.ASPELL_ENABLED: (self.aspell_enabled, Defaults.aspell_enabled),
            prefs.SAVEWINDOWSETTINGS: (
                self.save_window_settings,
                Defaults.save_window_settings,
            ),
            prefs.TABWIDTH: (self.tabwidth, Defaults.tabwidth),
            prefs.EXPANDTAB: (self.expandtab, Defaults.expandtab),
            prefs.TEXTWIDTH: (self.textwidth, Defaults.textwidth),
            prefs.LINEBREAK: (self.linebreak, Defaults.linebreak),
            prefs.MAXRECENT: (self.maxrecent, Defaults.maxrecent),
            prefs.SORT_BOOKMARKS: (self.sort_bookmarks, Defaults.sort_bookmarks),
            prefs.DIFFTOOL: (self.difftool, Defaults.difftool),
            prefs.EDITOR: (self.editor, fallback_editor()),
            prefs.BACKGROUND_EDITOR: (
                self.background_editor,
                Defaults.background_editor,
            ),
            prefs.HISTORY_BROWSER: (
                self.historybrowser,
                prefs.default_history_browser(),
            ),
            prefs.BLAME_VIEWER: (self.blameviewer, Defaults.blame_viewer),
            prefs.CHECK_CONFLICTS: (self.check_conflicts, Defaults.check_conflicts),
            prefs.CHECK_PUBLISHED_COMMITS: (
                self.check_published_commits,
                Defaults.check_published_commits,
            ),
            prefs.MERGE_KEEPBACKUP: (
                self.keep_merge_backups,
                Defaults.merge_keep_backup,
            ),
            prefs.MERGETOOL: (self.mergetool, Defaults.mergetool),
            prefs.REFRESH_ON_FOCUS: (self.refresh_on_focus, Defaults.refresh_on_focus),
            prefs.RESIZE_BROWSER_COLUMNS: (
                self.resize_browser_columns,
                Defaults.resize_browser_columns,
            ),
            prefs.SAFE_MODE: (self.safe_mode, Defaults.safe_mode),
            prefs.SPELL_CHECK: (self.check_spelling, Defaults.spellcheck),
            prefs.MOUSE_ZOOM: (self.mouse_zoom, Defaults.mouse_zoom),
            prefs.NOTIFY_ON_PUSH: (self.notifyonpush, Defaults.notifyonpush),
            prefs.VERBOSITY: (self.verbosity, Defaults.verbosity),
        })


class AppearanceFormWidget(FormWidget):
    def __init__(self, context, model, parent):
        FormWidget.__init__(self, context, model, parent)
        # Fonts
        font = self.font()
        font_size = context.cfg.get(prefs.FONTSIZE, font.pointSize())
        self.default_font_size = font_size
        self.fixed_font = QtWidgets.QFontComboBox()
        self.fixed_font_size = standard.SpinBox(value=12, mini=6, maxi=192)
        self.fixed_font_size.setToolTip(
            N_('The font size for the fixed-width diff font')
        )
        self.font_size = standard.SpinBox(value=font_size, mini=6, maxi=192)
        self.font_size.setToolTip(N_('The font size for the main UI elements'))
        # Theme selectors
        self.themes = themes.get_all_themes()
        self.theme = qtutils.combo_mapped(themes.options(themes=self.themes))
        self.icon_theme = qtutils.combo_mapped(icons.icon_themes())

        # The transform to ustr is needed because the config reader will convert
        # "0", "1", and "2" into integers.  The "1.5" value, though, is
        # parsed as a string, so the transform is effectively a no-op.
        self.high_dpi = qtutils.combo_mapped(hidpi.options(), transform=ustr)
        self.high_dpi.setEnabled(hidpi.is_supported())
        self.bold_fonts = qtutils.checkbox()
        self.bold_headers = qtutils.checkbox()
        self.status_show_totals = qtutils.checkbox()
        self.status_indent = qtutils.checkbox()
        self.block_cursor = qtutils.checkbox(checked=True)

        self.add_row(N_('Fixed-Width Font'), self.fixed_font)
        self.add_row(N_('Font Size'), self.fixed_font_size)
        self.add_row(N_('Font Size (UI)'), self.font_size)
        self.add_row(N_('GUI theme'), self.theme)
        self.add_row(N_('Icon theme'), self.icon_theme)
        self.add_row(N_('High DPI'), self.high_dpi)
        self.add_row(N_('Bold all fonts'), self.bold_fonts)
        self.add_row(N_('Bold on Dark Headers Instead of Italic'), self.bold_headers)
        self.add_row(N_('Show File Counts in Status Titles'), self.status_show_totals)
        self.add_row(N_('Indent Status paths'), self.status_indent)
        self.add_row(N_('Use a Block Cursor in Diff Editors'), self.block_cursor)

        self.set_config({
            prefs.BOLD_FONTS: (self.bold_fonts, Defaults.bold_fonts),
            prefs.BOLD_HEADERS: (self.bold_headers, Defaults.bold_headers),
            prefs.FONTSIZE: (
                self.font_size,
                self.default_font_size,
            ),
            prefs.HIDPI: (self.high_dpi, Defaults.hidpi),
            prefs.STATUS_SHOW_TOTALS: (
                self.status_show_totals,
                Defaults.status_show_totals,
            ),
            prefs.STATUS_INDENT: (self.status_indent, Defaults.status_indent),
            prefs.THEME: (self.theme, Defaults.theme),
            prefs.ICON_THEME: (self.icon_theme, Defaults.icon_theme),
            prefs.BLOCK_CURSOR: (self.block_cursor, Defaults.block_cursor),
        })

        self.fixed_font.currentFontChanged.connect(self.current_font_changed)
        self.fixed_font_size.valueChanged.connect(self.diff_font_size_changed)
        self.font_size.valueChanged.connect(self.font_size_changed)
        self.theme.currentIndexChanged.connect(self._theme_changed)

    def _theme_changed(self, theme_idx):
        """Set the icon theme to dark/light when the main theme changes"""
        # Set the icon theme to a theme that corresponds to the main settings.
        try:
            theme = self.themes[theme_idx]
        except IndexError:
            return
        icon_theme = self.icon_theme.value()
        if theme.name == 'default':
            if icon_theme in ('light', 'dark'):
                self.icon_theme.set_value('default')
        elif theme.is_dark:
            if icon_theme in ('default', 'light'):
                self.icon_theme.set_value('dark')
        elif not theme.is_dark:
            if icon_theme in ('default', 'dark'):
                self.icon_theme.set_value('light')

    def update_from_config(self):
        """Update widgets to the current config values"""
        FormWidget.update_from_config(self)
        context = self.context

        with qtutils.BlockSignals(self.fixed_font):
            font = qtutils.diff_font(context)
            self.fixed_font.setCurrentFont(font)

        with qtutils.BlockSignals(self.fixed_font_size):
            font_size = font.pointSize()
            self.fixed_font_size.setValue(font_size)

    def diff_font_size_changed(self, size):
        """The diff font size was changed"""
        font = self.fixed_font.currentFont()
        font.setPointSize(size)
        cmds.do(prefs.SetConfig, self.model, 'global', prefs.FONTDIFF, font.toString())

    def font_size_changed(self, size):
        """The UI font size was changed"""
        cmds.do(prefs.SetConfig, self.model, 'global', prefs.FONTSIZE, size)

    def current_font_changed(self, font):
        cmds.do(prefs.SetConfig, self.model, 'global', prefs.FONTDIFF, font.toString())


class AppearanceWidget(QtWidgets.QWidget):
    def __init__(self, form, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.form = form
        self.label = QtWidgets.QLabel(
            '<center><b>'
            + N_('Restart the application after changing appearance settings.')
            + '</b></center>'
        )
        layout = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.form,
            defs.spacing * 4,
            self.label,
            qtutils.STRETCH,
        )
        self.setLayout(layout)

    def update_from_config(self):
        self.form.update_from_config()


class DictionaryList(QtWidgets.QWidget):
    """A widget for editing a list of spelling dictionaries"""

    def __init__(self, context):
        QtWidgets.QWidget.__init__(self)
        self.context = context
        self.add_button = qtutils.create_toolbutton(
            text=N_('Add'), icon=icons.add(), tooltip=N_('Add Dictionary')
        )
        self.add_menu = qtutils.create_menu(N_('Add Dictionary'), self.add_button)
        self.add_button.setMenu(self.add_menu)

        self.remove_button = qtutils.create_toolbutton(
            text=N_('Remove'),
            icon=icons.remove(),
            tooltip=N_('Remove selected (Delete)'),
        )
        self.remove_button.setEnabled(False)

        self.dict_list = standard.ListWidget()

        self.top_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.add_button,
            self.remove_button,
            qtutils.STRETCH,
        )
        layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.top_layout, self.dict_list
        )
        self.setLayout(layout)

        self.add_menu.aboutToShow.connect(self._build_menu)
        self.dict_list.itemSelectionChanged.connect(self._selection_changed)
        qtutils.connect_button(self.remove_button, self._remove_selected)

        self.refresh()

    def refresh(self):
        """Refresh the list of configured dictionaries"""
        self.dict_list.clear()
        current_dicts = prefs.spelling_dictionaries(self.context)
        if current_dicts:
            self.dict_list.addItems(current_dicts)

    def _selection_changed(self):
        """Update the widget state when the dictionary selection changes"""
        items = self.dict_list.selected_items()
        self.remove_button.setEnabled(bool(items))

    def _build_menu(self):
        """Populate the "Add" menu with dictionary files"""
        current_dicts = set(prefs.spelling_dictionaries(self.context))
        dictionaries = spellcheck.get_available_dictionaries()
        paths = []
        for path in dictionaries:
            if path in current_dicts:
                continue
            paths.append(path)

        # If all of the paths were already added, or if the quick list of
        # dictionaries is empty, then launch the file dialog immediately.
        self.add_menu.clear()
        if not paths:
            self._select_dictionaries()
            return

        select_action = self.add_menu.addAction(N_('Select dictionary file(s)...'))
        select_action.triggered.connect(lambda _: self._select_dictionaries())
        self.add_menu.addSeparator()

        for path in paths:
            action = self.add_menu.addAction(path)
            action.triggered.connect(
                lambda _, path=path: self._add_dictionaries([path])
            )

    def _remove_selected(self):
        """Remove selected dictionary files"""
        values = [item.text() for item in self.dict_list.selected_items()]
        if not values:
            return
        remove_cmd = prefs.RemoveDictionary(self.context, values)
        remove_cmd.do()
        self.refresh()

    def _add_dictionaries(self, values):
        """Add dictionary files"""
        if not values:
            return
        add_command = prefs.AddDictionary(self.context, values)
        add_command.do()
        self.refresh()

    def _select_dictionaries(self):
        """Select and add dictionary files from disk"""
        values = qtutils.open_files(
            N_('Select dictionary file(s)...'),
            filters='Spelling Dictionaries (*.dic);;All Files (*)',
        )
        self._add_dictionaries(values)


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
        self.tab_bar.addTab(N_('Current Repository'))
        self.tab_bar.addTab(N_('All Repositories'))
        self.tab_bar.addTab(N_('Settings'))
        self.tab_bar.addTab(N_('Appearance'))

        self.user_form = RepoFormWidget(context, model, self, source='global')
        self.repo_form = RepoFormWidget(context, model, self, source='local')
        self.options_form = SettingsFormWidget(context, model, self)
        self.appearance_form = AppearanceFormWidget(context, model, self)
        self.appearance = AppearanceWidget(self.appearance_form, self)

        self.stack_widget = QtWidgets.QStackedWidget()
        self.stack_widget.addWidget(self.repo_form)
        self.stack_widget.addWidget(self.user_form)
        self.stack_widget.addWidget(self.options_form)
        self.stack_widget.addWidget(self.appearance)

        self.close_button = qtutils.close_button()

        self.button_layout = qtutils.hbox(
            defs.no_margin, defs.spacing, qtutils.STRETCH, self.close_button
        )
        # If the user already has the user.email and user.name configured then default
        # to editing the current repo's config instead of the user-wide settings.
        if context.cfg.get(prefs.USER_NAME) and context.cfg.get(prefs.USER_EMAIL):
            index = 0
        else:
            index = 1
        self.stack_widget.setCurrentIndex(index)
        self.tab_bar.setCurrentIndex(index)

        self.main_layout = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.tab_bar,
            self.stack_widget,
            self.button_layout,
        )
        self.setLayout(self.main_layout)

        self.tab_bar.currentChanged.connect(self.stack_widget.setCurrentIndex)
        self.stack_widget.currentChanged.connect(self.update_widget)

        qtutils.connect_button(self.close_button, self.accept)
        qtutils.add_close_action(self)

        self.update_widget(index)

    def update_widget(self, idx):
        widget = self.stack_widget.widget(idx)
        widget.update_from_config()
