from __future__ import absolute_import, division, print_function, unicode_literals
from functools import partial

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import actions
from .. import cmds
from .. import core
from .. import gitcmds
from .. import hotkeys
from .. import icons
from .. import textwrap
from .. import qtutils
from ..interaction import Interaction
from ..gitcmds import commit_message_path
from ..i18n import N_
from ..models import dag
from ..models import prefs
from ..qtutils import get
from ..utils import Group
from . import defs
from .selectcommits import select_commits
from .spellcheck import SpellCheckTextEdit
from .text import HintedLineEdit


class CommitMessageEditor(QtWidgets.QFrame):
    commit_message_changed = Signal(object)
    cursor_changed = Signal(int, int)
    down = Signal()
    up = Signal()

    def __init__(self, context, parent):
        QtWidgets.QFrame.__init__(self, parent)
        self.context = context
        self.model = model = context.model
        self.spellcheck_initialized = False

        self._linebreak = None
        self._textwidth = None
        self._tabwidth = None

        # Actions
        self.signoff_action = qtutils.add_action(
            self, cmds.SignOff.name(), cmds.run(cmds.SignOff, context), hotkeys.SIGNOFF
        )
        self.signoff_action.setIcon(icons.style_dialog_apply())
        self.signoff_action.setToolTip(N_('Sign off on this commit'))

        self.commit_action = qtutils.add_action(
            self, N_('Commit@@verb'), self.commit, hotkeys.APPLY
        )
        self.commit_action.setIcon(icons.commit())
        self.commit_action.setToolTip(N_('Commit staged changes'))
        self.clear_action = qtutils.add_action(self, N_('Clear...'), self.clear)

        self.launch_editor = actions.launch_editor_at_line(context, self)
        self.launch_difftool = actions.launch_difftool(context, self)

        self.move_up = actions.move_up(self)
        self.move_down = actions.move_down(self)

        # Menu acctions
        self.menu_actions = menu_actions = [
            None,
            self.signoff_action,
            self.commit_action,
            None,
            self.launch_editor,
            self.launch_difftool,
            None,
            self.move_up,
            self.move_down,
        ]

        # Widgets
        self.summary = CommitSummaryLineEdit(context)
        self.summary.setMinimumHeight(defs.tool_button_height)
        self.summary.menu_actions.extend(menu_actions)

        cfg = context.cfg
        self.summary_validator = MessageValidator(context, parent=self.summary)
        self.summary.setValidator(self.summary_validator)

        self.description = CommitMessageTextEdit(context, parent=self)
        self.description.set_dictionary(cfg.get('cola.dictionary', None))
        self.description.menu_actions.extend(menu_actions)

        commit_button_tooltip = N_('Commit staged changes\n' 'Shortcut: Ctrl+Enter')
        self.commit_button = qtutils.create_button(
            text=N_('Commit@@verb'), tooltip=commit_button_tooltip, icon=icons.commit()
        )
        self.commit_group = Group(self.commit_action, self.commit_button)

        self.actions_menu = qtutils.create_menu(N_('Actions'), self)
        self.actions_button = qtutils.create_toolbutton(
            icon=icons.configure(), tooltip=N_('Actions...')
        )
        self.actions_button.setMenu(self.actions_menu)

        self.actions_menu.addAction(self.signoff_action)
        self.actions_menu.addAction(self.commit_action)
        self.actions_menu.addSeparator()

        # Amend checkbox
        self.amend_action = self.actions_menu.addAction(N_('Amend Last Commit'))
        self.amend_action.setIcon(icons.edit())
        self.amend_action.setCheckable(True)
        self.amend_action.setShortcut(hotkeys.AMEND)
        self.amend_action.setShortcutContext(Qt.ApplicationShortcut)

        # Bypass hooks
        self.bypass_commit_hooks_action = self.actions_menu.addAction(
            N_('Bypass Commit Hooks')
        )
        self.bypass_commit_hooks_action.setCheckable(True)
        self.bypass_commit_hooks_action.setChecked(False)

        # Sign commits
        self.sign_action = self.actions_menu.addAction(N_('Create Signed Commit'))
        self.sign_action.setCheckable(True)
        signcommits = cfg.get('cola.signcommits', default=False)
        self.sign_action.setChecked(signcommits)

        # Spell checker
        self.check_spelling_action = self.actions_menu.addAction(N_('Check Spelling'))
        self.check_spelling_action.setCheckable(True)
        spellcheck = prefs.spellcheck(context)
        self.check_spelling_action.setChecked(spellcheck)
        self.toggle_check_spelling(spellcheck)

        # Line wrapping
        self.autowrap_action = self.actions_menu.addAction(N_('Auto-Wrap Lines'))
        self.autowrap_action.setCheckable(True)
        self.autowrap_action.setChecked(prefs.linebreak(context))

        # Commit message
        self.actions_menu.addSeparator()
        self.load_commitmsg_menu = self.actions_menu.addMenu(
            N_('Load Previous Commit Message')
        )
        self.load_commitmsg_menu.aboutToShow.connect(self.build_commitmsg_menu)

        self.fixup_commit_menu = self.actions_menu.addMenu(N_('Fixup Previous Commit'))
        self.fixup_commit_menu.aboutToShow.connect(self.build_fixup_menu)

        self.toplayout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.actions_button,
            self.summary,
            self.commit_button,
        )
        self.toplayout.setContentsMargins(
            defs.margin, defs.no_margin, defs.no_margin, defs.no_margin
        )

        self.mainlayout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.toplayout, self.description
        )
        self.setLayout(self.mainlayout)

        qtutils.connect_button(self.commit_button, self.commit)

        # Broadcast the amend mode
        qtutils.connect_action_bool(
            self.amend_action, partial(cmds.run(cmds.AmendMode), context)
        )
        qtutils.connect_action_bool(
            self.check_spelling_action, self.toggle_check_spelling
        )

        # Handle the one-off autowrapping
        qtutils.connect_action_bool(self.autowrap_action, self.set_linebreak)

        qtutils.add_action(
            self.summary, N_('Move Down'), self.focus_description, *hotkeys.ACCEPT
        )

        qtutils.add_action(
            self.summary, N_('Move Down'), self.summary_cursor_down, hotkeys.DOWN
        )

        self.model.add_observer(
            self.model.message_commit_message_changed, self.commit_message_changed.emit
        )

        self.commit_message_changed.connect(
            self.set_commit_message, type=Qt.QueuedConnection
        )

        self.summary.cursor_changed.connect(self.cursor_changed.emit)
        self.description.cursor_changed.connect(
            # description starts at line 2
            lambda row, col: self.cursor_changed.emit(row + 2, col)
        )

        # pylint: disable=no-member
        self.summary.textChanged.connect(self.commit_summary_changed)
        self.description.textChanged.connect(self._commit_message_changed)
        self.description.leave.connect(self.focus_summary)

        self.commit_group.setEnabled(False)

        self.set_expandtab(prefs.expandtab(context))
        self.set_tabwidth(prefs.tabwidth(context))
        self.set_textwidth(prefs.textwidth(context))
        self.set_linebreak(prefs.linebreak(context))

        # Loading message
        commit_msg = ''
        commit_msg_path = commit_message_path(context)
        if commit_msg_path:
            commit_msg = core.read(commit_msg_path)
        model.set_commitmsg(commit_msg)

        # Allow tab to jump from the summary to the description
        self.setTabOrder(self.summary, self.description)
        self.setFont(qtutils.diff_font(context))
        self.setFocusProxy(self.summary)

        cfg.add_observer(cfg.message_user_config_changed, self.config_changed)

    def config_changed(self, key, value):
        if key != prefs.SPELL_CHECK:
            return
        if get(self.check_spelling_action) == value:
            return
        self.check_spelling_action.setChecked(value)
        self.toggle_check_spelling(value)

    def set_initial_size(self):
        self.setMaximumHeight(133)
        QtCore.QTimer.singleShot(1, self.restore_size)

    def restore_size(self):
        self.setMaximumHeight(2 ** 13)

    def focus_summary(self):
        self.summary.setFocus()

    def focus_description(self):
        self.description.setFocus()

    def summary_cursor_down(self):
        """Handle the down key in the summary field

        If the cursor is at the end of the line then focus the description.
        Otherwise, move the cursor to the end of the line so that a
        subsequence "down" press moves to the end of the line.

        """
        cur_position = self.summary.cursorPosition()
        end_position = len(get(self.summary))
        if cur_position == end_position:
            self.focus_description()
        else:
            self.summary.setCursorPosition(end_position)

    def commit_message(self, raw=True):
        """Return the commit message as a unicode string"""
        summary = get(self.summary)
        if raw:
            description = get(self.description)
        else:
            description = self.formatted_description()
        if summary and description:
            return summary + '\n\n' + description
        if summary:
            return summary
        if description:
            return '\n\n' + description
        return ''

    def formatted_description(self):
        text = get(self.description)
        if not self._linebreak:
            return text
        return textwrap.word_wrap(text, self._tabwidth, self._textwidth)

    def commit_summary_changed(self, value):
        """Respond to changes to the `summary` field

        Newlines can enter the `summary` field when pasting, which is
        undesirable.  Break the pasted value apart into the separate
        (summary, description) values and move the description over to the
        "extended description" field.

        """
        if '\n' in value:
            summary, description = value.split('\n', 1)
            description = description.lstrip('\n')
            cur_description = get(self.description)
            if cur_description:
                description = description + '\n' + cur_description
            # this callback is triggered by changing `summary`
            # so disable signals for `summary` only.
            self.summary.set_value(summary, block=True)
            self.description.set_value(description)
        self._commit_message_changed()

    def _commit_message_changed(self, _value=None):
        """Update the model when values change"""
        message = self.commit_message()
        self.model.set_commitmsg(message, notify=False)
        self.refresh_palettes()
        self.update_actions()

    def clear(self):
        if not Interaction.confirm(
            N_('Clear commit message?'),
            N_('The commit message will be cleared.'),
            N_('This cannot be undone.  Clear commit message?'),
            N_('Clear commit message'),
            default=True,
            icon=icons.discard(),
        ):
            return
        self.model.set_commitmsg('')

    def update_actions(self):
        commit_enabled = bool(get(self.summary))
        self.commit_group.setEnabled(commit_enabled)

    def refresh_palettes(self):
        """Update the color palette for the hint text"""
        self.summary.hint.refresh()
        self.description.hint.refresh()

    def set_commit_message(self, message):
        """Set the commit message to match the observed model"""
        # Parse the "summary" and "description" fields
        lines = message.splitlines()

        num_lines = len(lines)

        if num_lines == 0:
            # Message is empty
            summary = ''
            description = ''

        elif num_lines == 1:
            # Message has a summary only
            summary = lines[0]
            description = ''

        elif num_lines == 2:
            # Message has two lines; this is not a common case
            summary = lines[0]
            description = lines[1]

        else:
            # Summary and several description lines
            summary = lines[0]
            if lines[1]:
                # We usually skip this line but check just in case
                description_lines = lines[1:]
            else:
                description_lines = lines[2:]
            description = '\n'.join(description_lines)

        focus_summary = not summary
        focus_description = not description

        # Update summary
        self.summary.set_value(summary, block=True)

        # Update description
        self.description.set_value(description, block=True)

        # Update text color
        self.refresh_palettes()

        # Focus the empty summary or description
        if focus_summary:
            self.summary.setFocus()
        elif focus_description:
            self.description.setFocus()
        else:
            self.summary.cursor_position.emit()

        self.update_actions()

    def set_expandtab(self, value):
        self.description.set_expandtab(value)

    def set_tabwidth(self, width):
        self._tabwidth = width
        self.description.set_tabwidth(width)

    def set_textwidth(self, width):
        self._textwidth = width
        self.description.set_textwidth(width)

    def set_linebreak(self, brk):
        self._linebreak = brk
        self.description.set_linebreak(brk)
        with qtutils.BlockSignals(self.autowrap_action):
            self.autowrap_action.setChecked(brk)

    def setFont(self, font):
        """Pass the setFont() calls down to the text widgets"""
        self.summary.setFont(font)
        self.description.setFont(font)

    def set_mode(self, mode):
        can_amend = not self.model.is_merging
        checked = mode == self.model.mode_amend
        with qtutils.BlockSignals(self.amend_action):
            self.amend_action.setEnabled(can_amend)
            self.amend_action.setChecked(checked)

    def commit(self):
        """Attempt to create a commit from the index and commit message."""
        context = self.context
        if not bool(get(self.summary)):
            # Describe a good commit message
            error_msg = N_(
                'Please supply a commit message.\n\n'
                'A good commit message has the following format:\n\n'
                '- First line: Describe in one sentence what you did.\n'
                '- Second line: Blank\n'
                '- Remaining lines: Describe why this change is good.\n'
            )
            Interaction.log(error_msg)
            Interaction.information(N_('Missing Commit Message'), error_msg)
            return

        msg = self.commit_message(raw=False)

        # We either need to have something staged, or be merging.
        # If there was a merge conflict resolved, there may not be anything
        # to stage, but we still need to commit to complete the merge.
        if not (self.model.staged or self.model.is_merging):
            error_msg = N_(
                'No changes to commit.\n\n'
                'You must stage at least 1 file before you can commit.'
            )
            if self.model.modified:
                informative_text = N_(
                    'Would you like to stage and ' 'commit all modified files?'
                )
                if not Interaction.confirm(
                    N_('Stage and commit?'),
                    error_msg,
                    informative_text,
                    N_('Stage and Commit'),
                    default=True,
                    icon=icons.save(),
                ):
                    return
            else:
                Interaction.information(N_('Nothing to commit'), error_msg)
                return
            cmds.do(cmds.StageModified, context)

        # Warn that amending published commits is generally bad
        amend = get(self.amend_action)
        check_published = prefs.check_published_commits(context)
        if (
            amend
            and check_published
            and self.model.is_commit_published()
            and not Interaction.confirm(
                N_('Rewrite Published Commit?'),
                N_(
                    'This commit has already been published.\n'
                    'This operation will rewrite published history.\n'
                    'You probably don\'t want to do this.'
                ),
                N_('Amend the published commit?'),
                N_('Amend Commit'),
                default=False,
                icon=icons.save(),
            )
        ):
            return
        no_verify = get(self.bypass_commit_hooks_action)
        sign = get(self.sign_action)
        cmds.do(cmds.Commit, context, amend, msg, sign, no_verify=no_verify)
        self.bypass_commit_hooks_action.setChecked(False)

    def build_fixup_menu(self):
        self.build_commits_menu(
            cmds.LoadFixupMessage,
            self.fixup_commit_menu,
            self.choose_fixup_commit,
            prefix='fixup! ',
        )

    def build_commitmsg_menu(self):
        self.build_commits_menu(
            cmds.LoadCommitMessageFromOID,
            self.load_commitmsg_menu,
            self.choose_commit_message,
        )

    def build_commits_menu(self, cmd, menu, chooser, prefix=''):
        context = self.context
        params = dag.DAG('HEAD', 6)
        commits = dag.RepoReader(context, params)

        menu_commits = []
        for idx, c in enumerate(commits.get()):
            menu_commits.insert(0, c)
            if idx > 5:
                continue

        menu.clear()
        for c in menu_commits:
            menu.addAction(prefix + c.summary, cmds.run(cmd, context, c.oid))

        if len(commits) == 6:
            menu.addSeparator()
            menu.addAction(N_('More...'), chooser)

    def choose_commit(self, cmd):
        context = self.context
        revs, summaries = gitcmds.log_helper(context)
        oids = select_commits(
            context, N_('Select Commit'), revs, summaries, multiselect=False
        )
        if not oids:
            return
        oid = oids[0]
        cmds.do(cmd, context, oid)

    def choose_commit_message(self):
        self.choose_commit(cmds.LoadCommitMessageFromOID)

    def choose_fixup_commit(self):
        self.choose_commit(cmds.LoadFixupMessage)

    def toggle_check_spelling(self, enabled):
        spellcheck = self.description.spellcheck
        cfg = self.context.cfg

        if cfg.get_user(prefs.SPELL_CHECK) != enabled:
            cfg.set_user(prefs.SPELL_CHECK, enabled)
        if enabled and not self.spellcheck_initialized:
            # Add our name to the dictionary
            self.spellcheck_initialized = True
            user_name = cfg.get('user.name')
            if user_name:
                for part in user_name.split():
                    spellcheck.add_word(part)

            # Add our email address to the dictionary
            user_email = cfg.get('user.email')
            if user_email:
                for part in user_email.split('@'):
                    for elt in part.split('.'):
                        spellcheck.add_word(elt)

            # git jargon
            spellcheck.add_word('Acked')
            spellcheck.add_word('Signed')
            spellcheck.add_word('Closes')
            spellcheck.add_word('Fixes')

        self.description.highlighter.enable(enabled)


