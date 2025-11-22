"""Themes generators"""
import os


try:
    import AppKit
except ImportError:
    AppKit = None
from qtpy import QtGui

from .i18n import N_
from .widgets import defs
from . import core
from . import icons
from . import qtutils
from . import resources
from . import utils


class EStylesheet:
    DEFAULT = 1
    FLAT = 2
    CUSTOM = 3  # Files located in ~/.config/git-cola/themes/*.qss


class Theme:
    def __init__(
        self,
        name,
        title,
        is_dark,
        style_sheet=EStylesheet.DEFAULT,
        main_color=None,
        macos_appearance=None,
    ):
        self.name = name
        self.title = title
        self.is_dark = is_dark
        self.is_palette_dark = None
        self.style_sheet = style_sheet
        self.main_color = main_color
        self.macos_appearance = macos_appearance
        self.disabled_text_color = None
        self.text_color = None
        self.highlight_color = None
        self.background_color = None
        self.palette = None

    def build_style_sheet(self, app_palette, bold_fonts):
        if self.style_sheet == EStylesheet.CUSTOM:
            return self.style_sheet_custom(app_palette, bold_fonts)
        if self.style_sheet == EStylesheet.FLAT:
            return self.style_sheet_flat(bold_fonts)
        window = app_palette.color(QtGui.QPalette.Window)
        self.is_palette_dark = window.lightnessF() < 0.5
        return style_sheet_default(app_palette, bold_fonts)

    def build_palette(self, app_palette):
        QPalette = QtGui.QPalette
        palette_dark = app_palette.color(QPalette.Base).lightnessF() < 0.5
        if self.is_palette_dark is None:
            self.is_palette_dark = palette_dark

        if palette_dark and self.is_dark:
            self.palette = app_palette
            return app_palette
        if not palette_dark and not self.is_dark:
            self.palette = app_palette
            return app_palette
        if self.is_dark:
            background = '#202025'
        else:
            background = '#edeef3'

        bg_color = qtutils.css_color(background)
        txt_color = qtutils.css_color('#777777')
        palette = QPalette(bg_color)
        palette.setColor(QPalette.Base, bg_color)
        palette.setColor(QPalette.Disabled, QPalette.Text, txt_color)
        self.background_color = background
        self.palette = palette
        return palette

    def style_sheet_flat(self, bold_fonts):
        main_color = self.main_color
        color = qtutils.css_color(main_color)
        color_rgb = qtutils.rgb_css(color)
        self.is_palette_dark = self.is_dark

        if self.is_dark:
            background = '#2e2f30'
            field = '#383a3c'
            grayed = '#06080a'
            button_text = '#000000'
            field_text = '#d0d0d0'
            darker = qtutils.hsl_css(
                color.hslHueF(), color.hslSaturationF() * 0.3, color.lightnessF() * 1.3
            )
            lighter = qtutils.hsl_css(
                color.hslHueF(), color.hslSaturationF() * 0.7, color.lightnessF() * 0.6
            )
            focus = qtutils.hsl_css(
                color.hslHueF(), color.hslSaturationF() * 0.7, color.lightnessF() * 0.7
            )
        else:
            background = '#edeef3'
            field = '#ffffff'
            grayed = '#a2a2b0'
            button_text = '#ffffff'
            field_text = '#000000'
            darker = qtutils.hsl_css(
                color.hslHueF(), color.hslSaturationF(), color.lightnessF() * 0.4
            )
            lighter = qtutils.hsl_css(color.hslHueF(), color.hslSaturationF(), 0.92)
            focus = color_rgb

        self.disabled_text_color = grayed
        self.text_color = field_text
        self.highlight_color = lighter
        self.background_color = background
        if bold_fonts:
            font_weight = 'font-weight: bold;'
        else:
            font_weight = ''

        return """
            /* regular widgets */
            * {{
                {font_weight}
                background-color: {background};
                color: {field_text};
                selection-background-color: {lighter};
                alternate-background-color: {field};
                selection-color: {field_text};
                show-decoration-selected: 1;
                spacing: 2px;
            }}

            /* Focused widths get a thin border */
            QTreeView:focus, QListView:focus,
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-width: 1px;
                border-style: solid;
                border-color: {focus};
            }}

            QWidget:disabled {{
                border-color: {grayed};
                color: {grayed};
            }}
            QDockWidget > QFrame {{
                margin: 0px 0px 0px 0px;
            }}
            QPlainTextEdit, QLineEdit, QTextEdit, QAbstractItemView,
            QAbstractSpinBox {{
                background-color: {field};
                border-color: {grayed};
                border-style: solid;
                border-width: 1px;
            }}
            QAbstractItemView::item:selected {{
                background-color: {lighter};
            }}
            QAbstractItemView::item:hover {{
                background-color: {lighter};
            }}
            QLabel {{
                color: {darker};
                background-color: transparent;
            }}
            DockTitleBarWidget {{
                padding-bottom: 4px;
            }}

            /* buttons */
            QPushButton[flat="false"] {{
                background-color: {button};
                color: {button_text};
                border-radius: 2px;
                border-width: 0;
                margin-bottom: 1px;
                min-width: 55px;
                padding: 4px 5px;
            }}
            QPushButton[flat="true"], QToolButton {{
                background-color: transparent;
                border-radius: 0px;
            }}
            QPushButton[flat="true"] {{
                margin-bottom: 10px;
            }}
            QPushButton:hover, QToolButton:hover {{
               background-color: {darker};
            }}
            QPushButton[flat="false"]:pressed, QToolButton:pressed {{
                background-color: {darker};
                margin: 1px 1px 2px 1px;
            }}
            QPushButton:disabled {{
                background-color: {grayed};
                color: {field};
                padding-left: 5px;
                padding-top: 5px;
            }}
            QPushButton[flat="true"]:disabled {{
                background-color: transparent;
            }}

            /*menus*/
            QMenuBar {{
                background-color: {background};
                color: {field_text};
                border-width: 0;
                padding: 1px;
            }}
            QMenuBar::item {{
                background: transparent;
            }}
            QMenuBar::item:selected {{
                background: {button};
            }}
            QMenuBar::item:pressed {{
                background: {button};
            }}
            QMenu {{
                background-color: {field};
            }}
            QMenu::separator {{
                background: {background};
                height: 1px;
            }}

            /* combo box */
            QComboBox {{
                background-color: {field};
                border-color: {grayed};
                border-style: solid;
                color: {field_text};
                border-radius: 0px;
                border-width: 1px;
                margin-bottom: 1px;
                padding: 0 5px;
            }}
            QComboBox::drop-down {{
                border-color: {field_text} {field} {field} {field};
                border-style: solid;
                subcontrol-position: right;
                border-width: 4px 3px 0 3px;
                height: 0;
                margin-right: 5px;
                width: 0;
            }}
            QComboBox::drop-down:hover {{
                border-color: {button} {field} {field} {field};
            }}
            QComboBox:item {{
                background-color: {button};
                color: {button_text};
                border-width: 0;
                height: 22px;
            }}
            QComboBox:item:selected {{
                background-color: {darker};
                color: {button_text};
            }}
            QComboBox:item:checked {{
                background-color: {darker};
                color: {button_text};
            }}

            /* MainWindow separator */
            QMainWindow::separator {{
                width: {separator}px;
                height: {separator}px;
            }}
            QMainWindow::separator:hover {{
                background: {focus};
            }}

            /* scroll bar */
            QScrollBar {{
                background-color: {field};
                border: 0;
            }}
            QScrollBar::handle {{
                 background: {lighter}
            }}
            QScrollBar::handle:hover {{
                 background: {button}
            }}
            QScrollBar:horizontal {{
                margin: 0 11px 0 11px;
                height: 10px;
            }}
            QScrollBar:vertical {{
                margin: 11px 0 11px 0;
                width: 10px;
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                background: {background};
                subcontrol-origin: margin;
            }}
            QScrollBar::sub-line:horizontal {{ /*required by a buggy Qt version*/
                subcontrol-position: left;
            }}
            QScrollBar::add-line:hover, QScrollBar::sub-line:hover {{
                background: {button};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 10px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 10px;
            }}
            QScrollBar:left-arrow, QScrollBar::right-arrow,
            QScrollBar::up-arrow, QScrollBar::down-arrow {{
                border-style: solid;
                height: 0;
                width: 0;
            }}
            QScrollBar:right-arrow {{
                border-color: {background} {background}
                              {background} {darker};
                border-width: 3px 0 3px 4px;
            }}
            QScrollBar:left-arrow {{
                border-color: {background} {darker}
                              {background} {background};
                border-width: 3px 4px 3px 0;
            }}
            QScrollBar:up-arrow {{
                border-color: {background} {background}
                              {darker} {background};
                border-width: 0 3px 4px 3px;
            }}
            QScrollBar:down-arrow {{
                border-color: {darker} {background}
                              {background} {background};
                border-width: 4px 3px 0 3px;
            }}
            QScrollBar:right-arrow:hover {{
                border-color: {button} {button}
                              {button} {darker};
            }}
            QScrollBar:left-arrow:hover {{
                border-color: {button} {darker}
                              {button} {button};
            }}
            QScrollBar:up-arrow:hover {{
                border-color: {button} {button}
                              {darker} {button};
            }}
            QScrollBar:down-arrow:hover {{
                border-color: {darker} {button}
                              {button} {button};
            }}

            /* tab bar (stacked & docked widgets) */
            QTabBar::tab {{
                background: transparent;
                border-color: {darker};
                border-width: 1px;
                margin: 1px;
                padding: 3px 5px;
            }}
            QTabBar::tab:selected {{
                background: {grayed};
            }}

            /* check box */
            QCheckBox {{
                spacing: 8px;
                margin: 4px;
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                background-color: {field};
                border-color: {darker};
                border-style: solid;
                subcontrol-position: left;
                border-width: 1px;
                height: 13px;
                width: 13px;
            }}
            QCheckBox::indicator:unchecked:hover {{
                background-color: {button};
            }}
            QCheckBox::indicator:unchecked:pressed {{
                background-color: {darker};
            }}
            QCheckBox::indicator:checked {{
                background-color: {darker};
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: {button};
            }}
            QCheckBox::indicator:checked:pressed {{
                background-color: {field};
            }}

            /* radio checkbox */
            QRadioButton {{
                spacing: 8px;
                margin: 4px;
            }}
            QRadioButton::indicator {{
                height: 0.75em;
                width: 0.75em;
            }}

            /* progress bar */
            QProgressBar {{
                background-color: {field};
                border: 1px solid {darker};
            }}
            QProgressBar::chunk {{
                background-color: {button};
                width: 1px;
            }}

            /* spin box */
            QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
                background-color: transparent;
            }}
            QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {{
                border-style: solid;
                height: 0;
                width: 0;
            }}
            QAbstractSpinBox::up-arrow {{
                border-color: {field} {field} {darker} {field};
                border-width: 0 3px 4px 3px;
            }}
            QAbstractSpinBox::up-arrow:hover {{
                border-color: {field} {field} {button} {field};
                border-width: 0 3px 4px 3px;
            }}
            QAbstractSpinBox::down-arrow {{
                border-color: {darker} {field} {field} {field};
                border-width: 4px 3px 0 3px;
            }}
            QAbstractSpinBox::down-arrow:hover {{
                border-color: {button} {field} {field} {field};
                border-width: 4px 3px 0 3px;
            }}

            /* dialogs */
            QDialog > QFrame {{
                margin: 2px 2px 2px 2px;
            }}

            /* headers */
            QHeaderView {{
                color: {field_text};
                border-style: solid;
                border-width: 0 0 1px 0;
                border-color: {grayed};
            }}
            QHeaderView::section {{
                border-style: solid;
                border-right: 1px solid {grayed};
                background-color: {background};
                color: {field_text};
                padding-left: 4px;
            }}

            /* headers */
            QHeaderView {{
                color: {field_text};
                border-style: solid;
                border-width: 0 0 1px 0;
                border-color: {grayed};
            }}
            QHeaderView::section {{
                border-style: solid;
                border-right: 1px solid {grayed};
                background-color: {background};
                color: {field_text};
                padding-left: 4px;
            }}

            """.format(
            background=background,
            field=field,
            font_weight=font_weight,
            button=color_rgb,
            darker=darker,
            lighter=lighter,
            grayed=grayed,
            button_text=button_text,
            field_text=field_text,
            separator=defs.separator,
            focus=focus,
        )

    def style_sheet_custom(self, app_palette, bold_fonts):
        """Get custom style sheet.
        File name is saved in variable self.name.
        If user has deleted file, use default style"""

        # check if path exists
        filename = resources.config_home('themes', self.name + '.qss')
        if not core.exists(filename):
            return style_sheet_default(app_palette, bold_fonts)
        try:
            return core.read(filename)
        except OSError as err:
            core.print_stderr(f'warning: unable to read custom theme {filename}: {err}')
            return style_sheet_default(app_palette, bold_fonts)

    def get_palette(self):
        """Get a QPalette for the current theme"""
        if self.palette is None:
            palette = qtutils.current_palette()
        else:
            palette = self.palette
        return palette

    def highlight_color_rgb(self):
        """Return an rgb(r,g,b) CSS color value for the selection highlight"""
        if self.highlight_color:
            highlight_rgb = self.highlight_color
        elif self.main_color:
            highlight_rgb = qtutils.rgb_css(
                qtutils.css_color(self.main_color).lighter()
            )
        else:
            palette = self.get_palette()
            color = palette.color(QtGui.QPalette.Highlight)
            highlight_rgb = qtutils.rgb_css(color)
        return highlight_rgb

    def selection_color(self):
        """Return a color suitable for selections"""
        highlight = qtutils.css_color(self.highlight_color_rgb())
        if highlight.lightnessF() > 0.7:  # Avoid clamping light colors to white.
            color = highlight
        else:
            color = highlight.lighter()
        return color

    def text_colors_rgb(self):
        """Return a pair of rgb(r,g,b) CSS color values for text and selected text"""
        if self.text_color:
            text_rgb = self.text_color
            highlight_text_rgb = self.text_color
        else:
            palette = self.get_palette()
            color = palette.text().color()
            text_rgb = qtutils.rgb_css(color)

            color = palette.highlightedText().color()
            highlight_text_rgb = qtutils.rgb_css(color)
        return text_rgb, highlight_text_rgb

    def disabled_text_color_rgb(self):
        """Return an rgb(r,g,b) CSS color value for the disabled text"""
        if self.disabled_text_color:
            disabled_text_rgb = self.disabled_text_color
        else:
            palette = self.get_palette()
            color = palette.color(QtGui.QPalette.Disabled, QtGui.QPalette.Text)
            disabled_text_rgb = qtutils.rgb_css(color)
        return disabled_text_rgb

    def background_color_rgb(self):
        """Return an rgb(r,g,b) CSS color value for the window background"""
        if self.background_color:
            background_color = self.background_color
        else:
            palette = self.get_palette()
            window = palette.color(QtGui.QPalette.Base)
            background_color = qtutils.rgb_css(window)
        return background_color


