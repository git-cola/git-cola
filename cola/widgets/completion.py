from __future__ import division, absolute_import, unicode_literals
import re

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import core
from .. import gitcmds
from .. import icons
from .. import qtutils
from .. import utils
from ..models import main
from . import defs
from . import text


class CompletionLineEdit(text.HintedLineEdit):
    """An lineedit with advanced completion abilities"""

    activated = Signal()
    changed = Signal()
    cleared = Signal()
    enter = Signal()
    up = Signal()
    down = Signal()

    # Activation keys will cause a selected completion item to be chosen
    ACTIVATION_KEYS = (Qt.Key_Return, Qt.Key_Enter)

    # Navigation keys trigger signals that widgets can use for customization
    NAVIGATION_KEYS = {
            Qt.Key_Return: 'enter',
            Qt.Key_Enter: 'enter',
            Qt.Key_Up: 'up',
            Qt.Key_Down: 'down',
    }

    def __init__(self, model_factory, hint='', parent=None):
        text.HintedLineEdit.__init__(self, hint, parent=parent)
        # Tracks when the completion popup was active during key events
        self._was_visible = False
        # The most recently selected completion item
        self._selection = None

        # Create a completion model
        completion_model = model_factory(self)
        completer = Completer(completion_model, self)
        completer.setWidget(self)
        self._completer = completer
        self._completion_model = completion_model

        # The delegate highlights matching completion text in the popup widget
        self._delegate = HighlightDelegate(self)
        completer.popup().setItemDelegate(self._delegate)

        self.textChanged.connect(self._text_changed)
        self._completer.activated.connect(self.choose_completion)
        self._completion_model.updated.connect(self._completions_updated,
                                               type=Qt.QueuedConnection)
        self.destroyed.connect(self.dispose)

    def __del__(self):
        self.dispose()

    def dispose(self, *args):
        self._completer.dispose()

    def was_visible(self):
        """Was the popup visible during the last keypress event?"""
        return self._was_visible

    def completion_selection(self):
        """Return the last completion's selection"""
        return self._selection

    def complete(self):
        """Trigger the completion popup to appear and offer completions"""
        self._completer.complete()

    def refresh(self):
        """Refresh the completion model"""
        return self._completer.model().update()

    def popup(self):
        """Return the completer's popup"""
        return self._completer.popup()

    def _is_case_sensitive(self, text):
        return bool([char for char in text if char.isupper()])

    def _text_changed(self, full_text):
        match_text = self._last_word()
        self._do_text_changed(full_text, match_text)
        self.complete_last_word()

    def _do_text_changed(self, full_text, match_text):
        case_sensitive = self._is_case_sensitive(match_text)
        if case_sensitive:
            self._completer.setCaseSensitivity(Qt.CaseSensitive)
        else:
            self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._delegate.set_highlight_text(match_text, case_sensitive)
        self._completer.set_match_text(full_text, match_text, case_sensitive)

    def update_matches(self):
        text = self._last_word()
        case_sensitive = self._is_case_sensitive(text)
        self._completer.setCompletionPrefix(text)
        self._completer.model().update_matches(case_sensitive)

    def choose_completion(self, completion):
        """
        This is the event handler for the QCompleter.activated(QString) signal,
        it is called when the user selects an item in the completer popup.
        """
        if not completion:
            self._do_text_changed('', '')
            return
        words = self._words()
        if words and not self._ends_with_whitespace():
            words.pop()

        words.append(completion)
        text = core.list2cmdline(words)
        self.setText(text)
        self.changed.emit()
        self._do_text_changed(text, '')
        self.popup().hide()

    def _words(self):
        return utils.shell_split(self.value())

    def _ends_with_whitespace(self):
        return self.value() != self.value().rstrip()

    def _last_word(self):
        if self._ends_with_whitespace():
            return ''
        words = self._words()
        if not words:
            return self.value()
        if not words[-1]:
            return ''
        return words[-1]

    def event(self, event):
        if event.type() == QtCore.QEvent.Hide:
            self.close_popup()
        return text.HintedLineEdit.event(self, event)

    def complete_last_word(self):
        self.update_matches()
        self.complete()

    def close_popup(self):
        if self.popup().isVisible():
            self.popup().close()

    def _update_popup_items(self, prefix):
        """
        Filters the completer's popup items to only show items
        with the given prefix.
        """
        self._completer.setCompletionPrefix(prefix)

    def _completions_updated(self):
        popup = self.popup()
        if not popup.isVisible():
            return
        # Select the first item
        idx = self._completion_model.index(0, 0)
        selection = QtCore.QItemSelection(idx, idx)
        mode = QtCore.QItemSelectionModel.Select
        popup.selectionModel().select(selection, mode)

    def selected_completion(self):
        popup = self.popup()
        if not popup.isVisible():
            return None
        model = popup.selectionModel()
        indexes = model.selectedIndexes()
        if not indexes:
            return None
        idx = indexes[0]
        item = self._completion_model.itemFromIndex(idx)
        if not item:
            return
        return item.text()

    # Qt events
    def keyPressEvent(self, event):
        self._was_visible = visible = self.popup().isVisible()
        key = event.key()
        was_empty = not bool(self.value())

        if visible:
            self._selection = self.selected_completion()
        else:
            self._selection = None
            if event.key() in self.ACTIVATION_KEYS:
                event.accept()
                return

        result = text.HintedLineEdit.keyPressEvent(self, event)

        # Backspace at the beginning of the line should hide the popup
        if was_empty and visible and key == Qt.Key_Backspace:
            self.popup().hide()
        # Clearing a line should always emit a signal
        is_empty = not bool(self.value())
        if is_empty:
            self.cleared.emit()
        return result

    def keyReleaseEvent(self, event):
        """React to release events, handle completion"""
        key = event.key()
        visible = self.was_visible()
        if not visible:
            # If it's a navigation key then emit a signal
            try:
                event.accept()
                msg = self.NAVIGATION_KEYS[key]
                signal = getattr(self, msg)
                signal.emit()
                return
            except KeyError:
                pass
        # Run the real release event
        result = text.HintedLineEdit.keyReleaseEvent(self, event)
        # If the popup was visible and we have a selected popup item
        # then choose that completion.
        selection = self.completion_selection()
        if visible and selection and key in self.ACTIVATION_KEYS:
            self.choose_completion(selection)
            self.activated.emit()
            return
        return result


