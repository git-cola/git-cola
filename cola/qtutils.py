"""Miscellaneous Qt utility functions."""
import os

from qtpy import compat
from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from . import core
from . import hotkeys
from . import icons
from . import utils
from .i18n import N_
from .compat import int_types
from .compat import ustr
from .models import prefs
from .widgets import defs


STRETCH = object()
SKIPPED = object()


def active_window():
    """Return the active window for the current application"""
    return QtWidgets.QApplication.activeWindow()


def current_palette():
    """Return the QPalette for the current application"""
    return QtWidgets.QApplication.instance().palette()


def connect_action(action, func):
    """Connect an action to a function"""
    action.triggered[bool].connect(lambda x: func(), type=Qt.QueuedConnection)


def connect_action_bool(action, func):
    """Connect a triggered(bool) action to a function"""
    action.triggered[bool].connect(func, type=Qt.QueuedConnection)


def connect_button(button, func):
    """Connect a button to a function"""
    # Some versions of Qt send the `bool` argument to the clicked callback,
    # and some do not.  The lambda consumes all callback-provided arguments.
    button.clicked.connect(lambda *args, **kwargs: func(), type=Qt.QueuedConnection)


def connect_checkbox(widget, func):
    """Connect a checkbox to a function taking bool"""
    widget.clicked.connect(lambda value: func(value), type=Qt.QueuedConnection)


def connect_released(button, func):
    """Connect a button to a function"""
    button.released.connect(func, type=Qt.QueuedConnection)


def button_action(button, action):
    """Make a button trigger an action"""
    connect_button(button, action.trigger)


def connect_toggle(toggle, func):
    """Connect a toggle button to a function"""
    toggle.toggled.connect(func, type=Qt.QueuedConnection)


def disconnect(signal):
    """Disconnect signal from all slots"""
    try:
        signal.disconnect()
    except TypeError:  # allow unconnected slots
        pass


def get(widget, default=None):
    """Query a widget for its python value"""
    if hasattr(widget, 'isChecked'):
        value = widget.isChecked()
    elif hasattr(widget, 'value'):
        value = widget.value()
    elif hasattr(widget, 'text'):
        value = widget.text()
    elif hasattr(widget, 'toPlainText'):
        value = widget.toPlainText()
    elif hasattr(widget, 'sizes'):
        value = widget.sizes()
    elif hasattr(widget, 'date'):
        value = widget.date().toString(Qt.ISODate)
    else:
        value = default
    return value


def hbox(margin, spacing, *items):
    """Create an HBoxLayout with the specified sizes and items"""
    return box(QtWidgets.QHBoxLayout, margin, spacing, *items)


def vbox(margin, spacing, *items):
    """Create a VBoxLayout with the specified sizes and items"""
    return box(QtWidgets.QVBoxLayout, margin, spacing, *items)


def buttongroup(*items):
    """Create a QButtonGroup for the specified items"""
    group = QtWidgets.QButtonGroup()
    for i in items:
        group.addButton(i)
    return group


def set_margin(layout, margin):
    """Set the content margins for a layout"""
    layout.setContentsMargins(margin, margin, margin, margin)


def box(cls, margin, spacing, *items):
    """Create a QBoxLayout with the specified sizes and items"""
    stretch = STRETCH
    skipped = SKIPPED
    layout = cls()
    layout.setSpacing(spacing)
    set_margin(layout, margin)

    for i in items:
        if isinstance(i, QtWidgets.QWidget):
            layout.addWidget(i)
        elif isinstance(
            i,
            (
                QtWidgets.QHBoxLayout,
                QtWidgets.QVBoxLayout,
                QtWidgets.QFormLayout,
                QtWidgets.QLayout,
            ),
        ):
            layout.addLayout(i)
        elif i is stretch:
            layout.addStretch()
        elif i is skipped:
            continue
        elif isinstance(i, int_types):
            layout.addSpacing(i)

    return layout


def form(margin, spacing, *widgets):
    """Create a QFormLayout with the specified sizes and items"""
    layout = QtWidgets.QFormLayout()
    layout.setSpacing(spacing)
    layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
    set_margin(layout, margin)

    for idx, (name, widget) in enumerate(widgets):
        if isinstance(name, (str, ustr)):
            layout.addRow(name, widget)
        else:
            layout.setWidget(idx, QtWidgets.QFormLayout.LabelRole, name)
            layout.setWidget(idx, QtWidgets.QFormLayout.FieldRole, widget)

    return layout


def grid(margin, spacing, *widgets):
    """Create a QGridLayout with the specified sizes and items"""
    layout = QtWidgets.QGridLayout()
    layout.setSpacing(spacing)
    set_margin(layout, margin)

    for row in widgets:
        item = row[0]
        if isinstance(item, QtWidgets.QWidget):
            layout.addWidget(*row)
        elif isinstance(item, QtWidgets.QLayoutItem):
            layout.addItem(*row)

    return layout


