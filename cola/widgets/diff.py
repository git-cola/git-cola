from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt, SIGNAL

from cola import cmds
from cola import core
from cola import gitcmds
from cola import gravatar
from cola import qtutils
from cola.cmds import run
from cola.i18n import N_
from cola.models import main
from cola.models import selection
from cola.qtutils import add_action
from cola.qtutils import create_action_button
from cola.qtutils import create_menu
from cola.qtutils import DiffSyntaxHighlighter
from cola.qtutils import options_icon
from cola.widgets import defs
from cola.widgets.text import MonoTextView
from cola.compat import ustr


COMMITS_SELECTED = 'COMMITS_SELECTED'
FILES_SELECTED = 'FILES_SELECTED'


class DiffTextEdit(MonoTextView):
    def __init__(self, parent, whitespace=True):

        MonoTextView.__init__(self, parent)
        # Diff/patch syntax highlighter
        self.highlighter = DiffSyntaxHighlighter(self.document(),
                                                 whitespace=whitespace)


class DiffEditor(DiffTextEdit):

    def __init__(self, parent):
        DiffTextEdit.__init__(self, parent)
        self.model = model = main.model()

        # "Diff Options" tool menu
        self.diff_ignore_space_at_eol_action = add_action(self,
                N_('Ignore changes in whitespace at EOL'),
                self._update_diff_opts)
        self.diff_ignore_space_at_eol_action.setCheckable(True)

        self.diff_ignore_space_change_action = add_action(self,
                N_('Ignore changes in amount of whitespace'),
                self._update_diff_opts)
        self.diff_ignore_space_change_action.setCheckable(True)

        self.diff_ignore_all_space_action = add_action(self,
                N_('Ignore all whitespace'),
                self._update_diff_opts)
        self.diff_ignore_all_space_action.setCheckable(True)

        self.diff_function_context_action = add_action(self,
                N_('Show whole surrounding functions of changes'),
                self._update_diff_opts)
        self.diff_function_context_action.setCheckable(True)

        self.diffopts_button = create_action_button(
                tooltip=N_('Diff Options'), icon=options_icon())
        self.diffopts_menu = create_menu(N_('Diff Options'),
                                         self.diffopts_button)

        self.diffopts_menu.addAction(self.diff_ignore_space_at_eol_action)
        self.diffopts_menu.addAction(self.diff_ignore_space_change_action)
        self.diffopts_menu.addAction(self.diff_ignore_all_space_action)
        self.diffopts_menu.addAction(self.diff_function_context_action)
        self.diffopts_button.setMenu(self.diffopts_menu)
        qtutils.hide_button_menu_indicator(self.diffopts_button)

        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.diffopts_button)

        self.action_process_section = qtutils.add_action(self,
                N_('Process Diff Region'),
                self.apply_section, Qt.Key_H)
        self.action_process_selection = qtutils.add_action(self,
                N_('Process Selection'),
                self.apply_selection, Qt.Key_S)

        self.launch_editor = qtutils.add_action(self,
                cmds.LaunchEditor.name(), run(cmds.LaunchEditor),
                cmds.LaunchEditor.SHORTCUT,
                'Return', 'Enter')
        self.launch_editor.setIcon(qtutils.options_icon())

        self.launch_difftool = qtutils.add_action(self,
                cmds.LaunchDifftool.name(), run(cmds.LaunchDifftool),
                cmds.LaunchDifftool.SHORTCUT)
        self.launch_difftool.setIcon(qtutils.icon('git.svg'))

        self.action_stage_selection = qtutils.add_action(self,
                N_('Stage &Selected Lines'),
                self.stage_selection)
        self.action_stage_selection.setIcon(qtutils.icon('add.svg'))
        self.action_stage_selection.setShortcut(Qt.Key_S)

        self.action_revert_selection = qtutils.add_action(self,
                N_('Revert Selected Lines...'),
                self.revert_selection)
        self.action_revert_selection.setIcon(qtutils.icon('undo.svg'))

        self.action_unstage_selection = qtutils.add_action(self,
                N_('Unstage &Selected Lines'),
                self.unstage_selection)
        self.action_unstage_selection.setIcon(qtutils.icon('remove.svg'))
        self.action_unstage_selection.setShortcut(Qt.Key_S)

        model.add_observer(model.message_diff_text_changed, self._emit_text)

        self.connect(self, SIGNAL('copyAvailable(bool)'),
                     self.enable_selection_actions)

        self.connect(self, SIGNAL('set_text'), self.setPlainText)

    def _emit_text(self, text):
        self.emit(SIGNAL('set_text'), text)

    def _update_diff_opts(self):
        space_at_eol = self.diff_ignore_space_at_eol_action.isChecked()
        space_change = self.diff_ignore_space_change_action.isChecked()
        all_space = self.diff_ignore_all_space_action.isChecked()
        function_context = self.diff_function_context_action.isChecked()

        gitcmds.update_diff_overrides(space_at_eol,
                                      space_change,
                                      all_space,
                                      function_context)
        self.emit(SIGNAL('diff_options_updated()'))

    # Qt overrides
    def contextMenuEvent(self, event):
        """Create the context menu for the diff display."""
        menu = QtGui.QMenu(self)
        s = selection.selection()
        filename = selection.filename()

        if self.model.stageable():
            if s.modified and s.modified[0] in main.model().submodules:
                action = menu.addAction(qtutils.icon('add.svg'),
                                        cmds.Stage.name(),
                                        cmds.run(cmds.Stage, s.modified))
                action.setShortcut(cmds.Stage.SHORTCUT)
                menu.addAction(qtutils.git_icon(),
                               N_('Launch git-cola'),
                               cmds.run(cmds.OpenRepo,
                                        core.abspath(s.modified[0])))
            elif s.modified:
                action = menu.addAction(qtutils.icon('add.svg'),
                                        N_('Stage Diff Region'),
                                        self.stage_section)
                action.setShortcut(Qt.Key_H)
                menu.addAction(self.action_stage_selection)
                menu.addSeparator()
                menu.addAction(qtutils.icon('undo.svg'),
                               N_('Revert Diff Region...'),
                               self.revert_section)
                menu.addAction(self.action_revert_selection)

        if self.model.unstageable():
            if s.staged and s.staged[0] in main.model().submodules:
                action = menu.addAction(qtutils.icon('remove.svg'),
                                        cmds.Unstage.name(),
                                        cmds.do(cmds.Unstage, s.staged))
                action.setShortcut(cmds.Unstage.SHORTCUT)
                menu.addAction(qtutils.git_icon(),
                               N_('Launch git-cola'),
                               cmds.do(cmds.OpenRepo,
                                       core.abspath(s.staged[0])))
            elif s.staged:
                action = menu.addAction(qtutils.icon('remove.svg'),
                                        N_('Unstage Diff Region'),
                                        self.unstage_section)
                action.setShortcut(Qt.Key_H)
                menu.addAction(self.action_unstage_selection)

        if self.model.stageable() or self.model.unstageable():
            # Do not show the "edit" action when the file does not exist.
            # Untracked files exist by definition.
            if filename and core.exists(filename):
                menu.addSeparator()
                menu.addAction(self.launch_editor)

            # Removed files can still be diffed.
            menu.addAction(self.launch_difftool)

        menu.addSeparator()
        action = menu.addAction(qtutils.icon('edit-copy.svg'),
                                N_('Copy'), self.copy)
        action.setShortcut(QtGui.QKeySequence.Copy)

        action = menu.addAction(qtutils.icon('edit-select-all.svg'),
                                N_('Select All'), self.selectAll)
        action.setShortcut(QtGui.QKeySequence.SelectAll)
        menu.exec_(self.mapToGlobal(event.pos()))

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            # Intercept the Control modifier to not resize the text
            # when doing control+mousewheel
            event.accept()
            event = QtGui.QWheelEvent(event.pos(), event.delta(),
                                      Qt.NoButton,
                                      Qt.NoModifier,
                                      event.orientation())

        return DiffTextEdit.wheelEvent(self, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Intercept right-click to move the cursor to the current position.
            # setTextCursor() clears the selection so this is only done when
            # nothing is selected.
            _, selection_text = self.offset_and_selection()
            if not selection_text:
                cursor = self.cursorForPosition(event.pos())
                self.setTextCursor(cursor)

        return DiffTextEdit.mousePressEvent(self, event)

    def setPlainText(self, text):
        """setPlainText(str) while retaining scrollbar positions"""
        mode = self.model.mode
        highlight = (mode != self.model.mode_none and
                     mode != self.model.mode_untracked)
        self.highlighter.set_enabled(highlight)

        scrollbar = self.verticalScrollBar()
        if scrollbar:
            scrollvalue = scrollbar.value()
        else:
            scrollvalue = None

        if text is None:
            return

        offset, selection_text = self.offset_and_selection()
        old_text = ustr(self.toPlainText())

        DiffTextEdit.setPlainText(self, text)

        # If the old selection exists in the new text then
        # re-select it.
        if selection_text and selection_text in text:
            idx = text.index(selection_text)
            cursor = self.textCursor()
            cursor.setPosition(idx)
            cursor.setPosition(idx + len(selection_text),
                               QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)

        # Otherwise, if the text is identical and there
        # is no selection then restore the cursor position.
        elif text == old_text:
            cursor = self.textCursor()
            cursor.setPosition(offset)
            self.setTextCursor(cursor)

        if scrollbar and scrollvalue is not None:
            scrollbar.setValue(scrollvalue)

    def offset_and_selection(self):
        cursor = self.textCursor()
        offset = cursor.position()
        selection_text = ustr(cursor.selection().toPlainText())
        return offset, selection_text

    # Mutators
    def enable_selection_actions(self, enabled):
        self.action_revert_selection.setEnabled(enabled)
        self.action_unstage_selection.setEnabled(enabled)
        self.action_stage_selection.setEnabled(enabled)

    def apply_section(self):
        s = selection.single_selection()
        if self.model.stageable() and s.modified:
            self.stage_section()
        elif self.model.unstageable():
            self.unstage_section()

    def apply_selection(self):
        s = selection.single_selection()
        if self.model.stageable() and s.modified:
            self.stage_selection()
        elif self.model.unstageable():
            self.unstage_selection()

    def stage_section(self):
        """Stage a specific section."""
        self.process_diff_selection(staged=False)

    def stage_selection(self):
        """Stage selected lines."""
        self.process_diff_selection(staged=False, selected=True)

    def unstage_section(self, cached=True):
        """Unstage a section."""
        self.process_diff_selection(staged=True)

    def unstage_selection(self):
        """Unstage selected lines."""
        self.process_diff_selection(staged=True, selected=True)

    def revert_section(self):
        """Destructively remove a section from a worktree file."""
        if not qtutils.confirm(N_('Revert Diff Region?'),
                               N_('This operation drops uncommitted changes.\n'
                                  'These changes cannot be recovered.'),
                               N_('Revert the uncommitted changes?'),
                               N_('Revert Diff Region'),
                               default=True,
                               icon=qtutils.icon('undo.svg')):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True)

    def revert_selection(self):
        """Destructively check out content for the selected file from $head."""
        if not qtutils.confirm(N_('Revert Selected Lines?'),
                               N_('This operation drops uncommitted changes.\n'
                                  'These changes cannot be recovered.'),
                               N_('Revert the uncommitted changes?'),
                               N_('Revert Selected Lines'),
                               default=True,
                               icon=qtutils.icon('undo.svg')):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True, selected=True)

    def process_diff_selection(self, selected=False,
                               staged=True, apply_to_worktree=False,
                               reverse=False):
        """Implement un/staging of selected lines or sections."""
        if selection.selection_model().is_empty():
            return
        offset, selection_text = self.offset_and_selection()
        cmds.do(cmds.ApplyDiffSelection,
                staged, selected, offset, selection_text, apply_to_worktree)