class GatherCompletionsThread(QtCore.QThread):

    items_gathered = Signal(object)

    def __init__(self, model):
        QtCore.QThread.__init__(self)
        self.model = model
        self.case_sensitive = False

    def run(self):
        text = None
        # Loop when the matched text changes between the start and end time.
        # This happens when gather_matches() takes too long and the
        # model's match_text changes in-between.
        while text != self.model.match_text:
            text = self.model.match_text
            items = self.model.gather_matches(self.case_sensitive)

        if text is not None:
            self.items_gathered.emit(items)


class HighlightDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate used for auto-completion to give formatted completion"""

    def __init__(self, parent):
        QtWidgets.QStyledItemDelegate.__init__(self, parent)
        self.widget = parent
        self.highlight_text = ''
        self.case_sensitive = False

        self.doc = QtGui.QTextDocument()
        try:
            self.doc.setDocumentMargin(0)
        except:  # older PyQt4
            pass

    def set_highlight_text(self, text, case_sensitive):
        """Sets the text that will be made bold when displayed"""
        self.highlight_text = text
        self.case_sensitive = case_sensitive

    def paint(self, painter, option, index):
        """Overloaded Qt method for custom painting of a model index"""
        if not self.highlight_text:
            return QtWidgets.QStyledItemDelegate.paint(self, painter,
                                                       option, index)
        text = index.data()
        if self.case_sensitive:
            html = text.replace(self.highlight_text,
                                '<strong>%s</strong>' % self.highlight_text)
        else:
            match = re.match(r'(.*)(%s)(.*)' % re.escape(self.highlight_text),
                             text, re.IGNORECASE)
            if match:
                start = match.group(1) or ''
                middle = match.group(2) or ''
                end = match.group(3) or ''
                html = (start + ('<strong>%s</strong>' % middle) + end)
            else:
                html = text
        self.doc.setHtml(html)

        # Painting item without text, Text Document will paint the text
        params = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(params, index)
        params.text = ''

        style = QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, params, painter)
        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        # Highlighting text if item is selected
        if (params.state & QtWidgets.QStyle.State_Selected):
            color = params.palette.color(QtGui.QPalette.Active,
                                         QtGui.QPalette.HighlightedText)
            ctx.palette.setColor(QtGui.QPalette.Text, color)

        # translate the painter to where the text is drawn
        item_text = QtWidgets.QStyle.SE_ItemViewItemText
        rect = style.subElementRect(item_text, params, self.widget)
        painter.save()

        start = rect.topLeft() + QtCore.QPoint(defs.margin, 0)
        painter.translate(start)

        # tell the text document to draw the html for us
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()


def ref_sort_key(ref):
    """Sort key function that causes shorter refs to sort first, but
    alphabetizes refs of equal length (in order to make local branches sort
    before remote ones)."""
    return len(ref), ref


class CompletionModel(QtGui.QStandardItemModel):

    updated = Signal()
    items_gathered = Signal(object)
    model_updated = Signal()

    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.match_text = ''
        self.full_text = ''
        self.case_sensitive = False

        self.update_thread = GatherCompletionsThread(self)
        self.update_thread.items_gathered.connect(self.apply_matches,
                                                  type=Qt.QueuedConnection)

    def update(self):
        case_sensitive = self.update_thread.case_sensitive
        self.update_matches(case_sensitive)

    def set_match_text(self, full_text, match_text, case_sensitive):
        self.full_text = full_text
        self.match_text = match_text
        self.update_matches(case_sensitive)

    def update_matches(self, case_sensitive):
        self.case_sensitive = case_sensitive
        self.update_thread.case_sensitive = case_sensitive
        if not self.update_thread.isRunning():
            self.update_thread.start()

    def gather_matches(self, case_sensitive):
        return ((), (), set())

    def apply_matches(self, match_tuple):
        matched_refs, matched_paths, dirs = match_tuple
        QStandardItem = QtGui.QStandardItem

        dir_icon = icons.directory()
        git_icon = icons.cola()

        items = []
        for ref in matched_refs:
            item = QStandardItem()
            item.setText(ref)
            item.setIcon(git_icon)
            items.append(item)

        from_filename = icons.from_filename
        for match in matched_paths:
            item = QStandardItem()
            item.setText(match)
            if match in dirs:
                item.setIcon(dir_icon)
            else:
                item.setIcon(from_filename(match))
            items.append(item)

        self.clear()
        self.invisibleRootItem().appendRows(items)
        self.updated.emit()


def _identity(x):
    return x


def _lower(x):
    return x.lower()


def filter_matches(match_text, candidates, case_sensitive,
                   sort_key=lambda x: x):
    """Filter candidates and return the matches"""

    if case_sensitive:
        case_transform = _identity
    else:
        case_transform = _lower

    if match_text:
        match_text = case_transform(match_text)
        matches = [r for r in candidates if match_text in case_transform(r)]
    else:
        matches = list(candidates)

    matches.sort(key=lambda x: sort_key(case_transform(x)))
    return matches


def filter_path_matches(match_text, file_list, case_sensitive):
    """Return matching completions from a list of candidate files"""

    files = set(file_list)
    files_and_dirs = utils.add_parents(files)
    dirs = files_and_dirs.difference(files)

    paths = filter_matches(match_text, files_and_dirs, case_sensitive)
    return (paths, dirs)


class Completer(QtWidgets.QCompleter):

    def __init__(self, model, parent):
        QtWidgets.QCompleter.__init__(self, parent)
        self._model = model
        self.setCompletionMode(QtWidgets.QCompleter.UnfilteredPopupCompletion)
        self.setCaseSensitivity(Qt.CaseInsensitive)

        model.model_updated.connect(self.update, type=Qt.QueuedConnection)
        self.setModel(model)

    def update(self):
        self._model.update()

    def dispose(self):
        self._model.dispose()

    def set_match_text(self, full_text, match_text, case_sensitive):
        self._model.set_match_text(full_text, match_text, case_sensitive)


class GitCompletionModel(CompletionModel):

    def __init__(self, parent):
        CompletionModel.__init__(self, parent)
        self.main_model = model = main.model()
        msg = model.message_updated
        model.add_observer(msg, self.emit_model_updated)

    def gather_matches(self, case_sensitive):
        refs = filter_matches(self.match_text, self.matches(), case_sensitive,
                              sort_key=ref_sort_key)
        return (refs, (), set())

    def emit_model_updated(self):
        try:
            self.model_updated.emit()
        except RuntimeError:  # C++ object has been deleted
            self.dispose()

    def matches(self):
        return []

    def dispose(self):
        self.main_model.remove_observer(self.emit_model_updated)


class GitRefCompletionModel(GitCompletionModel):
    """Completer for branches and tags"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        return model.local_branches + model.remote_branches + model.tags


