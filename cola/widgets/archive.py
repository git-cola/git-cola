"""Git Archive dialog"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..git import STDOUT
from ..i18n import N_
from ..interaction import Interaction
from .. import cmds
from .. import core
from .. import icons
from .. import qtutils
from .text import LineEdit
from .standard import Dialog
from . import defs


class ExpandableGroupBox(QtWidgets.QGroupBox):

    expanded = Signal(bool)

    def __init__(self, parent=None):
        QtWidgets.QGroupBox.__init__(self, parent)
        self.setFlat(True)
        self.is_expanded = True
        self.click_pos = None
        self.arrow_icon_size = defs.small_icon

    def set_expanded(self, expanded):
        if expanded == self.is_expanded:
            self.expanded.emit(expanded)
            return
        self.is_expanded = expanded
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.setHidden(not expanded)
        self.expanded.emit(expanded)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            option = QtWidgets.QStyleOptionGroupBox()
            self.initStyleOption(option)
            icon_size = defs.small_icon
            button_area = QtCore.QRect(0, 0, icon_size, icon_size)
            offset = icon_size + defs.spacing
            adjusted = option.rect.adjusted(0, 0, -offset, 0)
            top_left = adjusted.topLeft()
            button_area.moveTopLeft(QtCore.QPoint(top_left))
            self.click_pos = event.pos()
        QtWidgets.QGroupBox.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.click_pos == event.pos():
            self.set_expanded(not self.is_expanded)
        QtWidgets.QGroupBox.mouseReleaseEvent(self, event)

    def paintEvent(self, _event):
        painter = QtWidgets.QStylePainter(self)
        option = QtWidgets.QStyleOptionGroupBox()
        self.initStyleOption(option)
        painter.save()
        painter.translate(self.arrow_icon_size + defs.spacing, 0)
        painter.drawText(option.rect, Qt.AlignLeft, self.title())
        painter.restore()

        style = QtWidgets.QStyle
        point = option.rect.adjusted(0, -4, 0, 0).topLeft()
        icon_size = self.arrow_icon_size
        option.rect = QtCore.QRect(point.x(), point.y(), icon_size, icon_size)
        if self.is_expanded:
            painter.drawPrimitive(style.PE_IndicatorArrowDown, option)
        else:
            painter.drawPrimitive(style.PE_IndicatorArrowRight, option)


def save_archive(context):
    oid = context.git.rev_parse('HEAD')[STDOUT]
    show_save_dialog(context, oid, parent=qtutils.active_window())


def show_save_dialog(context, oid, parent=None):
    shortoid = oid[:7]
    dlg = Archive(context, oid, shortoid, parent=parent)
    dlg.show()
    if dlg.exec_() != dlg.Accepted:
        return None
    return dlg


class Archive(Dialog):
    def __init__(self, context, ref, shortref=None, parent=None):
        Dialog.__init__(self, parent=parent)
        self.context = context
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        # input
        self.ref = ref
        if shortref is None:
            shortref = ref

        # outputs
        self.fmt = None

        filename = '%s-%s' % (os.path.basename(core.getcwd()), shortref)
        self.prefix = filename + '/'
        self.filename = filename

        # widgets
        self.setWindowTitle(N_('Save Archive'))

        self.filetext = LineEdit()
        self.filetext.set_value(self.filename)

        self.browse = qtutils.create_toolbutton(icon=icons.file_zip())

        stdout = context.git.archive('--list')[STDOUT]
        self.format_strings = stdout.rstrip().splitlines()
        self.format_combo = qtutils.combo(self.format_strings)

        self.close_button = qtutils.close_button()
        self.save_button = qtutils.create_button(
            text=N_('Save'), icon=icons.save(), default=True
        )
        self.prefix_label = QtWidgets.QLabel()
        self.prefix_label.setText(N_('Prefix'))
        self.prefix_text = LineEdit()
        self.prefix_text.set_value(self.prefix)

        self.prefix_group = ExpandableGroupBox()
        self.prefix_group.setTitle(N_('Advanced'))

        # layouts
        self.filelayt = qtutils.hbox(
            defs.no_margin, defs.spacing, self.browse, self.filetext, self.format_combo
        )

        self.prefixlayt = qtutils.hbox(
            defs.margin, defs.spacing, self.prefix_label, self.prefix_text
        )
        self.prefix_group.setLayout(self.prefixlayt)
        self.prefix_group.set_expanded(False)

        self.btnlayt = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.close_button,
            qtutils.STRETCH,
            self.save_button,
        )

        self.mainlayt = qtutils.vbox(
            defs.margin,
            defs.no_spacing,
            self.filelayt,
            self.prefix_group,
            qtutils.STRETCH,
            self.btnlayt,
        )
        self.setLayout(self.mainlayt)

        # initial setup; done before connecting to avoid
        # signal/slot side-effects
        if 'tar.gz' in self.format_strings:
            idx = self.format_strings.index('tar.gz')
        elif 'zip' in self.format_strings:
            idx = self.format_strings.index('zip')
        else:
            idx = 0
        self.format_combo.setCurrentIndex(idx)
        self.update_format(idx)

        # connections
        # pylint: disable=no-member
        self.filetext.textChanged.connect(self.filetext_changed)
        self.prefix_text.textChanged.connect(self.prefix_text_changed)
        self.format_combo.currentIndexChanged.connect(self.update_format)
        self.prefix_group.expanded.connect(self.prefix_group_expanded)
        self.accepted.connect(self.archive_saved)

        qtutils.connect_button(self.browse, self.choose_filename)
        qtutils.connect_button(self.close_button, self.reject)
        qtutils.connect_button(self.save_button, self.save_archive)

        self.init_size(parent=parent)

    def archive_saved(self):
        context = self.context
        ref = self.ref
        fmt = self.fmt
        prefix = self.prefix
        filename = self.filename

        cmds.do(cmds.Archive, context, ref, fmt, prefix, filename)
        Interaction.information(
            N_('File Saved'), N_('File saved to "%s"') % self.filename
        )

    def save_archive(self):
        filename = self.filename
        if not filename:
            return
        if core.exists(filename):
            title = N_('Overwrite File?')
            msg = N_('The file "%s" exists and will be overwritten.') % filename
            info_txt = N_('Overwrite "%s"?') % filename
            ok_txt = N_('Overwrite')
            if not Interaction.confirm(
                title, msg, info_txt, ok_txt, default=False, icon=icons.save()
            ):
                return
        self.accept()

    def choose_filename(self):
        filename = qtutils.save_as(self.filename)
        if not filename:
            return
        self.filetext.setText(filename)
        self.update_format(self.format_combo.currentIndex())

    def filetext_changed(self, filename):
        self.filename = filename
        self.save_button.setEnabled(bool(self.filename))
        prefix = self.strip_exts(os.path.basename(self.filename)) + '/'
        self.prefix_text.setText(prefix)

    def prefix_text_changed(self, prefix):
        self.prefix = prefix

    def strip_exts(self, text):
        for format_string in self.format_strings:
            ext = '.' + format_string
            if text.endswith(ext):
                return text[: -len(ext)]
        return text

    def update_format(self, idx):
        self.fmt = self.format_strings[idx]
        text = self.strip_exts(self.filetext.text())
        self.filename = '%s.%s' % (text, self.fmt)
        self.filetext.setText(self.filename)
        self.filetext.setFocus()
        if '/' in text:
            start = text.rindex('/') + 1
        else:
            start = 0
        self.filetext.setSelection(start, len(text) - start)

    def prefix_group_expanded(self, expanded):
        if expanded:
            self.prefix_text.setFocus()
        else:
            self.filetext.setFocus()
