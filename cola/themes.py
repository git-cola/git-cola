"""Provides themes generator"""
from __future__ import absolute_import, division, unicode_literals

from qtpy import QtGui

from .i18n import N_
from .widgets import defs
from . import icons
from . import qtutils


class EStylesheet(object):
    DEFAULT = 1
    FLAT = 2


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
            return self.style_sheet_flat()
        else:
            return self.style_sheet_default(app_palette)

    def build_palette(self, app_palette):
        QPalette = QtGui.QPalette
        palette_dark = app_palette.color(QPalette.Base).lightnessF() < 0.5

        if palette_dark and self.is_dark:
            return app_palette
        if not palette_dark and not self.is_dark:
            return app_palette
        if self.is_dark:
            bg_color = QtGui.QColor("#202025")
        else:
            bg_color = QtGui.QColor("#edeef3")

        txt_color = QtGui.QColor("#777")
        palette = QPalette(bg_color)
        palette.setColor(QPalette.Base, bg_color)
        palette.setColor(QPalette.Disabled, QPalette.Text, txt_color)
        return palette

    @staticmethod
    def style_sheet_default(palette):
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

    def style_sheet_flat(self):
        main_color = self.main_color
        color = QtGui.QColor(main_color)
        color_rgb = qtutils.rgb_css(color)

        if self.is_dark:
            background = '#2e2f30'
            field = '#383a3c'
            grayed = '#06080a'
            button_text = '#000000'
            field_text = '#d0d0d0'
            darker = qtutils.hsl_css(
                color.hslHueF(),
                color.hslSaturationF()*0.3,
                color.lightnessF()*1.3
            )
            lighter = qtutils.hsl_css(
                color.hslHueF(),
                color.hslSaturationF()*0.4,
                color.lightnessF()*0.55
            )
            focus = qtutils.hsl_css(
                color.hslHueF(),
                color.hslSaturationF() * 3,
                0.09
            )
        else:
            background = '#edeef3'
            field = '#ffffff'
            grayed = '#a2a2b0'
            button_text = '#ffffff'
            field_text = '#000000'
            darker = qtutils.hsl_css(
                color.hslHueF(),
                color.hslSaturationF(),
                color.lightnessF()*0.4
            )
            lighter = qtutils.hsl_css(
                color.hslHueF(),
                color.hslSaturationF()*2,
                0.92
            )
            focus = qtutils.hsl_css(
                color.hslHueF(),
                color.hslSaturationF(),
                color.lightnessF()
            )

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
            QWidget:disabled {
                border-color: %(grayed)s;
                color: %(grayed)s;
            }
            QDockWidget > QFrame {
                margin: 0 2px 2px 2px;
                min-height: 40px;
            }
            QPlainTextEdit, QLineEdit, QTextEdit, QAbstractItemView,
            QStackedWidget, QAbstractSpinBox {
                background-color: %(field)s;
                border-color: %(grayed)s;
                border-style: solid;
                border-width: 1px;
            }
            QAbstractItemView::item:selected {
                background-color: %(lighter)s;
            }
            QAbstractItemView::item:hover {
                background-color: %(lighter)s;
            }
            QWidget:focus {
                border-color: %(focus)s;
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
            QPushButton[flat="true"], QToolButton {
                background-color: transparent;
                border-radius: 0px;
            }
            QPushButton[flat="true"] {
                margin-bottom: 10px;
            }
            QPushButton:hover, QToolButton:hover {
               background-color: %(darker)s;
            }
            QPushButton[flat="false"]:pressed, QToolButton:pressed {
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
                background: %(button)s;
            }
            QMenuBar::item:pressed {
                background: %(button)s;
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
                background-color: %(field)s;
                border-color: %(grayed)s;
                border-style: solid;
                color: %(field_text)s;
                border-radius: 0px;
                border-width: 1px;
                margin-bottom: 1px;
                padding: 0 5px;
            }
            QComboBox::drop-down {
                border-color: %(field_text)s %(field)s %(field)s %(field)s;
                border-style: solid;
                subcontrol-position: right;
                border-width: 4px 3px 0 3px;
                height: 0;
                margin-right: 5px;
                width: 0;
            }
            QComboBox::drop-down:hover {
                border-color: %(button)s %(field)s %(field)s %(field)s;
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
            QScrollBar::sub-line:horizontal { /*required by a buggy Qt version*/
                subcontrol-position: left;
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
                margin: 2px 2px 2px 2px;
            }

            /* headers */
            QHeaderView {
                color: %(field_text)s;
                border-style: solid;
                border-width: 0 0 1px 0;
                border-color: %(grayed)s;
            }
            QHeaderView::section {
                border-style: solid;
                border-right: 1px solid %(grayed)s;
                background-color: %(background)s;
                color: %(field_text)s;
                padding-left: 4px;
            }

            /* headers */
            QHeaderView {
                color: %(field_text)s;
                border-style: solid;
                border-width: 0 0 1px 0;
                border-color: %(grayed)s;
            }
            QHeaderView::section {
                border-style: solid;
                border-right: 1px solid %(grayed)s;
                background-color: %(background)s;
                color: %(field_text)s;
                padding-left: 4px;
            }

            """ % dict(background=background,
                       field=field,
                       button=color_rgb,
                       darker=darker,
                       lighter=lighter,
                       grayed=grayed,
                       button_text=button_text,
                       field_text=field_text,
                       focus=focus
                       )


def get_all_themes():
    return [
        Theme('default', N_('Default'), False,
              EStylesheet.DEFAULT, None),
        Theme('flat-light-blue', N_('Flat light blue'),
              False, EStylesheet.FLAT, '#5271cc'),
        Theme('flat-light-red', N_('Flat light red'),
              False, EStylesheet.FLAT, '#cc5452'),
        Theme('flat-light-grey', N_('Flat light grey'),
              False, EStylesheet.FLAT, '#707478'),
        Theme('flat-light-green', N_('Flat light green'),
              False, EStylesheet.FLAT, '#42a65c'),
        Theme('flat-dark-blue', N_('Flat dark blue'),
              True, EStylesheet.FLAT, '#5271cc'),
        Theme('flat-dark-red', N_('Flat dark red'),
              True, EStylesheet.FLAT, '#cc5452'),
        Theme('flat-dark-grey', N_('Flat dark grey'),
              True, EStylesheet.FLAT, '#aaaaaa'),
        Theme('flat-dark-green', N_('Flat dark green'),
              True, EStylesheet.FLAT, '#42a65c')
    ]


def themes_map():
    result = dict()
    items = get_all_themes()
    for item in items:
        result[item.hr_name] = item.name

    return result


def find_theme(name):
    themes = get_all_themes()
    for item in themes:
        if item.name == name:
            return item
    return themes[0]