def splitter(orientation, *widgets):
    """Create a splitter over the specified widgets

    :param orientation: Qt.Horizontal or Qt.Vertical

    """
    layout = QtWidgets.QSplitter()
    layout.setOrientation(orientation)
    layout.setHandleWidth(defs.handle_width)
    layout.setChildrenCollapsible(True)

    for idx, widget in enumerate(widgets):
        layout.addWidget(widget)
        layout.setStretchFactor(idx, 1)

    # Workaround for Qt not setting the WA_Hover property for QSplitter
    # Cf. https://bugreports.qt.io/browse/QTBUG-13768
    layout.handle(1).setAttribute(Qt.WA_Hover)

    return layout


def label(text=None, align=None, fmt=None, selectable=True, tooltip=None, parent=None):
    """Create a QLabel with the specified properties"""
    widget = QtWidgets.QLabel(parent)
    if align is not None:
        widget.setAlignment(align)
    if fmt is not None:
        widget.setTextFormat(fmt)
    if selectable:
        widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
        widget.setOpenExternalLinks(True)
    if text:
        widget.setText(text)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def plain_text_label(text=None, align=None, selectable=True, tooltip=None, parent=None):
    """Create a QLabel that display plain text"""
    return label(
        text=text,
        align=align,
        fmt=Qt.PlainText,
        selectable=selectable,
        tooltip=tooltip,
        parent=parent,
    )


def pixmap_label(icon, width, height=None, tooltip=None, parent=None):
    """Create a QLabel that displays a pixmap"""
    if height is None:
        height = width
    widget = QtWidgets.QLabel(parent)
    pixmap = icon.pixmap(width, height)
    widget.setPixmap(pixmap)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


class ComboBox(QtWidgets.QComboBox):
    """Custom read-only combo box with a convenient API"""

    def __init__(self, items=None, editable=False, parent=None, transform=None):
        super().__init__(parent)
        self.setEditable(editable)
        self.transform = transform
        self.item_data = []
        if items:
            self.addItems(items)
            self.item_data.extend(items)

    def set_index(self, idx):
        idx = utils.clamp(idx, 0, self.count() - 1)
        self.setCurrentIndex(idx)

    def set_index_if_enabled(self, idx):
        """Set the current index while ignoring disabled items"""
        idx = utils.clamp(idx, 0, self.count() - 1)
        model = self.model()
        if model is None:
            return
        item = model.item(idx)
        if item is None:
            return
        if item.isEnabled():
            self.setCurrentIndex(idx)

    def current_index(self):
        """Return the index of the currently selected item"""
        return self.currentIndex()

    def set_item_enabled(self, idx, enabled):
        """Enable an item on this combobox"""
        model = self.model()
        if model is None:
            return
        item = model.item(idx)
        if item is None:
            return
        item.setEnabled(enabled)
        # If the current item became disabled then select the first non-disabled item.
        if not enabled and idx == self.currentIndex():
            for item_idx in range(len(self.item_data)):
                item = model.item(item_idx)
                if item is not None and item.isEnabled():
                    self.setCurrentIndex(item_idx)
                    break

    def add_item(self, text, data=None):
        if data is None:
            data = text
        self.addItem(text)
        self.item_data.append(data)

    def value(self):
        """Return the current data"""
        return self.item_data[self.currentIndex()]

    def values(self):
        """Return all of the valid values"""
        return self.item_data

    def set_value(self, value):
        """Set the value to one of the known values"""
        if self.transform:
            value = self.transform(value)
        try:
            index = self.item_data.index(value)
        except ValueError:
            index = 0
        self.setCurrentIndex(index)

    def set_current_value(self, value):
        """Set the current value irrespective of the preset values"""
        self.setCurrentText(value)

    def current_value(self):
        """Return the current value irrespective of the preset values"""
        return self.currentText()


def combo(items, editable=False, tooltip='', parent=None):
    """Create a readonly (by default) combo box from a list of items"""
    combobox = ComboBox(editable=editable, items=items, parent=parent)
    if tooltip:
        combobox.setToolTip(tooltip)
    return combobox


def combo_mapped(data, editable=False, transform=None, parent=None):
    """Create a readonly (by default) combo box from a list of items"""
    widget = ComboBox(editable=editable, transform=transform, parent=parent)
    for k, v in data:
        widget.add_item(k, data=v)
    return widget


def textbrowser(text=None):
    """Create a QTextBrowser for the specified text"""
    widget = QtWidgets.QTextBrowser()
    widget.setOpenExternalLinks(True)
    if text:
        widget.setText(text)
    return widget


def link(url, text, palette=None):
    if palette is None:
        palette = QtGui.QPalette()

    color = palette.color(QtGui.QPalette.WindowText)
    rgb_color = f'rgb({color.red()}, {color.green()}, {color.blue()})'
    scope = {'rgb': rgb_color, 'text': text, 'url': url}

    return (
        """
        <a style="font-style: italic; text-decoration: none; color: %(rgb)s;"
            href="%(url)s">
            %(text)s
        </a>
    """
        % scope
    )


