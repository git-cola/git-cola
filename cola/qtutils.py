# Copyright (c) 2008-2016 David Aguilar
"""Miscellaneous Qt utility functions."""
from __future__ import division, absolute_import, unicode_literals

from qtpy import compat
from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from . import core
from . import gitcfg
from . import hotkeys
from . import icons
from . import utils
from .i18n import N_
from .interaction import Interaction
from .compat import int_types
from .compat import ustr
from .models import prefs
from .widgets import defs


def connect_action(action, fn):
    """Connect an action to a function"""
    action.triggered[bool].connect(lambda x: fn())


def connect_action_bool(action, fn):
    """Connect a triggered(bool) action to a function"""
    action.triggered[bool].connect(fn)


def connect_button(button, fn):
    """Connect a button to a function"""
    button.pressed.connect(fn)


def button_action(button, action):
    """Make a button trigger an action"""
    connect_button(button, action.trigger)


def connect_toggle(toggle, fn):
    toggle.toggled.connect(fn)


def active_window():
    return QtWidgets.QApplication.activeWindow()


def hbox(margin, spacing, *items):
    return box(QtWidgets.QHBoxLayout, margin, spacing, *items)


def vbox(margin, spacing, *items):
    return box(QtWidgets.QVBoxLayout, margin, spacing, *items)


def buttongroup(*items):
    group = QtWidgets.QButtonGroup()
    for i in items:
        group.addButton(i)
    return group


STRETCH = object()
SKIPPED = object()


def set_margin(layout, margin):
    layout.setContentsMargins(margin, margin, margin, margin)


def box(cls, margin, spacing, *items):
    stretch = STRETCH
    skipped = SKIPPED
    layout = cls()
    layout.setSpacing(spacing)
    set_margin(layout, margin)

    for i in items:
        if isinstance(i, QtWidgets.QWidget):
            layout.addWidget(i)
        elif isinstance(i, (QtWidgets.QHBoxLayout, QtWidgets.QVBoxLayout,
                            QtWidgets.QFormLayout, QtWidgets.QLayout)):
            layout.addLayout(i)
        elif i is stretch:
            layout.addStretch()
        elif i is skipped:
            continue
        elif isinstance(i, int_types):
            layout.addSpacing(i)

    return layout


def form(margin, spacing, *widgets):
    layout = QtWidgets.QFormLayout()
    layout.setSpacing(spacing)
    layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
    set_margin(layout, margin)

    for idx, (label, widget) in enumerate(widgets):
        if isinstance(label, (str, ustr)):
            layout.addRow(label, widget)
        else:
            layout.setWidget(idx, QtWidgets.QFormLayout.LabelRole, label)
            layout.setWidget(idx, QtWidgets.QFormLayout.FieldRole, widget)

    return layout


def grid(margin, spacing, *widgets):
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
    layout = QtWidgets.QSplitter()
    layout.setOrientation(orientation)
    layout.setHandleWidth(defs.handle_width)
    layout.setChildrenCollapsible(True)
    for idx, widget in enumerate(widgets):
        layout.addWidget(widget)
        layout.setStretchFactor(idx, 1)

    return layout


def prompt(msg, title=None, text=''):
    """Presents the user with an input widget and returns the input."""
    if title is None:
        title = msg
    result = QtWidgets.QInputDialog.getText(
            active_window(), msg, title,
            QtWidgets.QLineEdit.Normal, text)
    return (result[0], result[1])


class TreeWidgetItem(QtWidgets.QTreeWidgetItem):

    TYPE = QtGui.QStandardItem.UserType + 101

    def __init__(self, path, icon, deleted):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.path = path
        self.deleted = deleted
        self.setIcon(0, icons.from_name(icon))
        self.setText(0, path)

    def type(self):
        return self.TYPE


def paths_from_indexes(model, indexes,
                       item_type=TreeWidgetItem.TYPE,
                       item_filter=None):
    """Return paths from a list of QStandardItemModel indexes"""
    items = [model.itemFromIndex(i) for i in indexes]
    return paths_from_items(items, item_type=item_type, item_filter=item_filter)


def _true_filter(x):
    return True


def paths_from_items(items,
                     item_type=TreeWidgetItem.TYPE,
                     item_filter=None):
    """Return a list of paths from a list of items"""
    if item_filter is None:
        item_filter = _true_filter
    return [i.path for i in items
            if i.type() == item_type and item_filter(i)]