def style_sheet_default(palette, bold_fonts):
    highlight = palette.color(QtGui.QPalette.Highlight)
    shadow = palette.color(QtGui.QPalette.Shadow)
    base = palette.color(QtGui.QPalette.Base)

    highlight_rgb = qtutils.rgb_css(highlight)
    shadow_rgb = qtutils.rgb_css(shadow)
    base_rgb = qtutils.rgb_css(base)
    if bold_fonts:
        font_weight = 'font-weight: bold;'
    else:
        font_weight = ''

    return """
        * {{
            {font_weight}
        }}
        QCheckBox::indicator {{
            width: {checkbox_size}px;
            height: {checkbox_size}px;
        }}
        QCheckBox::indicator::unchecked {{
            border: {checkbox_border}px solid {shadow_rgb};
            background: {base_rgb};
        }}
        QCheckBox::indicator::checked {{
            image: url({checkbox_icon});
            border: {checkbox_border}px solid {shadow_rgb};
            background: {base_rgb};
        }}

        QRadioButton::indicator {{
            width: {radio_size}px;
            height: {radio_size}px;
        }}
        QRadioButton::indicator::unchecked {{
            border: {radio_border}px solid {shadow_rgb};
            border-radius: {radio_radius}px;
            background: {base_rgb};
        }}
        QRadioButton::indicator::checked {{
            image: url({radio_icon});
            border: {radio_border}px solid {shadow_rgb};
            border-radius: {radio_radius}px;
            background: {base_rgb};
        }}

        QSplitter::handle:hover {{
            background: {highlight_rgb};
        }}

        QMainWindow::separator {{
            background: none;
            width: {separator}px;
            height: {separator}px;
        }}
        QMainWindow::separator:hover {{
            background: {highlight_rgb};
        }}

        """.format(
        font_weight=font_weight,
        separator=defs.separator,
        highlight_rgb=highlight_rgb,
        shadow_rgb=shadow_rgb,
        base_rgb=base_rgb,
        checkbox_border=defs.border,
        checkbox_icon=icons.check_name(),
        checkbox_size=defs.checkbox,
        radio_border=defs.radio_border,
        radio_icon=icons.dot_name(),
        radio_radius=defs.radio // 2,
        radio_size=defs.radio,
    )