def add_completer(widget, items):
    """Add simple completion to a widget"""
    completer = QtWidgets.QCompleter(items, widget)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
    widget.setCompleter(completer)


def prompt(msg, title=None, text='', parent=None):
    """Presents the user with an input widget and returns the input."""
    if title is None:
        title = msg
    if parent is None:
        parent = active_window()
    result = QtWidgets.QInputDialog.getText(
        parent, title, msg, QtWidgets.QLineEdit.Normal, text
    )
    return (result[0], result[1])


def prompt_n(msg, inputs):
    """Presents the user with N input widgets and returns the results"""
    dialog = QtWidgets.QDialog(active_window())
    dialog.setWindowModality(Qt.WindowModal)
    dialog.setWindowTitle(msg)

    long_value = msg
    for k, v in inputs:
        if len(k + v) > len(long_value):
            long_value = k + v

    min_width = min(720, text_width(dialog.font(), long_value) + 100)
    dialog.setMinimumWidth(min_width)

    ok_b = ok_button(msg, enabled=False)
    close_b = close_button()

    form_widgets = []

    def get_values():
        return [pair[1].text().strip() for pair in form_widgets]

    for name, value in inputs:
        lineedit = QtWidgets.QLineEdit()
        # Enable the OK button only when all fields have been populated
        lineedit.textChanged.connect(
            lambda x: ok_b.setEnabled(all(get_values())), type=Qt.QueuedConnection
        )
        if value:
            lineedit.setText(value)
        form_widgets.append((name, lineedit))

    # layouts
    form_layout = form(defs.no_margin, defs.button_spacing, *form_widgets)
    button_layout = hbox(defs.no_margin, defs.button_spacing, STRETCH, close_b, ok_b)
    main_layout = vbox(defs.margin, defs.button_spacing, form_layout, button_layout)
    dialog.setLayout(main_layout)

    # connections
    connect_button(ok_b, dialog.accept)
    connect_button(close_b, dialog.reject)

    accepted = dialog.exec_() == QtWidgets.QDialog.Accepted
    text = get_values()
    success = accepted and all(text)
    return (success, text)


def standard_item_type_value(value):
    """Return a custom UserType for use in QTreeWidgetItem.type() overrides"""
    return custom_item_type_value(QtGui.QStandardItem, value)


def graphics_item_type_value(value):
    """Return a custom UserType for use in QGraphicsItem.type() overrides"""
    return custom_item_type_value(QtWidgets.QGraphicsItem, value)


def custom_item_type_value(cls, value):
    """Return a custom cls.UserType for use in cls.type() overrides"""
    user_type = enum_value(cls.UserType)
    return user_type + value


def enum_value(value):
    """Qt6 has enums with an inner '.value' attribute."""
    if hasattr(value, 'value'):
        value = value.value
    return value


class TreeWidgetItem(QtWidgets.QTreeWidgetItem):
    TYPE = standard_item_type_value(101)

    def __init__(self, path, icon, deleted):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.path = path
        self.deleted = deleted
        self.setIcon(0, icons.from_name(icon))
        self.setText(0, path)

    def type(self):
        return self.TYPE


def paths_from_indexes(model, indexes, item_type=TreeWidgetItem.TYPE, item_filter=None):
    """Return paths from a list of QStandardItemModel indexes"""
    items = [model.itemFromIndex(i) for i in indexes]
    return paths_from_items(items, item_type=item_type, item_filter=item_filter)


def _true_filter(_value):
    return True


def paths_from_items(items, item_type=TreeWidgetItem.TYPE, item_filter=None):
    """Return a list of paths from a list of items"""
    if item_filter is None:
        item_filter = _true_filter
    return [i.path for i in items if i.type() == item_type and item_filter(i)]


def tree_selection(tree_item, items):
    """Returns an array of model items that correspond to the selected
    QTreeWidgetItem children"""
    selected = []
    count = min(tree_item.childCount(), len(items))
    for idx in range(count):
        if tree_item.child(idx).isSelected():
            selected.append(items[idx])

    return selected


def tree_selection_items(tree_item):
    """Returns selected widget items"""
    selected = []
    for idx in range(tree_item.childCount()):
        child = tree_item.child(idx)
        if child.isSelected():
            selected.append(child)

    return selected


def selected_item(list_widget, items):
    """Returns the model item that corresponds to the selected QListWidget
    row."""
    widget_items = list_widget.selectedItems()
    if not widget_items:
        return None
    widget_item = widget_items[0]
    row = list_widget.row(widget_item)
    if row < len(items):
        item = items[row]
    else:
        item = None
    return item


def selected_items(list_widget, items):
    """Returns an array of model items that correspond to the selected
    QListWidget rows."""
    item_count = len(items)
    selected = []
    for widget_item in list_widget.selectedItems():
        row = list_widget.row(widget_item)
        if row < item_count:
            selected.append(items[row])
    return selected


def open_file(title, directory=None):
    """Creates an Open File dialog and returns a filename."""
    result = compat.getopenfilename(
        parent=active_window(), caption=title, basedir=directory
    )
    return result[0]