def confirm(title, text, informative_text, ok_text,
            icon=None, default=True,
            cancel_text=None, cancel_icon=None):
    """Confirm that an action should take place"""
    msgbox = QtWidgets.QMessageBox(active_window())
    msgbox.setWindowModality(Qt.WindowModal)
    msgbox.setWindowTitle(title)
    msgbox.setText(text)
    msgbox.setInformativeText(informative_text)

    icon = icons.mkicon(icon, icons.ok)
    ok = msgbox.addButton(ok_text, QtWidgets.QMessageBox.ActionRole)
    ok.setIcon(icon)

    cancel = msgbox.addButton(QtWidgets.QMessageBox.Cancel)
    cancel_icon = icons.mkicon(cancel_icon, icons.close)
    cancel.setIcon(cancel_icon)
    if cancel_text:
        cancel.setText(cancel_text)

    if default:
        msgbox.setDefaultButton(ok)
    else:
        msgbox.setDefaultButton(cancel)
    msgbox.exec_()
    return msgbox.clickedButton() == ok


class ResizeableMessageBox(QtWidgets.QMessageBox):

    def __init__(self, parent):
        QtWidgets.QMessageBox.__init__(self, parent)
        self.setMouseTracking(True)
        self.setSizeGripEnabled(True)

    def event(self, event):
        res = QtWidgets.QMessageBox.event(self, event)
        event_type = event.type()
        if (event_type == QtCore.QEvent.MouseMove or
                event_type == QtCore.QEvent.MouseButtonPress):
            maxi = QtCore.QSize(defs.max_size, defs.max_size)
            self.setMaximumSize(maxi)
            text = self.findChild(QtWidgets.QTextEdit)
            if text is not None:
                expand = QtWidgets.QSizePolicy.Expanding
                text.setSizePolicy(QtWidgets.QSizePolicy(expand, expand))
                text.setMaximumSize(maxi)
        return res


def critical(title, message=None, details=None):
    """Show a warning with the provided title and message."""
    if message is None:
        message = title
    mbox = ResizeableMessageBox(active_window())
    mbox.setWindowTitle(title)
    mbox.setTextFormat(Qt.PlainText)
    mbox.setText(message)
    mbox.setIcon(QtWidgets.QMessageBox.Critical)
    mbox.setStandardButtons(QtWidgets.QMessageBox.Close)
    mbox.setDefaultButton(QtWidgets.QMessageBox.Close)
    if details:
        mbox.setDetailedText(details)
    mbox.exec_()


def information(title, message=None, details=None, informative_text=None):
    """Show information with the provided title and message."""
    if message is None:
        message = title
    mbox = QtWidgets.QMessageBox(active_window())
    mbox.setStandardButtons(QtWidgets.QMessageBox.Close)
    mbox.setDefaultButton(QtWidgets.QMessageBox.Close)
    mbox.setWindowTitle(title)
    mbox.setWindowModality(Qt.WindowModal)
    mbox.setTextFormat(Qt.PlainText)
    mbox.setText(message)
    if informative_text:
        mbox.setInformativeText(informative_text)
    if details:
        mbox.setDetailedText(details)
    # Render into a 1-inch wide pixmap
    pixmap = icons.cola().pixmap(defs.large_icon)
    mbox.setIconPixmap(pixmap)
    mbox.exec_()


def question(title, msg, default=True):
    """Launches a QMessageBox question with the provided title and message.
    Passing "default=False" will make "No" the default choice."""
    yes = QtWidgets.QMessageBox.Yes
    no = QtWidgets.QMessageBox.No
    buttons = yes | no
    if default:
        default = yes
    else:
        default = no

    parent = active_window()
    MessageBox = QtWidgets.QMessageBox
    result = MessageBox.question(parent, title, msg, buttons, default)
    return result == QtWidgets.QMessageBox.Yes


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
        return items[row]
    else:
        return None


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
    result = compat.getopenfilename(parent=active_window(),
                                    caption=title,
                                    basedir=directory)
    return result[0]


def open_files(title, directory=None, filters=''):
    """Creates an Open File dialog and returns a list of filenames."""
    result = compat.getopenfilenames(parent=active_window(),
                                     caption=title,
                                     basedir=directory,
                                     filters=filters)
    return result[0]


def opendir_dialog(caption, path):
    """Prompts for a directory path"""

    options = (QtWidgets.QFileDialog.ShowDirsOnly |
               QtWidgets.QFileDialog.DontResolveSymlinks)
    return compat.getexistingdirectory(parent=active_window(),
                                       caption=caption,
                                       basedir=path,
                                       options=options)