class DiffWidget(QtGui.QWidget):

    def __init__(self, notifier, parent):
        QtGui.QWidget.__init__(self, parent)

        author_font = QtGui.QFont(self.font())
        author_font.setPointSize(int(author_font.pointSize() * 1.1))

        summary_font = QtGui.QFont(author_font)
        summary_font.setWeight(QtGui.QFont.Bold)

        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                                   QtGui.QSizePolicy.Minimum)

        self.gravatar_label = gravatar.GravatarLabel()

        self.author_label = TextLabel()
        self.author_label.setTextFormat(Qt.RichText)
        self.author_label.setFont(author_font)
        self.author_label.setSizePolicy(policy)
        self.author_label.setAlignment(Qt.AlignBottom)
        self.author_label.elide()

        self.summary_label = TextLabel()
        self.summary_label.setTextFormat(Qt.PlainText)
        self.summary_label.setFont(summary_font)
        self.summary_label.setSizePolicy(policy)
        self.summary_label.setAlignment(Qt.AlignTop)
        self.summary_label.elide()

        self.sha1_label = TextLabel()
        self.sha1_label.setTextFormat(Qt.PlainText)
        self.sha1_label.setSizePolicy(policy)
        self.sha1_label.setAlignment(Qt.AlignTop)
        self.sha1_label.elide()

        self.diff = DiffTextEdit(self, whitespace=False)
        self.tasks = set()
        self.reflector = QtCore.QObject(self)

        self.info_layout = QtGui.QVBoxLayout()
        self.info_layout.setMargin(defs.no_margin)
        self.info_layout.setSpacing(defs.no_spacing)
        self.info_layout.addWidget(self.author_label)
        self.info_layout.addWidget(self.summary_label)
        self.info_layout.addWidget(self.sha1_label)

        self.logo_layout = QtGui.QHBoxLayout()
        self.logo_layout.setContentsMargins(defs.margin, 0, defs.margin, 0)
        self.logo_layout.setSpacing(defs.button_spacing)
        self.logo_layout.addWidget(self.gravatar_label)
        self.logo_layout.addLayout(self.info_layout)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.no_margin)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addLayout(self.logo_layout)
        self.main_layout.addWidget(self.diff)
        self.setLayout(self.main_layout)

        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)
        notifier.add_observer(FILES_SELECTED, self.files_selected)
        self.connect(self.reflector, SIGNAL('diff'), self.diff.setText)
        self.connect(self.reflector, SIGNAL('task_done'), self.task_done)

    def task_done(self, task):
        try:
            self.tasks.remove(task)
        except:
            pass

    def set_diff_sha1(self, sha1, filename=None):
        self.diff.setText('+++ ' + N_('Loading...'))
        task = DiffInfoTask(sha1, self.reflector, filename=filename)
        self.tasks.add(task)
        QtCore.QThreadPool.globalInstance().start(task)

    def commits_selected(self, commits):
        if len(commits) != 1:
            return
        commit = commits[0]
        self.sha1 = commit.sha1

        email = commit.email or ''
        summary = commit.summary or ''
        author = commit.author or ''

        template_args = {
                'author': author,
                'email': email,
                'summary': summary
        }

        author_text = ("""%(author)s &lt;"""
                       """<a href="mailto:%(email)s">"""
                       """%(email)s</a>&gt;"""
                       % template_args)

        author_template = '%(author)s <%(email)s>' % template_args
        self.author_label.set_template(author_text, author_template)
        self.summary_label.set_text(summary)
        self.sha1_label.set_text(self.sha1)

        self.set_diff_sha1(self.sha1)
        self.gravatar_label.set_email(email)

    def files_selected(self, filenames):
        if not filenames:
            return
        self.set_diff_sha1(self.sha1, filenames[0])