def open_files(title, directory=None, filters=''):
    """Creates an Open File dialog and returns a list of filenames."""
    result = compat.getopenfilenames(
        parent=active_window(), caption=title, basedir=directory, filters=filters
    )
    return result[0]


def _enum_value(value):
    """Resolve Qt6 enum values"""
    if hasattr(value, 'value'):
        return value.value
    return value


def opendir_dialog(caption, path):
    """Prompts for a directory path"""
    options = QtWidgets.QFileDialog.Option(
        _enum_value(QtWidgets.QFileDialog.Directory)
        | _enum_value(QtWidgets.QFileDialog.DontResolveSymlinks)
        | _enum_value(QtWidgets.QFileDialog.ReadOnly)
        | _enum_value(QtWidgets.QFileDialog.ShowDirsOnly)
    )
    return compat.getexistingdirectory(
        parent=active_window(), caption=caption, basedir=path, options=options
    )


def save_as(filename, title='Save As...'):
    """Creates a Save File dialog and returns a filename."""
    result = compat.getsavefilename(
        parent=active_window(), caption=title, basedir=filename
    )
    return result[0]


def existing_file(directory, title='Open File...'):
    """Creates an OpenSave File dialog and returns a filename."""
    result = compat.getopenfilename(
        parent=active_window(), caption=title, basedir=directory
    )
    return result[0]


def copy_path(filename, absolute=True):
    """Copy a filename to the clipboard"""
    if filename is None:
        return
    if absolute:
        filename = core.abspath(filename)
    set_clipboard(filename)


def set_clipboard(text):
    """Sets the copy/paste buffer to text."""
    if not text:
        return
    clipboard = QtWidgets.QApplication.clipboard()
    clipboard.setText(text, QtGui.QClipboard.Clipboard)
    if not utils.is_darwin() and not utils.is_win32():
        clipboard.setText(text, QtGui.QClipboard.Selection)
    persist_clipboard()


def persist_clipboard():
    """Persist the clipboard

    X11 stores only a reference to the clipboard data.
    Send a clipboard event to force a copy of the clipboard to occur.
    This ensures that the clipboard is present after git-cola exits.
    Otherwise, the reference is destroyed on exit.

    C.f. https://stackoverflow.com/questions/2007103/how-can-i-disable-clear-of-clipboard-on-exit-of-pyqt4-application

    """  # noqa
    clipboard = QtWidgets.QApplication.clipboard()
    event = QtCore.QEvent(QtCore.QEvent.Clipboard)
    QtWidgets.QApplication.sendEvent(clipboard, event)


def add_action_bool(widget, text, func, checked, *shortcuts):
    tip = text
    action = _add_action(widget, text, tip, func, connect_action_bool, *shortcuts)
    action.setCheckable(True)
    action.setChecked(checked)
    return action


def add_action(widget, text, func, *shortcuts):
    """Create a QAction and bind it to the `func` callback and hotkeys"""
    tip = text
    return _add_action(widget, text, tip, func, connect_action, *shortcuts)


def add_action_with_icon(widget, icon, text, func, *shortcuts):
    """Create a QAction using a custom icon bound to the `func` callback and hotkeys"""
    tip = text
    action = _add_action(widget, text, tip, func, connect_action, *shortcuts)
    action.setIcon(icon)
    return action


def add_action_with_tooltip(widget, text, tip, func, *shortcuts):
    """Create an action with a tooltip"""
    return _add_action(widget, text, tip, func, connect_action, *shortcuts)


def menu_separator(widget, text=''):
    """Return a QAction whose isSeparator() returns true. Used in context menus"""
    action = QtWidgets.QAction(text, widget)
    action.setSeparator(True)
    return action


def _add_action(widget, text, tip, func, connect, *shortcuts):
    action = QtWidgets.QAction(text, widget)
    if hasattr(action, 'setIconVisibleInMenu'):
        action.setIconVisibleInMenu(True)
    if tip:
        action.setStatusTip(tip)
    connect(action, func)
    if shortcuts:
        action.setShortcuts(shortcuts)
        if hasattr(Qt, 'WidgetWithChildrenShortcut'):
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        widget.addAction(action)
    return action


def set_selected_item(widget, idx):
    """Sets the currently selected item to the item at index idx."""
    if isinstance(widget, QtWidgets.QTreeWidget):
        item = widget.topLevelItem(idx)
        if item:
            item.setSelected(True)
            widget.setCurrentItem(item)


def add_items(widget, items):
    """Adds items to a widget."""
    for item in items:
        if item is None:
            continue
        widget.addItem(item)


def set_items(widget, items):
    """Clear the existing widget contents and set the new items."""
    widget.clear()
    add_items(widget, items)


def create_treeitem(filename, staged=False, deleted=False, untracked=False):
    """Given a filename, return a TreeWidgetItem for a status widget

    "staged", "deleted, and "untracked" control which icon is used.

    """
    icon_name = icons.status(filename, deleted, staged, untracked)
    icon = icons.name_from_basename(icon_name)
    return TreeWidgetItem(filename, icon, deleted=deleted)