class MessageValidator(QtGui.QValidator):
    """Prevent invalid branch names"""

    config_updated = Signal()

    def __init__(self, context, parent=None):
        super(MessageValidator, self).__init__(parent)
        self.context = context
        self._comment_char = None
        self._cfg = cfg = context.cfg
        self.refresh()
        # pylint: disable=no-member
        self.config_updated.connect(self.refresh, type=Qt.QueuedConnection)
        cfg.add_observer(cfg.message_updated, self.emit_config_updated)
        self.destroyed.connect(self.teardown)

    def teardown(self):
        self._cfg.remove_observer(self.emit_config_updated)

    def emit_config_updated(self):
        self.config_updated.emit()

    def refresh(self):
        """Update comment char in response to config changes"""
        self._comment_char = prefs.comment_char(self.context)

    def validate(self, string, idx):
        """Scrub whitespace and validate the commit message"""
        string = string.lstrip()
        if string.startswith(self._comment_char):
            state = self.Invalid
        else:
            state = self.Acceptable
        return (state, string, idx)


class CommitSummaryLineEdit(HintedLineEdit):

    cursor = Signal(int, int)

    def __init__(self, context, parent=None):
        hint = N_('Commit summary')
        HintedLineEdit.__init__(self, context, hint, parent=parent)
        self.menu_actions = []

    def build_menu(self):
        menu = self.createStandardContextMenu()
        add_menu_actions(menu, self.menu_actions)
        return menu

    def contextMenuEvent(self, event):
        menu = self.build_menu()
        menu.exec_(self.mapToGlobal(event.pos()))