class TextLabel(QtGui.QLabel):

    def __init__(self, parent=None):
        QtGui.QLabel.__init__(self, parent)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse |
                                     Qt.LinksAccessibleByMouse)
        self._display = ''
        self._template = ''
        self._text = ''
        self._elide = False
        self._metrics = QtGui.QFontMetrics(self.font())
        self.setOpenExternalLinks(True)

    def elide(self):
        self._elide = True

    def set_text(self, text):
        self.set_template(text, text)

    def set_template(self, text, template):
        self._display = text
        self._text = text
        self._template = template
        self.update_text(self.width())
        self.setText(self._display)

    def update_text(self, width):
        self._display = self._text
        if not self._elide:
            return
        text = self._metrics.elidedText(self._template,
                                        Qt.ElideRight, width-2)
        if ustr(text) != self._template:
            self._display = text

    # Qt overrides
    def setFont(self, font):
        self._metrics = QtGui.QFontMetrics(font)
        QtGui.QLabel.setFont(self, font)

    def resizeEvent(self, event):
        if self._elide:
            self.update_text(event.size().width())
            block = self.blockSignals(True)
            self.setText(self._display)
            self.blockSignals(block)
        QtGui.QLabel.resizeEvent(self, event)


class DiffInfoTask(QtCore.QRunnable):

    def __init__(self, sha1, reflector, filename=None):
        QtCore.QRunnable.__init__(self)
        self.sha1 = sha1
        self.reflector = reflector
        self.filename = filename

    def run(self):
        diff = gitcmds.diff_info(self.sha1, filename=self.filename)
        self.reflector.emit(SIGNAL('diff'), diff)