class GitPotentialBranchCompletionModel(GitCompletionModel):
    """Completer for branches, tags, and potential branches"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        remotes = model.remotes
        remote_branches = model.remote_branches

        ambiguous = set()
        allnames = set(model.local_branches)
        potential = []

        for remote_branch in remote_branches:
            branch = gitcmds.strip_remote(remotes, remote_branch)
            if branch in allnames or branch == remote_branch:
                ambiguous.add(branch)
                continue
            potential.append(branch)
            allnames.add(branch)

        potential_branches = [p for p in potential if p not in ambiguous]

        return (model.local_branches +
                potential_branches +
                model.remote_branches +
                model.tags)


class GitBranchCompletionModel(GitCompletionModel):
    """Completer for remote branches"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        return model.local_branches


class GitRemoteBranchCompletionModel(GitCompletionModel):
    """Completer for remote branches"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        return model.remote_branches


class GitPathCompletionModel(GitCompletionModel):
    """Base class for path completion"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def candidate_paths(self):
        return []

    def gather_matches(self, case_sensitive):
        paths, dirs = filter_path_matches(self.match_text,
                                          self.candidate_paths(),
                                          case_sensitive)
        return ((), paths, dirs)


class GitStatusFilterCompletionModel(GitPathCompletionModel):
    """Completer for modified files and folders for status filtering"""

    def __init__(self, parent):
        GitPathCompletionModel.__init__(self, parent)

    def candidate_paths(self):
        model = self.main_model
        return (model.staged + model.unmerged +
                model.modified + model.untracked)