def get_all_themes():
    themes = [
        Theme(
            'default',
            N_('Default'),
            False,
            style_sheet=EStylesheet.DEFAULT,
            main_color=None,
        ),
    ]

    if utils.is_darwin():
        themes.extend(get_macos_themes().values())

    themes.extend([
        Theme(
            'flat-light-blue',
            N_('Flat light blue'),
            False,
            style_sheet=EStylesheet.FLAT,
            main_color='#5271cc',
        ),
        Theme(
            'flat-light-red',
            N_('Flat light red'),
            False,
            style_sheet=EStylesheet.FLAT,
            main_color='#cc5452',
        ),
        Theme(
            'flat-light-grey',
            N_('Flat light grey'),
            False,
            style_sheet=EStylesheet.FLAT,
            main_color='#707478',
        ),
        Theme(
            'flat-light-green',
            N_('Flat light green'),
            False,
            style_sheet=EStylesheet.FLAT,
            main_color='#42a65c',
        ),
        Theme(
            'flat-dark-blue',
            N_('Flat dark blue'),
            True,
            style_sheet=EStylesheet.FLAT,
            main_color='#5271cc',
        ),
        Theme(
            'flat-dark-red',
            N_('Flat dark red'),
            True,
            style_sheet=EStylesheet.FLAT,
            main_color='#cc5452',
        ),
        Theme(
            'flat-dark-grey',
            N_('Flat dark grey'),
            True,
            style_sheet=EStylesheet.FLAT,
            main_color='#aaaaaa',
        ),
        Theme(
            'flat-dark-green',
            N_('Flat dark green'),
            True,
            style_sheet=EStylesheet.FLAT,
            main_color='#42a65c',
        ),
    ])

    # check if themes path exists in user folder
    path = resources.config_home('themes')
    if not os.path.isdir(path):
        return themes

    # Gather Qt .qss stylesheet themes
    try:
        filenames = core.listdir(path)
    except OSError:
        return themes

    for filename in filenames:
        name, ext = os.path.splitext(filename)
        if ext == '.qss':
            themes.append(Theme(name, N_(name), False, EStylesheet.CUSTOM, None))

    return themes