def save_as(filename, title='Save As...'):
    """Creates a Save File dialog and returns a filename."""
    result = compat.getsavefilename(parent=active_window(),
                                    caption=title,
                                    basedir=filename)
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
    clipboard.setText(text, QtGui.QClipboard.Selection)
    persist_clipboard()


def persist_clipboard():
    """Persist the clipboard

    X11 stores only a reference to the clipboard data.
    Send a clipboard event to force a copy of the clipboard to occur.
    This ensures that the clipboard is present after git-cola exits.
    Otherwise, the reference is destroyed on exit.

    C.f. https://stackoverflow.com/questions/2007103/how-can-i-disable-clear-of-clipboard-on-exit-of-pyqt4-application

    """
    clipboard = QtWidgets.QApplication.clipboard()
    event = QtCore.QEvent(QtCore.QEvent.Clipboard)
    QtWidgets.QApplication.sendEvent(clipboard, event)


def add_action_bool(widget, text, fn, checked, *shortcuts):
    tip = text
    action = _add_action(widget, text, tip, fn, connect_action_bool, *shortcuts)
    action.setCheckable(True)
    action.setChecked(checked)
    return action


def add_action(widget, text, fn, *shortcuts):
    tip = text
    return _add_action(widget, text, tip, fn, connect_action, *shortcuts)


def add_action_with_status_tip(widget, text, tip, fn, *shortcuts):
    return _add_action(widget, text, tip, fn, connect_action, *shortcuts)


def _add_action(widget, text, tip, fn, connect, *shortcuts):
    action = QtWidgets.QAction(text, widget)
    if hasattr(action, 'setIconVisibleInMenu'):
        action.setIconVisibleInMenu(True)
    if tip:
        action.setStatusTip(tip)
    connect(action, fn)
    if shortcuts:
        action.setShortcuts(shortcuts)
        if hasattr(Qt, 'WidgetWithChildrenShortcut'):
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        widget.addAction(action)
    return action


def set_selected_item(widget, idx):
    """Sets a the currently selected item to the item at index idx."""
    if type(widget) is QtWidgets.QTreeWidget:
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
    return TreeWidgetItem(filename, icons.name_from_basename(icon_name),
                          deleted=deleted)


def add_close_action(widget):
    """Adds close action and shortcuts to a widget."""
    return add_action(widget, N_('Close...'),
                      widget.close, hotkeys.CLOSE, hotkeys.QUIT)


def center_on_screen(widget):
    """Move widget to the center of the default screen"""
    desktop = QtWidgets.QApplication.instance().desktop()
    rect = desktop.screenGeometry(QtGui.QCursor().pos())
    cy = rect.height()//2
    cx = rect.width()//2
    widget.move(cx - widget.width()//2, cy - widget.height()//2)


def default_size(parent, width, height):
    """Return the parent's size, or the provided defaults"""
    if parent is not None:
        width = parent.width()
        height = parent.height()
    return (width, height)


def default_monospace_font():
    font = QtGui.QFont()
    family = 'Monospace'
    if utils.is_darwin():
        family = 'Monaco'
    font.setFamily(family)
    return font


def diff_font_str():
    font_str = gitcfg.current().get(prefs.FONTDIFF)
    if font_str is None:
        font_str = default_monospace_font().toString()
    return font_str


def diff_font():
    return font(diff_font_str())


def font(string):
    font = QtGui.QFont()
    font.fromString(string)
    return font


def create_button(text='', layout=None, tooltip=None, icon=None,
                  enabled=True, default=False):
    """Create a button, set its title, and add it to the parent."""
    button = QtWidgets.QPushButton()
    button.setCursor(Qt.PointingHandCursor)
    if text:
        button.setText(text)
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


def create_action_button(tooltip=None, icon=None):
    button = QtWidgets.QPushButton()
    button.setCursor(Qt.PointingHandCursor)
    button.setFlat(True)
    if tooltip is not None:
        button.setToolTip(tooltip)
    if icon is not None:
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(defs.small_icon, defs.small_icon))
    return button


def ok_button(text, default=False, enabled=True):
    return create_button(text=text, icon=icons.ok(),
                         default=default, enabled=enabled)


def close_button():
    return create_button(text=N_('Close'), icon=icons.close())


def edit_button(enabled=True, default=False):
    return create_button(text=N_('Edit'), icon=icons.edit(),
                         enabled=enabled, default=default)


