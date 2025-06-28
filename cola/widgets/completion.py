import re
import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..models import prefs
from .. import core
from .. import gitcmds
from .. import icons
from .. import qtutils
from .. import utils
from . import defs
from .text import HintedLineEdit


class ValidateRegex:
    def __init__(self, regex):
        self.regex = re.compile(regex)  # regex to scrub

    def validate(self, string, idx):
        """Scrub and validate the user-supplied input"""
        state = QtGui.QValidator.Acceptable
        if self.regex.search(string):
            string = self.regex.sub('', string)  # scrub matching bits
            idx = min(idx - 1, len(string))
        return (state, string, idx)


class RemoteValidator(QtGui.QValidator):
    """Prevent invalid remote names"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._validate = ValidateRegex(r'[ \t\\/]')

    def validate(self, string, idx):
        return self._validate.validate(string, idx)


class BranchValidator(QtGui.QValidator):
    """Prevent invalid branch names"""

    def __init__(self, git, parent=None):
        super().__init__(parent)
        self._git = git
        self._validate = ValidateRegex(r'[ \t\\]')  # forward-slash is okay

    def validate(self, string, idx):
        """Scrub and validate the user-supplied input"""
        state, string, idx = self._validate.validate(string, idx)
        if string:  # Allow empty strings
            status, _, _ = self._git.check_ref_format(string, branch=True)
            if status != 0:
                # The intermediate string, when deleting characters, might
                # end in a name that is invalid to Git, but we must allow it
                # otherwise we won't be able to delete it using backspace.
                if string.endswith('/') or string.endswith('.'):
                    state = self.Intermediate
                else:
                    state = self.Invalid
        return (state, string, idx)


def _is_case_sensitive(text):
    return bool([char for char in text if char.isupper()])


class CompletionLineEdit(HintedLineEdit):
    """A lineedit with advanced completion abilities"""

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

    def __init__(
        self, context, model_factory, hint='', show_all_completions=False, parent=None
    ):
        HintedLineEdit.__init__(self, context, hint, parent=parent)
        # Tracks when the completion popup was active during key events

        self.context = context
        # The most recently selected completion item
        self._selection = None
        self._show_all_completions = show_all_completions

        # Create a completion model
        completion_model = model_factory(context, self)
        completer = Completer(completion_model, self)
        completer.setWidget(self)
        self._completer = completer
        self._completion_model = completion_model

        # The delegate highlights matching completion text in the popup widget
        self._delegate = HighlightDelegate(self)
        completer.popup().setItemDelegate(self._delegate)

        self.textChanged.connect(self._text_changed)
        self._completer.activated.connect(self.choose_completion)
        self._completion_model.updated.connect(
            self._completions_updated, type=Qt.QueuedConnection
        )
        self.destroyed.connect(self.dispose)

    def __del__(self):
        self.dispose()

    def dispose(self, *args):
        self._completer.dispose()

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

    def _text_changed(self, full_text):
        match_text = self._last_word()
        self._do_text_changed(full_text, match_text)
        self.complete_last_word()

    def _do_text_changed(self, full_text, match_text):
        case_sensitive = _is_case_sensitive(match_text)
        if case_sensitive:
            self._completer.setCaseSensitivity(Qt.CaseSensitive)
        else:
            self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._delegate.set_highlight_text(match_text, case_sensitive)
        self._completer.set_match_text(full_text, match_text, case_sensitive)

    def update_matches(self):
        text = self._last_word()
        case_sensitive = _is_case_sensitive(text)
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
        value = self.value()
        return value != value.rstrip()

    def _last_word(self):
        if self._ends_with_whitespace():
            return ''
        words = self._words()
        if not words:
            return self.value()
        if not words[-1]:
            return ''
        return words[-1]

    def complete_last_word(self):
        self.update_matches()
        self.complete()

    def close_popup(self):
        """Close the completion popup"""
        self.popup().close()

    def _completions_updated(self):
        """Select the first completion item when completions are updated"""
        popup = self.popup()
        if self._completion_model.rowCount() == 0:
            popup.hide()
            return
        if not popup.isVisible():
            if not self.hasFocus() or not self._show_all_completions:
                return
        self.select_first_completion()

    def select_first_completion(self):
        """Select the first item in the completion model"""
        idx = self._completion_model.index(0, 0)
        mode = (
            QtCore.QItemSelectionModel.Rows | QtCore.QItemSelectionModel.SelectCurrent
        )
        self.popup().selectionModel().setCurrentIndex(idx, mode)

    def selected_completion(self):
        """Return the selected completion item"""
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
            return None
        return item.text()

    def select_completion(self):
        """Choose the selected completion option from the completion popup"""
        result = False
        visible = self.popup().isVisible()
        if visible:
            selection = self.selected_completion()
            if selection:
                self.choose_completion(selection)
                result = True
        return result

    def show_popup(self):
        """Display the completion popup"""
        self.refresh()
        x_val = self.x()
        y_val = self.y() + self.height()
        point = QtCore.QPoint(x_val, y_val)
        mapped = self.parent().mapToGlobal(point)
        popup = self.popup()
        popup.move(mapped.x(), mapped.y())
        popup.show()

    # Qt overrides
    def event(self, event):
        """Override QWidget::event() for tab completion"""
        event_type = event.type()

        if (
            event_type == QtCore.QEvent.KeyPress
            and event.key() == Qt.Key_Tab
            and self.select_completion()
        ):
            return True

        # Make sure the popup goes away during teardown
        if event_type == QtCore.QEvent.Close:
            self.close_popup()
        elif event_type == QtCore.QEvent.Hide:
            self.popup().hide()

        return super().event(event)

    def keyPressEvent(self, event):
        """Process completion and navigation events"""
        super().keyPressEvent(event)

        popup = self.popup()
        visible = popup.isVisible()

        # Hide the popup when the field becomes empty.
        is_empty = not self.value()
        if is_empty and event.modifiers() != Qt.ControlModifier:
            self.cleared.emit()
            if visible:
                popup.hide()

        # Activation keys select the completion when pressed and emit the
        # activated signal.  Navigation keys have lower priority, and only
        # emit when it wasn't already handled as an activation event.
        key = event.key()
        if key in self.ACTIVATION_KEYS and visible:
            if self.select_completion():
                self.activated.emit()
            return

        navigation = self.NAVIGATION_KEYS.get(key, None)
        if navigation:
            signal = getattr(self, navigation)
            signal.emit()
            return

        # Show the popup when Ctrl-Space is pressed.
        if (
            not visible
            and key == Qt.Key_Space
            and event.modifiers() == Qt.ControlModifier
        ):
            self.show_popup()


class GatherCompletionsThread(QtCore.QThread):
    items_gathered = Signal(object)

    def __init__(self, model):
        QtCore.QThread.__init__(self)
        self.model = model
        self.case_sensitive = False
        self.running = False

    def dispose(self):
        self.running = False
        utils.catch_runtime_error(self.wait)

    def run(self):
        text = None
        items = []
        self.running = True
        # Loop when the matched text changes between the start and end time.
        # This happens when gather_matches() takes too long and the
        # model's match_text changes in-between.
        while self.running and text != self.model.match_text:
            text = self.model.match_text
            items = self.model.gather_matches(self.case_sensitive)

        if self.running and text is not None:
            self.items_gathered.emit(items)


class HighlightDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate used for auto-completion to give formatted completion"""

    def __init__(self, parent):
        QtWidgets.QStyledItemDelegate.__init__(self, parent)
        self.widget = parent
        self.highlight_text = ''
        self.case_sensitive = False

        self.doc = QtGui.QTextDocument()
        # older PyQt4 does not have setDocumentMargin
        if hasattr(self.doc, 'setDocumentMargin'):
            self.doc.setDocumentMargin(0)

    def set_highlight_text(self, text, case_sensitive):
        """Sets the text that will be made bold when displayed"""
        self.highlight_text = text
        self.case_sensitive = case_sensitive

    def paint(self, painter, option, index):
        """Overloaded Qt method for custom painting of a model index"""
        if not self.highlight_text:
            QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)
            return
        text = index.data()
        if self.case_sensitive:
            html = text.replace(
                self.highlight_text, '<strong>%s</strong>' % self.highlight_text
            )
        else:
            match = re.match(
                r'(.*)(%s)(.*)' % re.escape(self.highlight_text), text, re.IGNORECASE
            )
            if match:
                start = match.group(1) or ''
                middle = match.group(2) or ''
                end = match.group(3) or ''
                html = start + ('<strong>%s</strong>' % middle) + end
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
        if params.state & QtWidgets.QStyle.State_Selected:
            color = params.palette.color(
                QtGui.QPalette.Active, QtGui.QPalette.HighlightedText
            )
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

    def __init__(self, context, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.context = context
        self.match_text = ''
        self.full_text = ''
        self.case_sensitive = False

        self.update_thread = GatherCompletionsThread(self)
        self.update_thread.items_gathered.connect(
            self.apply_matches, type=Qt.QueuedConnection
        )

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
        """Build widgets for all of the matching items"""
        if not match_tuple:
            # Results from background tasks may arrive after the widget
            # has been destroyed.
            utils.catch_runtime_error(self.set_items, [])
            return
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

        # Results from background tasks can arrive after the widget has been destroyed.
        utils.catch_runtime_error(self.set_items, items)

    def set_items(self, items):
        """Clear the widget and add items to the model"""
        self.clear()
        self.invisibleRootItem().appendRows(items)
        self.updated.emit()

    def dispose(self):
        self.update_thread.dispose()


def _identity(value):
    return value


def _lower(value):
    return value.lower()


def filter_matches(match_text, candidates, case_sensitive, sort_key=None):
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

    if case_sensitive:
        if sort_key is None:
            matches.sort()
        else:
            matches.sort(key=sort_key)
    else:
        if sort_key is None:
            matches.sort(key=_lower)
        else:
            matches.sort(key=lambda x: sort_key(_lower(x)))
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
        self.setFilterMode(QtCore.Qt.MatchContains)

        model.model_updated.connect(self.update, type=Qt.QueuedConnection)
        self.setModel(model)

    def update(self):
        self._model.update()

    def dispose(self):
        self._model.dispose()

    def set_match_text(self, full_text, match_text, case_sensitive):
        self._model.set_match_text(full_text, match_text, case_sensitive)


class GitCompletionModel(CompletionModel):
    def __init__(self, context, parent):
        CompletionModel.__init__(self, context, parent)
        self.context = context
        context.model.updated.connect(self.model_updated, type=Qt.QueuedConnection)

    def gather_matches(self, case_sensitive):
        refs = filter_matches(
            self.match_text, self.matches(), case_sensitive, sort_key=ref_sort_key
        )
        return (refs, (), set())

    def matches(self):
        return []


class GitRefCompletionModel(GitCompletionModel):
    """Completer for branches and tags"""

    def __init__(self, context, parent):
        GitCompletionModel.__init__(self, context, parent)
        context.model.refs_updated.connect(self.model_updated, type=Qt.QueuedConnection)

    def matches(self):
        model = self.context.model
        return model.local_branches + model.remote_branches + model.tags


def find_potential_branches(model):
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
    return potential_branches


class GitCreateBranchCompletionModel(GitCompletionModel):
    """Completer for naming new branches"""

    def matches(self):
        model = self.context.model
        potential_branches = find_potential_branches(model)
        return model.local_branches + potential_branches + model.tags


class GitCheckoutBranchCompletionModel(GitCompletionModel):
    """Completer for git checkout <branch>"""

    def matches(self):
        model = self.context.model
        potential_branches = find_potential_branches(model)
        return (
            model.local_branches
            + potential_branches
            + model.remote_branches
            + model.tags
        )


class GitBranchCompletionModel(GitCompletionModel):
    """Completer for local branches"""

    def __init__(self, context, parent):
        GitCompletionModel.__init__(self, context, parent)

    def matches(self):
        model = self.context.model
        return model.local_branches


class GitRemoteBranchCompletionModel(GitCompletionModel):
    """Completer for remote branches"""

    def __init__(self, context, parent):
        GitCompletionModel.__init__(self, context, parent)

    def matches(self):
        model = self.context.model
        return model.remote_branches


class GitPathCompletionModel(GitCompletionModel):
    """Base class for path completion"""

    def __init__(self, context, parent):
        GitCompletionModel.__init__(self, context, parent)

    def candidate_paths(self):
        return []

    def gather_matches(self, case_sensitive):
        paths, dirs = filter_path_matches(
            self.match_text, self.candidate_paths(), case_sensitive
        )
        return ((), paths, dirs)


class GitStatusFilterCompletionModel(GitPathCompletionModel):
    """Completer for modified files and folders for status filtering"""

    def __init__(self, context, parent):
        GitPathCompletionModel.__init__(self, context, parent)

    def candidate_paths(self):
        model = self.context.model
        return model.staged + model.unmerged + model.modified + model.untracked


class GitTrackedCompletionModel(GitPathCompletionModel):
    """Completer for tracked files and folders"""

    def __init__(self, context, parent):
        GitPathCompletionModel.__init__(self, context, parent)
        self.model_updated.connect(self.gather_paths, type=Qt.QueuedConnection)
        self._paths = []

    def gather_paths(self):
        context = self.context
        self._paths = gitcmds.tracked_files(context)

    def gather_matches(self, case_sensitive):
        if not self._paths:
            self.gather_paths()

        refs = []
        paths, dirs = filter_path_matches(self.match_text, self._paths, case_sensitive)
        return (refs, paths, dirs)


class GitPathsFromRefCompletionModel(GitTrackedCompletionModel):
    """Completer for tracked files and folders"""

    def __init__(self, context, ref, parent):
        super().__init__(context, parent)
        self.ref = ref

    def gather_paths(self):
        context = self.context
        self._paths = gitcmds.ls_tree_paths(context, self.ref)


class GitLogCompletionModel(GitRefCompletionModel):
    """Completer for arguments suitable for git-log like commands"""

    def __init__(self, context, parent):
        GitRefCompletionModel.__init__(self, context, parent)
        self._paths = []
        self._model = context.model
        self._runtask = qtutils.RunTask(parent=self)
        self._time = 0.0  # ensure that the first event runs a task.
        self.model_updated.connect(
            self._start_gathering_paths, type=Qt.QueuedConnection
        )

    def matches(self):
        """Return candidate values for completion"""
        matches = super().matches()
        return [
            '--all',
            '--all-match',
            '--author',
            '--after=two.days.ago',
            '--basic-regexp',
            '--before=two.days.ago',
            '--branches',
            '--committer',
            '--exclude',
            '--extended-regexp',
            '--find-object',
            '--first-parent',
            '--fixed-strings',
            '--full-diff',
            '--grep',
            '--invert-grep',
            '--merges',
            '--no-merges',
            '--not',
            '--perl-regexp',
            '--pickaxe-all',
            '--pickaxe-regex',
            '--regexp-ignore-case',
            '--tags',
            '-D',
            '-E',
            '-F',
            '-G',
            '-L',
            '-P',
            '-S',
            '@{upstream}',
        ] + matches

    def _start_gathering_paths(self):
        """Gather paths when the model changes"""
        # Debounce updates that land within 1 second of each other.
        if time.time() - self._time > 1.0:
            self._runtask.start(qtutils.SimpleTask(self.gather_paths))
        self._time = time.time()

    def gather_paths(self):
        """Gather paths and store them in the model"""
        self._time = time.time()
        if self._model.cfg.get(prefs.AUTOCOMPLETE_PATHS, True):
            self._paths = gitcmds.tracked_files(self.context)
        else:
            self._paths = []
        self._time = time.time()

    def gather_matches(self, case_sensitive):
        """Filter paths and refs to find matching entries"""
        if not self._paths:
            self.gather_paths()
        refs = filter_matches(
            self.match_text, self.matches(), case_sensitive, sort_key=ref_sort_key
        )
        paths, dirs = filter_path_matches(self.match_text, self._paths, case_sensitive)
        has_doubledash = (
            self.match_text == '--'
            or self.full_text.startswith('-- ')
            or ' -- ' in self.full_text
        )
        if has_doubledash:
            refs = []
        elif refs and paths:
            paths.insert(0, '--')

        return (refs, paths, dirs)


def bind_lineedit(model, hint='', show_all_completions=False):
    """Create a line edit bound against a specific model"""

    class BoundLineEdit(CompletionLineEdit):
        def __init__(self, context, hint=hint, parent=None):
            CompletionLineEdit.__init__(
                self,
                context,
                model,
                hint=hint,
                show_all_completions=show_all_completions,
                parent=parent,
            )

    return BoundLineEdit


# Concrete classes
GitLogLineEdit = bind_lineedit(GitLogCompletionModel, hint='<ref>')
GitRefLineEdit = bind_lineedit(GitRefCompletionModel, hint='<ref>')
GitCheckoutBranchLineEdit = bind_lineedit(
    GitCheckoutBranchCompletionModel,
    hint='<branch>',
    show_all_completions=True,
)
GitCreateBranchLineEdit = bind_lineedit(GitCreateBranchCompletionModel, hint='<branch>')
GitBranchLineEdit = bind_lineedit(GitBranchCompletionModel, hint='<branch>')
GitRemoteBranchLineEdit = bind_lineedit(
    GitRemoteBranchCompletionModel, hint='<remote-branch>'
)
GitStatusFilterLineEdit = bind_lineedit(GitStatusFilterCompletionModel, hint='<path>')
GitTrackedLineEdit = bind_lineedit(GitTrackedCompletionModel, hint='<path>')


class GitPathsFromRefLineEdit(CompletionLineEdit):
    """Filename completion for paths from a specific ref"""

    def __init__(
        self, context, ref, hint='<path>', show_all_completions=False, parent=None
    ):
        super().__init__(
            context,
            lambda ctx, parent: GitPathsFromRefCompletionModel(ctx, ref, parent),
            hint=hint,
            parent=parent,
        )


class GitDialog(QtWidgets.QDialog):
    # The "lineedit" argument is provided by the derived class constructor.
    def __init__(self, lineedit, context, title, text, parent, icon=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.context = context
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumWidth(333)

        self.label = QtWidgets.QLabel()
        self.label.setText(title)
        self.lineedit = lineedit(context)
        self.ok_button = qtutils.ok_button(text, icon=icon, enabled=False)
        self.close_button = qtutils.close_button()

        self.button_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            qtutils.STRETCH,
            self.close_button,
            self.ok_button,
        )

        self.main_layout = qtutils.vbox(
            defs.margin, defs.spacing, self.label, self.lineedit, self.button_layout
        )
        self.setLayout(self.main_layout)

        self.lineedit.textChanged.connect(self.text_changed)
        self.lineedit.enter.connect(self.accept)
        qtutils.connect_button(self.ok_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

        self.setFocusProxy(self.lineedit)
        self.lineedit.setFocus()

    def text(self):
        return self.lineedit.text()

    def text_changed(self, _txt):
        self.ok_button.setEnabled(bool(self.text()))

    def set_text(self, ref):
        self.lineedit.setText(ref)

    @classmethod
    def get(cls, context, title, text, parent, default=None, icon=None):
        dlg = cls(context, title, text, parent, icon=icon)
        if default:
            dlg.set_text(default)

        dlg.show()
        QtCore.QTimer().singleShot(250, dlg.lineedit.show_popup)

        if dlg.exec_() == cls.Accepted:
            return dlg.text()
        return None


class GitRefDialog(GitDialog):
    def __init__(self, context, title, text, parent, icon=None):
        GitDialog.__init__(
            self, GitRefLineEdit, context, title, text, parent, icon=icon
        )


class GitCheckoutBranchDialog(GitDialog):
    def __init__(self, context, title, text, parent, icon=None):
        GitDialog.__init__(
            self, GitCheckoutBranchLineEdit, context, title, text, parent, icon=icon
        )


class GitBranchDialog(GitDialog):
    def __init__(self, context, title, text, parent, icon=None):
        GitDialog.__init__(
            self, GitBranchLineEdit, context, title, text, parent, icon=icon
        )


class GitRemoteBranchDialog(GitDialog):
    def __init__(self, context, title, text, parent, icon=None):
        GitDialog.__init__(
            self, GitRemoteBranchLineEdit, context, title, text, parent, icon=icon
        )
