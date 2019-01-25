"""Provides themes generator"""
from __future__ import absolute_import

from qtpy import QtGui

from .i18n import N_
from .widgets import defs
from . import icons
from . import qtutils


class EStylesheet(object):
    DEFAULT = 1
    FLAT = 2


def normalize(val, min_v=0, max_v=1):
    if val < min_v:
        return min_v
    if val > max_v:
        return max_v
    return val


class Theme(object):

    def __init__(self, name, hr_name, is_dark,
                 style_sheet=EStylesheet.DEFAULT, main_color=None):
        self.name = name
        self.hr_name = hr_name
        self.is_dark = is_dark
        self.style_sheet = style_sheet
        self.main_color = main_color

    def build_style_sheet(self, app_palette):
        if self.style_sheet == EStylesheet.FLAT:
            return self.__style_sheet_flat()
        else:
            return Theme.__style_sheet_default(app_palette)

    @staticmethod
    def __style_sheet_default(palette):
        window = palette.color(QtGui.QPalette.Window)
        highlight = palette.color(QtGui.QPalette.Highlight)
        shadow = palette.color(QtGui.QPalette.Shadow)
        base = palette.color(QtGui.QPalette.Base)

        window_rgb = qtutils.rgb_css(window)
        highlight_rgb = qtutils.rgb_css(highlight)
        shadow_rgb = qtutils.rgb_css(shadow)
        base_rgb = qtutils.rgb_css(base)

        return """
            QCheckBox::indicator {
                width: %(checkbox_size)spx;
                height: %(checkbox_size)spx;
            }
            QCheckBox::indicator::unchecked {
                border: %(checkbox_border)spx solid %(shadow_rgb)s;
                background: %(base_rgb)s;
            }
            QCheckBox::indicator::checked {
                image: url(%(checkbox_icon)s);
                border: %(checkbox_border)spx solid %(shadow_rgb)s;
                background: %(base_rgb)s;
            }

            QRadioButton::indicator {
                width: %(radio_size)spx;
                height: %(radio_size)spx;
            }
            QRadioButton::indicator::unchecked {
                border: %(radio_border)spx solid %(shadow_rgb)s;
                border-radius: %(radio_radius)spx;
                background: %(base_rgb)s;
            }
            QRadioButton::indicator::checked {
                image: url(%(radio_icon)s);
                border: %(radio_border)spx solid %(shadow_rgb)s;
                border-radius: %(radio_radius)spx;
                background: %(base_rgb)s;
            }

            QSplitter::handle:hover {
                background: %(highlight_rgb)s;
            }

            QMainWindow::separator {
                background: %(window_rgb)s;
                width: %(separator)spx;
                height: %(separator)spx;
            }
            QMainWindow::separator:hover {
                background: %(highlight_rgb)s;
            }

            """ % dict(separator=defs.separator,
                       window_rgb=window_rgb,
                       highlight_rgb=highlight_rgb,
                       shadow_rgb=shadow_rgb,
                       base_rgb=base_rgb,
                       checkbox_border=defs.border,
                       checkbox_icon=icons.check_name(),
                       checkbox_size=defs.checkbox,
                       radio_border=defs.radio_border,
                       radio_icon=icons.dot_name(),
                       radio_radius=defs.checkbox//2,
                       radio_size=defs.checkbox)

    def __style_sheet_flat(self):
        main_color = self.main_color
        color = QtGui.QColor(main_color)
        color_rgb = qtutils.rgb_css(color)

        if self.is_dark:
            background = '#2e2f30'
            field = '#383a3c'
            grayed = '#06080a'
            button_text = '#000000'
            field_text = '#d0d0d0'
            d = QtGui.QColor.fromHslF(
                color.hslHueF(),
                color.hslSaturationF()*0.6,
                normalize(color.lightnessF()*1.2)
            )
            darker_rgb = qtutils.rgb_css(d)
            w = QtGui.QColor.fromHslF(
                color.hslHueF(),
                color.hslSaturationF()*0.3,
                color.lightnessF()*0.6
            )
            lighter_rgb = qtutils.rgb_css(w)
        else:
            background = '#edeef3'
            field = '#ffffff'
            grayed = '#a2a2b0'
            button_text = '#ffffff'
            field_text = '#000000'
            d = QtGui.QColor.fromHslF(
                color.hslHueF(),
                color.hslSaturationF(),
                color.lightnessF()*0.5
            )
            darker_rgb = qtutils.rgb_css(d)
            w = QtGui.QColor.fromHslF(
                color.hslHueF(),
                normalize(color.hslSaturationF()*1.5),
                normalize(color.lightnessF()*1.5)
            )
            lighter_rgb = qtutils.rgb_css(w)

        return """
            /* regular widgets */
            * {
                background-color: %(background)s;
                color: %(field_text)s;
                selection-background-color: %(lighter)s;
                alternate-background-color: %(field)s;
                selection-color: %(field_text)s;
                show-decoration-selected: 1;
                spacing: 2px;
            }
            QDockWidget > QFrame {
                margin: 0 8px 2px 8px;
                min-height: 40px;
            }
            QPlainTextEdit, QLineEdit, QTextEdit, QAbstractItemView,
            QStackedWidget, QAbstractSpinBox {
                background-color: %(field)s;
                border-color: %(darker)s;
                border-style: solid;
                border-width: 1px;
            }
            QStackedWidget QFrame {
                border-width: 0;
            }
            QLabel {
                color: %(darker)s;
                background-color: transparent;
            }

            /* buttons */
            QPushButton[flat="false"] {
                background-color: %(button)s;
                color: %(button_text)s;
                border-radius: 2px;
                border-width: 0;
                margin-bottom: 1px;
                min-width: 55px;
                padding: 4px 5px;
            }
            QPushButton[flat="true"] {
                background-color: transparent;
                padding: 5px 0;
                border-radius: 0px;
            }
            QPushButton:hover {
               background-color: %(darker)s;
            }
            QPushButton:pressed {
                background-color: %(darker)s;
                margin: 1px 1px 2px 1px;
            }
            QPushButton:disabled {
                background-color: %(grayed)s;
                color: %(field)s;
                padding-left: 5px;
                padding-top: 5px;
            }
            QPushButton[flat="true"]:disabled {
                background-color: transparent;
            }

            /*menus*/
            QMenuBar {
                background-color: %(background)s;
                color: %(field_text)s;
                border-width: 0;
                padding: 1px;
            }
            QMenuBar::item {
                background: transparent;
            }
            QMenuBar::item:selected {
                background: %(lighter)s;
            }
            QMenuBar::item:pressed {
                background: %(lighter)s;
            }
            QMenu {
                background-color: %(field)s;
            }
            QMenu::separator {
                background: %(background)s;
                height: 1px;
            }

            /* combo box */
            QComboBox {
                background-color: %(button)s;
                color: %(button_text)s;
                border-radius: 2px;
                border-width: 0;
                margin-bottom: 1px;
                padding: 0 5px;
            }
            QComboBox::drop-down {
                border-color: %(button_text)s %(button)s %(button)s %(button)s;
                border-style: solid;
                subcontrol-position: right;
                border-width: 4px 3px 0 3px;
                height: 0;
                margin-right: 5px;
                width: 0;
            }
            QComboBox QFrame {
                border-width: 0;
            }
            QComboBox:item {
                background-color: %(button)s;
                color: %(button_text)s;
                border-width: 0;
                height: 22px;
            }
            QComboBox:item:selected {
                background-color: %(darker)s;
                color: %(button_text)s;
            }
            QComboBox:item:checked {
                background-color: %(darker)s;
                color: %(button_text)s;
            }

            /* scroll bar */
            QScrollBar {
                background-color: %(field)s;
                border: 0;
            }
            QScrollBar::handle {
                 background: %(background)s
            }
            QScrollBar::handle:hover {
                 background: %(button)s
            }
            QScrollBar:horizontal {
                margin: 0 11px 0 11px;
                height: 10px;
            }
            QScrollBar:vertical {
                margin: 11px 0 11px 0;
                width: 10px;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                background: %(background)s;
                subcontrol-origin: margin;
            }
            QScrollBar::add-line:hover, QScrollBar::sub-line:hover {
                background: %(button)s;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 10px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 10px;
            }
            QScrollBar:left-arrow, QScrollBar::right-arrow,
            QScrollBar::up-arrow, QScrollBar::down-arrow {
                border-style: solid;
                height: 0;
                width: 0;
            }
            QScrollBar:right-arrow {
                border-color: %(background)s %(background)s
                              %(background)s %(darker)s;
                border-width: 3px 0 3px 4px;
            }
            QScrollBar:left-arrow {
                border-color: %(background)s %(darker)s
                              %(background)s %(background)s;
                border-width: 3px 4px 3px 0;
            }
            QScrollBar:up-arrow {
                border-color: %(background)s %(background)s
                              %(darker)s %(background)s;
                border-width: 0 3px 4px 3px;
            }
            QScrollBar:down-arrow {
                border-color: %(darker)s %(background)s
                              %(background)s %(background)s;
                border-width: 4px 3px 0 3px;
            }
            QScrollBar:right-arrow:hover {
                border-color: %(button)s %(button)s
                              %(button)s %(darker)s;
            }
            QScrollBar:left-arrow:hover {
                border-color: %(button)s %(darker)s
                              %(button)s %(button)s;
            }
            QScrollBar:up-arrow:hover {
                border-color: %(button)s %(button)s
                              %(darker)s %(button)s;
            }
            QScrollBar:down-arrow:hover {
                border-color: %(darker)s %(button)s
                              %(button)s %(button)s;
            }

            /* tab bar (stacked & docked widgets) */
            QTabBar::tab {
                background: transparent;
                border-color: %(darker)s;
                border-width: 1px;
                margin: 1px;
                padding: 3px 5px;
            }
            QTabBar::tab:selected {
                background: %(grayed)s;
            }

            /* check box */
            QCheckBox {
                background-color: transparent;
            }
            QCheckBox::indicator {
                background-color: %(field)s;
                border-color: %(darker)s;
                border-style: solid;
                subcontrol-position: left;
                border-radius: 2px;
                border-width: 1px;
                height: 13px;
                width: 13px;
            }
            QCheckBox::indicator:unchecked:hover {
                background-color: %(button)s;
            }
            QCheckBox::indicator:unchecked:pressed {
                background-color: %(darker)s;
            }
            QCheckBox::indicator:checked {
                background-color: %(darker)s;
            }
            QCheckBox::indicator:checked:hover {
                background-color: %(button)s;
            }
            QCheckBox::indicator:checked:pressed {
                background-color: %(field)s;
            }

            /* progress bar */
            QProgressBar {
                background-color: %(field)s;
                border: 1px solid %(darker)s;
            }
            QProgressBar::chunk {
                background-color: %(button)s;
                width: 1px;
            }

            /* spin box */
            QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
                background-color: transparent;
            }
            QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {
                border-style: solid;
                height: 0;
                width: 0;
            }
            QAbstractSpinBox::up-arrow {
                border-color: %(field)s %(field)s %(darker)s %(field)s;
                border-width: 0 3px 4px 3px;
            }
            QAbstractSpinBox::up-arrow:hover {
                border-color: %(field)s %(field)s %(button)s %(field)s;
                border-width: 0 3px 4px 3px;
            }
            QAbstractSpinBox::down-arrow {
                border-color: %(darker)s %(field)s %(field)s %(field)s;
                border-width: 4px 3px 0 3px;
            }
            QAbstractSpinBox::down-arrow:hover {
                border-color: %(button)s %(field)s %(field)s %(field)s;
                border-width: 4px 3px 0 3px;
            }

            /* dialogs */
            QDialog > QFrame {
                margin: 6px 6px 6px 6px;
            }

            """ % dict(background=background,
                       field=field,
                       button=color_rgb,
                       darker=darker_rgb,
                       lighter=lighter_rgb,
                       grayed=grayed,
                       button_text=button_text,
                       field_text=field_text
                       )


def get_all_themes():
    return [
        Theme("default", N_("Default"), False,
              EStylesheet.DEFAULT, None),
        Theme("flat_light_blue", N_("Flat light blue"),
              False, EStylesheet.FLAT, "#637fd9"),
        Theme("flat_light_red", N_("Flat light red"),
              False, EStylesheet.FLAT, "#cc5452"),
        Theme("flat_light_grey", N_("Flat light grey"),
              False, EStylesheet.FLAT, "#404454"),
        Theme("flat_light_green", N_("Flat light green"),
              False, EStylesheet.FLAT, "#9bc562"),
        Theme("flat_dark_blue", N_("Flat dark blue"),
              True, EStylesheet.FLAT, "#637fd9"),
        Theme("flat_dark_red", N_("Flat dark red"),
              True, EStylesheet.FLAT, "#cc5452"),
        Theme("flat_dark_grey", N_("Flat dark grey"),
              True, EStylesheet.FLAT, "#aaaaaa"),
        Theme("flat_dark_green", N_("Flat dark green"),
              True, EStylesheet.FLAT, "#9bc562")
    ]


def find_theme(name):
    themes = get_all_themes()
    for item in themes:
        if item.name == name:
            return item
    return themes[0]