# pylint: disable=too-many-ancestors
class CommitMessageTextEdit(SpellCheckTextEdit):
    leave = Signal()

    def __init__(self, context, parent=None):
        hint = N_('Extended description...')
        SpellCheckTextEdit.__init__(self, context, hint, parent)
        self.menu_actions = []

        self.action_emit_leave = qtutils.add_action(
            self, 'Shift Tab', self.leave.emit, hotkeys.LEAVE
        )

    def build_menu(self):
        menu, _ = self.context_menu()
        add_menu_actions(menu, self.menu_actions)
        return menu

    def contextMenuEvent(self, event):
        menu = self.build_menu()
        menu.exec_(self.mapToGlobal(event.pos()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            position = cursor.position()
            if position == 0:
                # The cursor is at the beginning of the line.
                # If we have selection then simply reset the cursor.
                # Otherwise, emit a signal so that the parent can
                # change focus.
                if cursor.hasSelection():
                    cursor.setPosition(0)
                    self.setTextCursor(cursor)
                else:
                    self.leave.emit()
                event.accept()
                return
            text_before = self.toPlainText()[:position]
            lines_before = text_before.count('\n')
            if lines_before == 0:
                # If we're on the first line, but not at the
                # beginning, then move the cursor to the beginning
                # of the line.
                if event.modifiers() & Qt.ShiftModifier:
                    mode = QtGui.QTextCursor.KeepAnchor
                else:
                    mode = QtGui.QTextCursor.MoveAnchor
                cursor.setPosition(0, mode)
                self.setTextCursor(cursor)
                event.accept()
                return
        elif event.key() == Qt.Key_Down:
            cursor = self.textCursor()
            position = cursor.position()
            all_text = self.toPlainText()
            text_after = all_text[position:]
            lines_after = text_after.count('\n')
            if lines_after == 0:
                if event.modifiers() & Qt.ShiftModifier:
                    mode = QtGui.QTextCursor.KeepAnchor
                else:
                    mode = QtGui.QTextCursor.MoveAnchor
                cursor.setPosition(len(all_text), mode)
                self.setTextCursor(cursor)
                event.accept()
                return
        SpellCheckTextEdit.keyPressEvent(self, event)

    def setFont(self, font):
        SpellCheckTextEdit.setFont(self, font)
        fm = self.fontMetrics()
        self.setMinimumSize(QtCore.QSize(fm.width('MMMM'), fm.height() * 2))


def add_menu_actions(menu, menu_actions):
    """Add actions to a menu, treating None as a separator"""
    for action in menu_actions:
        if action is None:
            menu.addSeparator()
        else:
            menu.addAction(action)