def add_close_action(widget):
    """Adds close action and shortcuts to a widget."""
    return add_action(widget, N_('Close...'), widget.close, hotkeys.CLOSE, hotkeys.QUIT)


def app():
    """Return the current application"""
    return QtWidgets.QApplication.instance()


def desktop_size():
    rect = app().primaryScreen().geometry()
    return (rect.width(), rect.height())


def center_on_screen(widget):
    """Move widget to the center of the default screen"""
    width, height = desktop_size()
    center_x = width // 2
    center_y = height // 2
    widget.move(center_x - widget.width() // 2, center_y - widget.height() // 2)


def default_size(parent, width, height, use_parent_height=True):
    """Return the parent's size, or the provided defaults"""
    if parent is not None:
        width = parent.width()
        if use_parent_height:
            height = parent.height()
    return (width, height)


def default_monospace_font():
    if utils.is_darwin():
        family = 'Monaco'
    elif utils.is_win32():
        family = 'Courier'
    else:
        family = 'Monospace'
    mfont = QtGui.QFont()
    mfont.setFamily(family)
    return mfont


def diff_font_str(context):
    cfg = context.cfg
    font_str = cfg.get(prefs.FONTDIFF)
    if not font_str:
        font_str = default_monospace_font().toString()
    return font_str


def diff_font(context):
    return font_from_string(diff_font_str(context))


def font_from_string(string):
    qfont = QtGui.QFont()
    qfont.fromString(string)
    return qfont


def create_button(
    text='', layout=None, tooltip=None, icon=None, enabled=True, default=False
):
    """Create a button, set its title, and add it to the parent."""
    button = QtWidgets.QPushButton()
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.NoFocus)
    if text:
        button.setText(' ' + text)
    if icon is not None:
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(defs.small_icon, defs.small_icon))
    if tooltip is not None:
        button.setToolTip(tooltip)
    if layout is not None:
        layout.addWidget(button)
    if not enabled:
        button.setEnabled(False)
    if default:
        button.setDefault(True)
    return button


def tool_button():
    """Create a flat border-less button"""
    button = QtWidgets.QToolButton()
    button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.NoFocus)
    # Highlight colors
    palette = QtGui.QPalette()
    highlight = palette.color(QtGui.QPalette.Highlight)
    highlight_rgb = rgb_css(highlight)

    button.setStyleSheet(
        """
        /* No borders */
        QToolButton {
            border: none;
            background-color: none;
        }
        /* Hide the menu indicator */
        QToolButton::menu-indicator {
            image: none;
        }
        QToolButton:hover {
            border: %(border)spx solid %(highlight_rgb)s;
        }
    """
        % {
            'border': defs.border,
            'highlight_rgb': highlight_rgb,
        }
    )
    return button


def create_action_button(tooltip=None, icon=None, visible=None):
    """Create a small tool button for use in dock title widgets"""
    button = tool_button()
    if tooltip is not None:
        button.setToolTip(tooltip)
    if icon is not None:
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(defs.small_icon, defs.small_icon))
    if visible is not None:
        button.setVisible(visible)
    return button


def ok_button(text, default=True, enabled=True, icon=None):
    if icon is None:
        icon = icons.ok()
    return create_button(text=text, icon=icon, default=default, enabled=enabled)


def close_button(text=None, icon=None):
    text = text or N_('Close')
    icon = icons.mkicon(icon, icons.close)
    return create_button(text=text, icon=icon)


def edit_button(enabled=True, default=False):
    return create_button(
        text=N_('Edit'), icon=icons.edit(), enabled=enabled, default=default
    )


def refresh_button(enabled=True, default=False):
    return create_button(
        text=N_('Refresh'), icon=icons.sync(), enabled=enabled, default=default
    )


def checkbox(text='', tooltip='', checked=None):
    """Create a checkbox"""
    return _checkbox(QtWidgets.QCheckBox, text, tooltip, checked)


def radio(text='', tooltip='', checked=None):
    """Create a radio button"""
    return _checkbox(QtWidgets.QRadioButton, text, tooltip, checked)


def _checkbox(cls, text, tooltip, checked):
    """Create a widget and apply properties"""
    widget = cls()
    if text:
        widget.setText(text)
    if tooltip:
        widget.setToolTip(tooltip)
    if checked is not None:
        widget.setChecked(checked)
    return widget