def apply_platform_theme(theme):
    """Apply platform-specific themes (e.g. dark mode on macOS)"""
    # https://developer.apple.com/documentation/appkit/nsappearancecustomization/choosing_a_specific_appearance_for_your_macos_app
    # https://github.com/git-cola/git-cola/issues/905#issuecomment-461118465
    if utils.is_darwin():
        if AppKit is None:
            return
        app = AppKit.NSApplication.sharedApplication()
        macos_themes = get_macos_themes()
        try:
            macos_appearance = macos_themes[theme].macos_appearance
        except KeyError:
            return
        if macos_appearance is None:
            return
        appearance = AppKit.NSAppearance.appearanceNamed_(macos_appearance)
        app.setAppearance_(appearance)


def get_macos_themes():
    """Get a mapping from theme names to macOS NSAppearanceName values"""
    themes = {}
    if AppKit is None:
        return themes

    def add_macos_theme(name, description, is_dark, attr):
        """Add an AppKit theme if it exists"""
        if hasattr(AppKit, attr):
            themes[name] = Theme(
                name, description, is_dark, macos_appearance=getattr(AppKit, attr)
            )

    add_macos_theme(
        'macos-aqua-light', N_('MacOS Aqua light'), False, 'NSAppearanceNameAqua'
    )
    add_macos_theme(
        'macos-aqua-dark',
        N_('MacOS Aqua dark'),
        True,
        'NSAppearanceNameDarkAqua',
    )
    add_macos_theme(
        'macos-vibrant-light',
        N_('MacOS Vibrant light'),
        False,
        'NSAppearanceNameVibrantLight',
    )
    add_macos_theme(
        'macos-vibrant-dark',
        N_('MacOS Vibrant dark'),
        True,
        'NSAppearanceNameVibrantDark',
    )
    return themes


def options(themes=None):
    """Return a dictionary mapping display names to theme names"""
    if themes is None:
        themes = get_all_themes()
    return [(theme.title, theme.name) for theme in themes]


def find_theme(name):
    themes = get_all_themes()
    for item in themes:
        if item.name == name:
            return item
    return themes[0]