def refresh_button(enabled=True, default=False):
    return create_button(text=N_('Refresh'), icon=icons.sync(),
                         enabled=enabled, default=default)


def hide_button_menu_indicator(button):
    cls = type(button)
    name = cls.__name__
    stylesheet = """
        %(name)s::menu-indicator {
            image: none;
        }
    """
    if name == 'QPushButton':
        stylesheet += """
            %(name)s {
                border-style: none;
            }
        """
    button.setStyleSheet(stylesheet % {'name': name})


def checkbox(text='', tooltip='', checked=None):
    cb = QtWidgets.QCheckBox()
    if text:
        cb.setText(text)
    if tooltip:
        cb.setToolTip(tooltip)
    if checked is not None:
        cb.setChecked(checked)

    url = icons.check_name()
    style = """
        QCheckBox::indicator {
            width: %(size)dpx;
            height: %(size)dpx;
        }
        QCheckBox::indicator::unchecked {
            border: %(border)dpx solid #999;
            background: #fff;
        }
        QCheckBox::indicator::checked {
            image: url(%(url)s);
            border: %(border)dpx solid black;
            background: #fff;
        }
    """ % dict(size=defs.checkbox, border=defs.border, url=url)
    cb.setStyleSheet(style)

    return cb


def radio(text='', tooltip='', checked=None):
    rb = QtWidgets.QRadioButton()
    if text:
        rb.setText(text)
    if tooltip:
        rb.setToolTip(tooltip)
    if checked is not None:
        rb.setChecked(checked)

    size = defs.checkbox
    radius = size / 2
    border = defs.radio_border
    url = icons.dot_name()
    style = """
        QRadioButton::indicator {
            width: %(size)dpx;
            height: %(size)dpx;
        }
        QRadioButton::indicator::unchecked {
            background: #fff;
            border: %(border)dpx solid #999;
            border-radius: %(radius)dpx;
        }
        QRadioButton::indicator::checked {
            image: url(%(url)s);
            background: #fff;
            border: %(border)dpx solid black;
            border-radius: %(radius)dpx;
        }
    """ % dict(size=size, radius=radius, border=border, url=url)
    rb.setStyleSheet(style)

    return rb


class DockTitleBarWidget(QtWidgets.QWidget):

    def __init__(self, parent, title, stretch=True):
        QtWidgets.QWidget.__init__(self, parent)
        self.label = label = QtWidgets.QLabel()
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        label.setText(title)
        label.setCursor(Qt.OpenHandCursor)

        self.close_button = create_action_button(
            tooltip=N_('Close'), icon=icons.close())

        self.toggle_button = create_action_button(
            tooltip=N_('Detach'), icon=icons.external())

        self.corner_layout = hbox(defs.no_margin, defs.spacing)

        if stretch:
            separator = STRETCH
        else:
            separator = SKIPPED

        self.main_layout = hbox(defs.small_margin, defs.spacing,
                                label, separator, self.corner_layout,
                                self.toggle_button, self.close_button)
        self.setLayout(self.main_layout)

        connect_button(self.toggle_button, self.toggle_floating)
        connect_button(self.close_button, self.toggle_visibility)

    def toggle_floating(self):
        self.parent().setFloating(not self.parent().isFloating())
        self.update_tooltips()

    def toggle_visibility(self):
        self.parent().toggleViewAction().trigger()

    def set_title(self, title):
        self.label.setText(title)

    def add_corner_widget(self, widget):
        self.corner_layout.addWidget(widget)

    def update_tooltips(self):
        if self.parent().isFloating():
            tooltip = N_('Attach')
        else:
            tooltip = N_('Detach')
        self.toggle_button.setToolTip(tooltip)


def create_dock(title, parent, stretch=True):
    """Create a dock widget and set it up accordingly."""
    dock = QtWidgets.QDockWidget(parent)
    dock.setWindowTitle(title)
    dock.setObjectName(title)
    titlebar = DockTitleBarWidget(dock, title, stretch=stretch)
    dock.setTitleBarWidget(titlebar)
    if hasattr(parent, 'dockwidgets'):
        parent.dockwidgets.append(dock)
    return dock


def create_menu(title, parent):
    """Create a menu and set its title."""
    qmenu = QtWidgets.QMenu(title, parent)
    return qmenu