class DockTitleBarWidget(QtWidgets.QFrame):
    """Provides a dockwidget titlebar that can be extended with custom widgets"""

    def __init__(self, parent, title, stretch=True, hide_title=False):
        QtWidgets.QFrame.__init__(self, parent)
        self.setAutoFillBackground(True)
        self.label = QtWidgets.QLabel(title, self)
        self.label.setCursor(Qt.OpenHandCursor)
        font = self.label.font()
        font.setPointSize(defs.action_text)
        self.label.setFont(font)
        if hide_title:
            self.label.hide()

        self.close_button = create_action_button(
            tooltip=N_('Close'), icon=icons.close()
        )

        self.toggle_button = create_action_button(
            tooltip=N_('Detach'), icon=icons.external()
        )
        self.toggle_button.hide()

        self.corner_layout = hbox(defs.no_margin, defs.spacing)
        self.title_layout = hbox(defs.no_margin, defs.button_spacing, self.label)

        if stretch:
            separator = STRETCH
        else:
            separator = SKIPPED

        self.main_layout = hbox(
            defs.small_margin,
            defs.titlebar_spacing,
            self.title_layout,
            separator,
            self.corner_layout,
            self.toggle_button,
            self.close_button,
        )
        self.main_layout.setAlignment(self.toggle_button, Qt.AlignTop)
        self.main_layout.setAlignment(self.close_button, Qt.AlignTop)
        self.setLayout(self.main_layout)

        connect_button(self.toggle_button, self.toggle_floating)
        connect_button(self.close_button, self.toggle_visibility)

    def toggle_floating(self):
        """Toggle between floating and embedded modes"""
        self.parent().setFloating(not self.parent().isFloating())

    def toggle_visibility(self):
        """Toggle visibility of the dock widget"""
        self.parent().toggleViewAction().trigger()

    def set_title(self, title):
        """Set the title text"""
        self.label.setText(title)

    def add_title_widget(self, widget):
        """Add widgets to the title area"""
        self.title_layout.addWidget(widget)

    def add_corner_widget(self, widget):
        """Add widgets to the corner area"""
        self.corner_layout.addWidget(widget)

    def update_floating(self):
        """Refresh the floating state"""
        self.set_floating(self.parent().isFloating())

    def set_floating(self, floating):
        """Update state in response to floating state changes"""
        if floating:
            tooltip = N_('Attach')
        else:
            tooltip = N_('Detach')
        self.toggle_button.setToolTip(tooltip)
        self.toggle_button.setVisible(floating)


def create_dock(
    name, title, parent, stretch=True, widget=None, func=None, hide_title=False
):
    """Create a dock widget and set it up accordingly."""
    dock = QtWidgets.QDockWidget(parent)
    dock.setWindowTitle(title)
    dock.setObjectName(name)
    titlebar = DockTitleBarWidget(dock, title, stretch=stretch, hide_title=hide_title)
    dock.setTitleBarWidget(titlebar)
    dock.setAutoFillBackground(True)
    dock.topLevelChanged.connect(titlebar.set_floating)
    if hasattr(parent, 'dockwidgets'):
        parent.dockwidgets.append(dock)
    if func:
        widget = func(dock)
    if widget:
        dock.setWidget(widget)
    return dock


def hide_dock(widget):
    widget.toggleViewAction().setChecked(False)
    widget.hide()


def create_menu(title, parent):
    """Create a menu and set its title."""
    qmenu = DebouncingMenu(title, parent)
    return qmenu


class DebouncingMenu(QtWidgets.QMenu):
    """Menu that debounces mouse release action i.e. stops it if occurred
    right after menu creation.

    Disables annoying behaviour when RMB is pressed to show menu, cursor is
    moved accidentally 1 px onto newly created menu and released causing to
    execute menu action
    """

    threshold_ms = 400

    def __init__(self, title, parent):
        QtWidgets.QMenu.__init__(self, title, parent)
        self.created_at = utils.epoch_millis()
        if hasattr(self, 'setToolTipsVisible'):
            self.setToolTipsVisible(True)

    def mouseReleaseEvent(self, event):
        threshold = DebouncingMenu.threshold_ms
        if (utils.epoch_millis() - self.created_at) > threshold:
            QtWidgets.QMenu.mouseReleaseEvent(self, event)


def add_menu(title, parent):
    """Create a menu and set its title."""
    menu = create_menu(title, parent)
    if hasattr(parent, 'addMenu'):
        parent.addMenu(menu)
    else:
        parent.addAction(menu.menuAction())
    return menu


def create_toolbutton(
    text=None,
    layout=None,
    tooltip=None,
    icon=None,
    icon_size=defs.default_icon,
    repeat=False,
):
    button = tool_button()
    if icon is not None:
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(icon_size, icon_size))
    if text is not None:
        button.setText(' ' + text)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    if tooltip is not None:
        button.setToolTip(tooltip)
    if repeat:
        button.setAutoRepeat(True)
    if layout is not None:
        layout.addWidget(button)
    return button


def create_toolbutton_with_callback(
    callback, text, icon, tooltip, layout=None, repeat=False
):
    """Create a tool button that runs the specified callback"""
    toolbutton = create_toolbutton(
        text=text, layout=layout, tooltip=tooltip, icon=icon, repeat=repeat
    )
    connect_button(toolbutton, callback)
    return toolbutton