class GitTrackedCompletionModel(GitPathCompletionModel):
    """Completer for tracked files and folders"""

    def __init__(self, parent):
        GitPathCompletionModel.__init__(self, parent)
        self.model_updated.connect(self.gather_paths, type=Qt.QueuedConnection)
        self._paths = []

    def gather_paths(self):
        self._paths = gitcmds.tracked_files()

    def gather_matches(self, case_sensitive):
        if not self._paths:
            self.gather_paths()

        refs = []
        paths, dirs = filter_path_matches(self.match_text, self._paths,
                                          case_sensitive)
        return (refs, paths, dirs)


class GitLogCompletionModel(GitRefCompletionModel):
    """Completer for arguments suitable for git-log like commands"""

    def __init__(self, parent):
        GitRefCompletionModel.__init__(self, parent)
        self.model_updated.connect(self.gather_paths, type=Qt.QueuedConnection)
        self.use_paths = False
        self._paths = []

    def gather_paths(self):
        self._paths = gitcmds.tracked_files()

    def gather_matches(self, case_sensitive):
        if not self._paths:
            self.gather_paths()
        refs = filter_matches(self.match_text, self.matches(), case_sensitive,
                              sort_key=ref_sort_key)
        paths = []
        dirs = []
        if self.use_paths:
            paths, dirs = filter_path_matches(self.match_text, self._paths,
                                              case_sensitive)
        has_doubledash = (self.match_text == '--' or
                          self.full_text.startswith('-- ') or
                          ' -- ' in self.full_text)
        if has_doubledash:
            refs = []
        elif refs and paths:
            paths.insert(0, '--')

        return (refs, paths, dirs)