def create_toolbutton(text=None, layout=None, tooltip=None, icon=None):
    button = QtWidgets.QToolButton()
    button.setAutoRaise(True)
    button.setAutoFillBackground(True)
    button.setCursor(Qt.PointingHandCursor)
    if icon is not None:
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(defs.small_icon, defs.small_icon))
    if text is not None:
        button.setText(text)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    if tooltip is not None:
        button.setToolTip(tooltip)
    if layout is not None:
        layout.addWidget(button)
    return button


def mimedata_from_paths(paths):
    """Return mimedata with a list of absolute path URLs"""

    abspaths = [core.abspath(path) for path in paths]
    urls = [QtCore.QUrl.fromLocalFile(path) for path in abspaths]

    mimedata = QtCore.QMimeData()
    mimedata.setUrls(urls)

    # The text/x-moz-list format is always included by Qt, and doing
    # mimedata.removeFormat('text/x-moz-url') has no effect.
    # C.f. http://www.qtcentre.org/threads/44643-Dragging-text-uri-list-Qt-inserts-garbage
    #
    # gnome-terminal expects utf-16 encoded text, but other terminals,
    # e.g. terminator, prefer utf-8, so allow cola.dragencoding
    # to override the default.
    paths_text = core.list2cmdline(abspaths)
    encoding = gitcfg.current().get('cola.dragencoding', 'utf-16')
    moz_text = core.encode(paths_text, encoding=encoding)
    mimedata.setData('text/x-moz-url', moz_text)

    return mimedata


def path_mimetypes():
    return ['text/uri-list', 'text/x-moz-url']


class BlockSignals(object):
    """Context manager for blocking a signals on a widget"""

    def __init__(self, *widgets):
        self.widgets = widgets
        self.values = {}

    def __enter__(self):
        for w in self.widgets:
            self.values[w] = w.blockSignals(True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for w in self.widgets:
            w.blockSignals(self.values[w])


class Channel(QtCore.QObject):
    finished = Signal(object)
    result = Signal(object)


class Task(QtCore.QRunnable):
    """Disable auto-deletion to avoid gc issues

    Python's garbage collector will try to double-free the task
    once it's finished, so disable Qt's auto-deletion as a workaround.

    """

    def __init__(self, parent):
        QtCore.QRunnable.__init__(self)

        self.channel = Channel()
        self.result = None
        self.setAutoDelete(False)

    def run(self):
        self.result = self.task()
        self.channel.result.emit(self.result)
        self.done()

    def task(self):
        return None

    def done(self):
        self.channel.finished.emit(self)

    def connect(self, handler):
        self.channel.result.connect(handler, type=Qt.QueuedConnection)


class SimpleTask(Task):
    """Run a simple callable as a task"""

    def __init__(self, parent, fn, *args, **kwargs):
        Task.__init__(self, parent)

        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def task(self):
        return self.fn(*self.args, **self.kwargs)


class RunTask(QtCore.QObject):
    """Runs QRunnable instances and transfers control when they finish"""

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.tasks = []
        self.task_details = {}
        self.threadpool = QtCore.QThreadPool.globalInstance()

    def start(self, task, progress=None, finish=None):
        """Start the task and register a callback"""
        if progress is not None:
            progress.show()
        # prevents garbage collection bugs in certain PyQt4 versions
        self.tasks.append(task)
        task_id = id(task)
        self.task_details[task_id] = (progress, finish)

        task.channel.finished.connect(self.finish, type=Qt.QueuedConnection)
        self.threadpool.start(task)

    def finish(self, task):
        task_id = id(task)
        try:
            self.tasks.remove(task)
        except:
            pass
        try:
            progress, finish = self.task_details[task_id]
            del self.task_details[task_id]
        except KeyError:
            finish = progress = None

        if progress is not None:
            progress.hide()

        if finish is not None:
            finish(task)


# Syntax highlighting

def rgba(r, g, b, a=255):
    c = QtGui.QColor()
    c.setRgb(r, g, b)
    c.setAlpha(a)
    return c


def RGB(args):
    return rgba(*args)


def make_format(fg=None, bg=None, bold=False):
    fmt = QtGui.QTextCharFormat()
    if fg:
        fmt.setForeground(fg)
    if bg:
        fmt.setBackground(bg)
    if bold:
        fmt.setFontWeight(QtGui.QFont.Bold)
    return fmt


def install():
    Interaction.critical = staticmethod(critical)
    Interaction.confirm = staticmethod(confirm)
    Interaction.question = staticmethod(question)
    Interaction.information = staticmethod(information)