def mimedata_from_paths(context, paths, include_urls=True):
    """Return mime data with a list of absolute path URLs

    Set `include_urls` to False to prevent URLs from being included
    in the mime data. This is useful in some terminals that do not gracefully handle
    multiple URLs being included in the payload.

    This allows the mime data to contain just plain a plain text value that we
    are able to format ourselves.

    Older versions of gnome-terminal expected a UTF-16 encoding, but that
    behavior is no longer needed.
    """  # noqa
    abspaths = [core.abspath(path) for path in paths]
    paths_text = core.list2cmdline(abspaths)

    # The text/x-moz-list format is always included by Qt, and doing
    # mimedata.removeFormat('text/x-moz-url') has no effect.
    # http://www.qtcentre.org/threads/44643-Dragging-text-uri-list-Qt-inserts-garbage
    #
    # Older versions of gnome-terminal expect UTF-16 encoded text, but other terminals,
    # e.g. terminator, expect UTF-8, so use cola.dragencoding to override the default.
    # NOTE: text/x-moz-url does not seem to be used/needed by modern versions of
    # gnome-terminal, kitty, and terminator.
    mimedata = QtCore.QMimeData()
    mimedata.setText(paths_text)
    if include_urls:
        urls = [QtCore.QUrl.fromLocalFile(path) for path in abspaths]
        encoding = context.cfg.get('cola.dragencoding', 'utf-16')
        encoded_text = core.encode(paths_text, encoding=encoding)
        mimedata.setUrls(urls)
        mimedata.setData('text/x-moz-url', encoded_text)

    return mimedata


def path_mimetypes(include_urls=True):
    """Return a list of mime types that we generate"""
    mime_types = [
        'text/plain',
        'text/plain;charset=utf-8',
    ]
    if include_urls:
        mime_types.append('text/uri-list')
        mime_types.append('text/x-moz-url')
    return mime_types


class BlockSignals:
    """Context manager for blocking a signals on a widget"""

    def __init__(self, *widgets):
        self.widgets = widgets
        self.values = []

    def __enter__(self):
        """Block Qt signals for all of the captured widgets"""
        self.values = [widget.blockSignals(True) for widget in self.widgets]
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore Qt signals when we exit the scope"""
        for widget, value in zip(self.widgets, self.values):
            widget.blockSignals(value)


class Channel(QtCore.QObject):
    finished = Signal(object)
    result = Signal(object)


class Task(QtCore.QRunnable):
    """Run a task in the background and return the result using a Channel"""

    def __init__(self):
        QtCore.QRunnable.__init__(self)

        self.channel = Channel()
        self.result = None
        # Python's garbage collector will try to double-free the task
        # once it's finished so disable the Qt auto-deletion.
        self.setAutoDelete(False)

    def run(self):
        self.result = self.task()
        self.channel.result.emit(self.result)
        self.channel.finished.emit(self)

    def task(self):
        """Perform a long-running task"""
        return ()

    def connect(self, handler):
        self.channel.result.connect(handler, type=Qt.QueuedConnection)


class SimpleTask(Task):
    """Run a simple callable as a task"""

    def __init__(self, func, *args, **kwargs):
        Task.__init__(self)

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def task(self):
        return self.func(*self.args, **self.kwargs)


class RunTask(QtCore.QObject):
    """Runs QRunnable instances and transfers control when they finish"""

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.tasks = []
        self.task_details = {}
        self.threadpool = QtCore.QThreadPool.globalInstance()
        self.result_func = None

    def start(self, task, progress=None, finish=None, result=None):
        """Start the task and register a callback"""
        self.result_func = result
        if progress is not None:
            if hasattr(progress, 'start'):
                progress.start()

        # prevents garbage collection bugs in certain PyQt4 versions
        self.tasks.append(task)
        task_id = id(task)
        self.task_details[task_id] = (progress, finish, result)
        task.channel.finished.connect(self.finish, type=Qt.QueuedConnection)
        self.threadpool.start(task)

    def finish(self, task):
        """The task has finished. Run the finish and result callbacks"""
        task_id = id(task)
        try:
            self.tasks.remove(task)
        except ValueError:
            pass
        try:
            progress, finish, result = self.task_details[task_id]
            del self.task_details[task_id]
        except KeyError:
            finish = progress = result = None

        if progress is not None:
            if hasattr(progress, 'stop'):
                progress.stop()
            progress.hide()

        if result is not None:
            result(task.result)

        if finish is not None:
            finish(task)

    def wait(self):
        """Wait until all tasks have finished processing"""
        self.threadpool.waitForDone()

    def run(self, fn, *args, **kwargs):
        """Run a task in the background"""
        task = SimpleTask(fn, *args, **kwargs)
        self.start(task)


# Syntax highlighting


def rgb(red, green, blue):
    """Create a QColor from r, g, b arguments"""
    color = QtGui.QColor()
    color.setRgb(red, green, blue)
    return color


def rgba(red, green, blue, alpha=255):
    """Create a QColor with alpha from r, g, b, a arguments"""
    color = rgb(red, green, blue)
    color.setAlpha(alpha)
    return color


def rgb_triple(args):
    """Create a QColor from an argument with an [r, g, b] triple"""
    return rgb(*args)


def rgb_css(color):
    """Convert a QColor into an rgb #abcdef CSS string"""
    return '#%s' % rgb_hex(color)