def bind_lineedit(model, hint=''):
    """Create a line edit bound against a specific model"""

    class BoundLineEdit(CompletionLineEdit):

        def __init__(self, hint=hint, parent=None):
            CompletionLineEdit.__init__(self, model,
                                        hint=hint, parent=parent)

    return BoundLineEdit


# Concrete classes
GitLogLineEdit = bind_lineedit(GitLogCompletionModel, hint='<ref>')
GitRefLineEdit = bind_lineedit(GitRefCompletionModel, hint='<ref>')
GitPotentialBranchLineEdit = bind_lineedit(GitPotentialBranchCompletionModel,
                                           hint='<branch>')
GitBranchLineEdit = bind_lineedit(GitBranchCompletionModel, hint='<branch>')
GitRemoteBranchLineEdit = bind_lineedit(GitRemoteBranchCompletionModel,
                                        hint='<remote-branch>')
GitStatusFilterLineEdit = bind_lineedit(GitStatusFilterCompletionModel,
                                        hint='<path>')
GitTrackedLineEdit = bind_lineedit(GitTrackedCompletionModel, hint='<path>')


class GitDialog(QtWidgets.QDialog):

    def __init__(self, lineedit, title, text, parent, icon=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumWidth(333)

        self.label = QtWidgets.QLabel()
        self.label.setText(title)

        self.lineedit = lineedit()
        self.setFocusProxy(self.lineedit)

        self.ok_button = qtutils.ok_button(text, icon=icon, enabled=False)
        self.close_button = qtutils.close_button()

        self.button_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                          qtutils.STRETCH,
                                          self.ok_button, self.close_button)

        self.main_layout = qtutils.vbox(defs.margin, defs.spacing,
                                        self.label, self.lineedit,
                                        self.button_layout)
        self.setLayout(self.main_layout)

        self.lineedit.textChanged.connect(self.text_changed)
        self.lineedit.enter.connect(self.accept)
        qtutils.connect_button(self.ok_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

    def text(self):
        return self.lineedit.text()

    def text_changed(self, txt):
        self.ok_button.setEnabled(bool(self.text()))

    def set_text(self, ref):
        self.lineedit.setText(ref)

    @classmethod
    def get(cls, title, text, parent, default=None, icon=None):
        dlg = cls(title, text, parent, icon=icon)
        if default:
            dlg.set_text(default)

        dlg.show()
        dlg.raise_()

        def show_popup():
            x = dlg.lineedit.x()
            y = dlg.lineedit.y() + dlg.lineedit.height()
            point = QtCore.QPoint(x, y)
            mapped = dlg.mapToGlobal(point)
            dlg.lineedit.popup().move(mapped.x(), mapped.y())
            dlg.lineedit.popup().show()
            dlg.lineedit.refresh()

        QtCore.QTimer().singleShot(0, show_popup)

        if dlg.exec_() == cls.Accepted:
            return dlg.text()
        else:
            return None


class GitRefDialog(GitDialog):

    def __init__(self, title, text, parent, icon=None):
        GitDialog.__init__(self, GitRefLineEdit,
                           title, text, parent, icon=icon)


class GitPotentialBranchDialog(GitDialog):

    def __init__(self, title, text, parent, icon=None):
        GitDialog.__init__(self, GitPotentialBranchLineEdit,
                           title, text, parent, icon=icon)


class GitBranchDialog(GitDialog):

    def __init__(self, title, text, parent, icon=None):
        GitDialog.__init__(self, GitBranchLineEdit,
                           title, text, parent, icon=icon)


class GitRemoteBranchDialog(GitDialog):

    def __init__(self, title, text, parent, icon=None):
        GitDialog.__init__(self, GitRemoteBranchLineEdit,
                           title, text, parent, icon=icon)