def rgb_hex(color):
    """Convert a QColor into a hex aabbcc string"""
    return f'{color.red():02x}{color.green():02x}{color.blue():02x}'


def clamp_color(value):
    """Clamp an integer value between 0 and 255"""
    return min(255, max(value, 0))


def css_color(value):
    """Convert a #abcdef hex string into a QColor"""
    if value.startswith('#'):
        value = value[1:]
    try:
        red = clamp_color(int(value[:2], base=16))  # ab
    except ValueError:
        red = 255
    try:
        green = clamp_color(int(value[2:4], base=16))  # cd
    except ValueError:
        green = 255
    try:
        blue = clamp_color(int(value[4:6], base=16))  # ef
    except ValueError:
        blue = 255
    return rgb(red, green, blue)


def hsl(hue, saturation, lightness):
    """Return a QColor from hue, saturation and lightness"""
    return QtGui.QColor.fromHslF(
        utils.clamp(hue, 0.0, 1.0),
        utils.clamp(saturation, 0.0, 1.0),
        utils.clamp(lightness, 0.0, 1.0),
    )


def hsl_css(hue, saturation, lightness):
    """Convert HSL values to a CSS #abcdef color string"""
    return rgb_css(hsl(hue, saturation, lightness))


def make_format(foreground=None, background=None, bold=False):
    """Create a QTextFormat from the provided foreground, background and bold values"""
    fmt = QtGui.QTextCharFormat()
    if foreground:
        fmt.setForeground(foreground)
    if background:
        fmt.setBackground(background)
    if bold:
        fmt.setFontWeight(QtGui.QFont.Bold)
    return fmt


class ImageFormats:
    def __init__(self):
        # returns a list of QByteArray objects
        formats_qba = QtGui.QImageReader.supportedImageFormats()
        # portability: python3 data() returns bytes, python2 returns str
        decode = core.decode
        formats = [decode(x.data()) for x in formats_qba]
        self.extensions = {'.' + fmt for fmt in formats}

    def ok(self, filename):
        _, ext = os.path.splitext(filename)
        return ext.lower() in self.extensions


def set_scrollbar_values(widget, hscroll_value, vscroll_value):
    """Set scrollbars to the specified values"""
    hscroll = widget.horizontalScrollBar()
    if hscroll and hscroll_value is not None:
        hscroll.setValue(hscroll_value)

    vscroll = widget.verticalScrollBar()
    if vscroll and vscroll_value is not None:
        vscroll.setValue(vscroll_value)


def get_scrollbar_values(widget):
    """Return the current (hscroll, vscroll) scrollbar values for a widget"""
    hscroll = widget.horizontalScrollBar()
    if hscroll:
        hscroll_value = get(hscroll)
    else:
        hscroll_value = None
    vscroll = widget.verticalScrollBar()
    if vscroll:
        vscroll_value = get(vscroll)
    else:
        vscroll_value = None
    return (hscroll_value, vscroll_value)


def scroll_to_item(widget, item):
    """Scroll to an item while retaining the horizontal scroll position"""
    hscroll = None
    hscrollbar = widget.horizontalScrollBar()
    if hscrollbar:
        hscroll = get(hscrollbar)
    widget.scrollToItem(item)
    if hscroll is not None:
        hscrollbar.setValue(hscroll)


def select_item(widget, item):
    """Scroll to and make a QTreeWidget item selected and current"""
    scroll_to_item(widget, item)
    widget.setCurrentItem(item)
    item.setSelected(True)


def get_selected_values(widget, top_level_idx, values):
    """Map the selected items under the top-level item to the values list"""
    # Get the top-level item
    item = widget.topLevelItem(top_level_idx)
    return tree_selection(item, values)


def get_selected_items(widget, idx):
    """Return the selected items under the top-level item"""
    item = widget.topLevelItem(idx)
    return tree_selection_items(item)


def add_menu_actions(menu, menu_actions):
    """Add actions to a menu, treating None as a separator"""
    current_actions = menu.actions()
    if current_actions:
        first_action = current_actions[0]
    else:
        first_action = None
        menu.addSeparator()

    for action in menu_actions:
        if action is None:
            action = menu_separator(menu)
        menu.insertAction(first_action, action)


def fontmetrics_width(metrics, text):
    """Get the width in pixels of specified text

    Calls QFontMetrics.horizontalAdvance() when available.
    QFontMetricswidth() is deprecated. Qt 5.11 added horizontalAdvance().
    """
    if hasattr(metrics, 'horizontalAdvance'):
        return metrics.horizontalAdvance(text)
    return metrics.width(text)


def text_width(font, text):
    """Get the width in pixels for the QFont and text"""
    metrics = QtGui.QFontMetrics(font)
    return fontmetrics_width(metrics, text)


def text_size(font, text):
    """Return the width in pixels for the specified text

    :param font_or_widget: The QFont or widget providing the font to use.
    :param text: The text to measure.
    """
    metrics = QtGui.QFontMetrics(font)
    return (fontmetrics_width(metrics, text), metrics.height())
