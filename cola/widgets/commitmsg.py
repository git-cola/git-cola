import datetime
from functools import partial

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import actions
from .. import cmds
from .. import core
from .. import display
from .. import gitcmds
from .. import hotkeys
from .. import icons
from .. import textwrap
from .. import qtutils
from .. import spellcheck
from .. import utils
from ..interaction import Interaction
from ..gitcmds import commit_message_path
from ..i18n import N_
from ..models import dag
from ..models import prefs
from ..qtutils import get
from . import defs
from . import standard
from .selectcommits import select_commits
from .spellcheck import SpellCheckLineEdit, SpellCheckTextEdit
from .text import event_anchor_mode, is_shift_pressed


class CommitMessageEditor(QtWidgets.QFrame):
    commit_finished = Signal(object)
    cursor_changed = Signal(int, int)
    down = Signal()
    up = Signal()

    def __init__(self, context, parent):
        QtWidgets.QFrame.__init__(self, parent)
        cfg = context.cfg
        self.context = context
        self.model = model = context.model
        self.spellcheck_initialized = False
        self.spellcheck = spellcheck.NorvigSpellCheck()
        self.spellcheck.add_dictionaries(prefs.spelling_dictionaries(context))
        self.spellcheck.set_aspell_enabled(prefs.aspell_enabled(context))
        self.spellcheck.set_aspell_langs(prefs.aspell_languages(context))

        self._linebreak = None
        self._textwidth = None
        self._tabwidth = None
        self._last_commit_datetime = None  # The most recently selected commit date.
        self._last_commit_datetime_backup = None  # Used when amending.
        self._git_commit_date = None  # Overrides the commit date when committing.
        self._commit_authors = []  # Recently used author override values.
        self._last_git_commit_author = None  # The most recently selected author.
        self._git_commit_author = None  # Overrides the commit author when comitting.
        self._git_commit_author_backup = None  # Used when amending.

        self._widgets_initialized = False  # Defer setting the cursor position height.

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

        # Menu actions
        self.menu_actions = menu_actions = [
            self.signoff_action,
            self.commit_action,
            None,
            self.launch_editor,
            self.launch_difftool,
            None,
            self.move_up,
            self.move_down,
            None,
        ]

        # Widgets
        self.summary = CommitSummaryLineEdit(context, check=self.spellcheck)
        self.summary.menu_actions.extend(menu_actions)
        self.summary.addAction(self.commit_action)
        self.summary.addAction(self.move_up)
        self.summary.addAction(self.move_down)
        self.summary.addAction(self.signoff_action)

        self.description = CommitMessageTextEdit(
            context, check=self.spellcheck, parent=self
        )
        self.description.menu_actions.extend(menu_actions)

        commit_button_tooltip = N_('Commit staged changes\nShortcut: Ctrl+Enter')
        self.commit_button = qtutils.create_button(
            text=N_('Commit@@verb'), tooltip=commit_button_tooltip, icon=icons.commit()
        )
        self.commit_group = utils.Group(self.commit_action, self.commit_button)
        self.commit_progress_bar = standard.progress_bar(
            self,
            disable=(self.commit_button, self.summary, self.description),
        )

        # make the position label fixed size to avoid layout issues
        font = qtutils.default_monospace_font()
        font.setPixelSize(defs.action_text)
        text_width = qtutils.text_width(font, '999:999')
        cursor_position_label = self.cursor_position_label = QtWidgets.QLabel(self)
        cursor_position_label.setFont(font)
        cursor_position_label.setMinimumWidth(text_width)
        cursor_position_label.setAlignment(Qt.AlignCenter)

        self.actions_menu = qtutils.create_menu(N_('Actions'), self)
        self.actions_button = qtutils.create_toolbutton(
            icon=icons.configure(), tooltip=N_('Actions...')
        )
        self.actions_button.setMenu(self.actions_menu)

        self.actions_menu.addAction(self.signoff_action)
        self.actions_menu.addAction(self.commit_action)
        self.actions_menu.addSeparator()

        # Amend checkbox
        self.amend_action = qtutils.add_action_bool(
            self,
            N_('Amend Last Commit'),
            partial(cmds.run(cmds.AmendMode), context),
            False,
            *hotkeys.AMEND,
        )
        self.amend_action.setIcon(icons.edit())
        self.amend_action.setCheckable(True)
        self.amend_action.setShortcutContext(Qt.ApplicationShortcut)
        self.actions_menu.addAction(self.amend_action)

        # Commit Date
        self.commit_date_action = self.actions_menu.addAction(N_('Set Commit Date'))
        self.commit_date_action.setCheckable(True)
        self.commit_date_action.setChecked(False)
        qtutils.connect_action_bool(self.commit_date_action, self.set_commit_date)

        # Commit Author
        self.commit_author_action = self.actions_menu.addAction(N_('Set Commit Author'))
        self.commit_author_action.setCheckable(True)
        self.commit_author_action.setChecked(False)
        qtutils.connect_action_bool(self.commit_author_action, self.set_commit_author)

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
        spell_check = prefs.spellcheck(context)
        self.check_spelling_action.setChecked(spell_check)
        self.toggle_check_spelling(spell_check)

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

        # Display commit author overrides.
        self._author_close = qtutils.create_action_button(
            icon=icons.close(),
            tooltip=N_('Cancel the commit author override.'),
        )
        tooltip = N_('A commit will be recorded with this author')
        self._author_image = qtutils.pixmap_label(
            icons.person(), defs.default_icon, tooltip=tooltip, parent=self
        )
        self._author_label = qtutils.plain_text_label(tooltip=tooltip, parent=self)
        tooltip = N_('A commit will be recorded with this date and time')

        # Display commit date overrides.
        self._date_close = qtutils.create_action_button(
            icon=icons.close(),
            tooltip=N_('Cancel the commit date override.'),
        )
        self._date_image = qtutils.pixmap_label(
            icons.clock(), defs.default_icon, tooltip=tooltip, parent=self
        )
        self._date_label = qtutils.plain_text_label(tooltip=tooltip, parent=self)

        self.bottomlayout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self._author_close,
            self._author_image,
            self._author_label,
            qtutils.STRETCH,
            self._date_close,
            self._date_image,
            self._date_label,
        )
        self.toplayout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.actions_button,
            self.summary,
            self.commit_progress_bar,
            self.commit_button,
            self.cursor_position_label,
        )
        self.topwidget = QtWidgets.QWidget()
        self.topwidget.setLayout(self.toplayout)

        self.mainlayout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.description, self.bottomlayout
        )
        self.setLayout(self.mainlayout)

        qtutils.connect_button(self.commit_button, self.commit)
        qtutils.connect_button(
            self._author_close, lambda: self.set_commit_author(False)
        )
        qtutils.connect_button(self._date_close, lambda: self.set_commit_date(False))
        qtutils.connect_action_bool(
            self.check_spelling_action, self.toggle_check_spelling
        )
        # Handle the one-off auto-wrapping
        qtutils.connect_action_bool(self.autowrap_action, self.set_linebreak)

        self.summary.accepted.connect(self.focus_description)
        self.summary.down_pressed.connect(self.summary_cursor_down)

        self.model.commit_message_changed.connect(
            self.set_commit_message, type=Qt.QueuedConnection
        )
        self.commit_finished.connect(self._commit_finished, type=Qt.QueuedConnection)

        self.summary.cursor_changed.connect(self.cursor_changed.emit)
        self.description.cursor_changed.connect(
            # description starts at line 2
            lambda row, col: self.cursor_changed.emit(row + 2, col)
        )
        self.summary.textChanged.connect(self.commit_summary_changed)
        self.description.textChanged.connect(self._commit_message_changed)
        self.description.leave.connect(self.focus_summary)
        self.cursor_changed.connect(self.show_cursor_position)
        # Set initial position.
        self.show_cursor_position(1, 0)

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
        self.setFont(qtutils.diff_font(context))
        self.setFocusProxy(self.summary)

        cfg.user_config_changed.connect(self.config_changed)
        self.context.notifier.ready.connect(self._ready, type=Qt.QueuedConnection)

    def _ready(self):
        """Called when the app is ready for events"""
        self.context.runtask.run(self.spellcheck.init)

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

    def export_state(self, state):
        """Save persistent UI state on shutdown"""
        # Set a limit on the number of recent author values.
        max_recent = prefs.maxrecent(self.context)
        state['authors'] = self._commit_authors[:max_recent]
        return state

    def apply_state(self, state):
        """Apply persistent UI state on startup"""
        self._commit_authors = state.get('authors', [])
        return True

    def restore_size(self):
        self.setMaximumHeight(2**13)

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
        self.focus_description()

    def commit_message(self, raw=True):
        """Return the commit message as a Unicode string"""
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

    def commit_summary_changed(self):
        """Respond to changes to the `summary` field

        Newlines can enter the `summary` field when pasting, which is
        undesirable.  Break the pasted value apart into the separate
        (summary, description) values and move the description over to the
        "extended description" field.

        """
        value = self.summary.value()
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
        self.summary.cursor_position.emit()

    def _commit_message_changed(self, _value=None):
        """Update the model when values change"""
        message = self.commit_message()
        self.model.set_commitmsg(message, notify=False)
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
        # Store/restore the commit date and author when amending.
        if checked:
            self._last_commit_datetime_backup = self._last_commit_datetime
            self._last_commit_datetime = _get_latest_commit_datetime(self.context)
            self._git_commit_author_backup = self._git_commit_author
            self._git_commit_author = None
        else:
            self._last_commit_datetime = self._last_commit_datetime_backup
            self._last_commit_datetime_backup = None
            if self._git_commit_author_backup:
                self._git_commit_author = self._git_commit_author_backup
                self._git_commit_author_backup = None
                with qtutils.BlockSignals(self.commit_author_action):
                    self.commit_author_action.setChecked(True)

        self.update_author_and_date()

    def update_author_and_date(self):
        """Hide or display the author field"""
        amending = self.model.mode == self.model.mode_amend
        # Display the author when amending or when overridden.
        if self._git_commit_author:
            author = self._git_commit_author
        elif amending:
            author = self.model.commit_author
        else:
            author = None
        author_visible = bool(author)
        if author:
            self._author_label.setText(author)
        author_checked = self.commit_author_action.isChecked()
        self._author_close.setVisible(author_visible and author_checked)
        self._author_image.setVisible(author_visible)
        self._author_label.setVisible(author_visible)

        # Display the commit date when amending or when overridden.
        if self._git_commit_date:
            date = self._git_commit_date
        elif amending and self._last_commit_datetime:
            date = display.git_commit_date(self._last_commit_datetime)
        else:
            date = ''
        date_visible = bool(date)
        if date:
            self._date_label.setText(date)
        self._date_close.setVisible(bool(self._git_commit_date))
        self._date_image.setVisible(date_visible)
        self._date_label.setVisible(date_visible)

        if author_visible or date_visible:
            self.actions_button.setIcon(icons.gear_solid())
        else:
            self.actions_button.setIcon(icons.configure())

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
                    'Would you like to stage and commit all modified files?'
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
                    "You probably don't want to do this."
                ),
                N_('Amend the published commit?'),
                N_('Amend Commit'),
                default=False,
                icon=icons.save(),
            )
        ):
            return

        sign = get(self.sign_action)
        no_verify = get(self.bypass_commit_hooks_action)
        if self.commit_date_action.isChecked():
            date = self._git_commit_date
        else:
            date = None

        if self.commit_author_action.isChecked():
            author = self._git_commit_author
        else:
            author = None

        task = qtutils.SimpleTask(
            cmds.run(
                cmds.Commit,
                context,
                amend,
                msg,
                sign,
                no_verify=no_verify,
                author=author,
                date=date,
            )
        )
        self.context.runtask.start(
            task,
            finish=self.commit_finished.emit,
            progress=self.commit_progress_bar,
        )

    def _commit_finished(self, task):
        """Reset widget state on completion of the commit task"""
        title = N_('Commit failed')
        status, out, err = task.result
        Interaction.command(title, 'git commit', status, out, err)
        self.bypass_commit_hooks_action.setChecked(False)
        # Author and date settings are not cleared unless the commit operation succeeds.
        # These settings are consumed when a commit is produced with their values.
        if status == 0:
            self.set_commit_author(False, update=False)
            self.set_commit_date(False, update=True)
        self.setFocus()

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
        for idx, commit in enumerate(commits.get()):
            menu_commits.insert(0, commit)
            if idx > 5:
                continue

        menu.clear()
        for commit in menu_commits:
            menu.addAction(prefix + commit.summary, cmds.run(cmd, context, commit.oid))

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
        spell_check = self.spellcheck
        cfg = self.context.cfg

        if prefs.spellcheck(self.context) != enabled:
            cfg.set_user(prefs.SPELL_CHECK, enabled)
        if enabled and not self.spellcheck_initialized:
            # Add our name to the dictionary
            self.spellcheck_initialized = True
            user_name = cfg.get('user.name')
            if user_name:
                for part in user_name.split():
                    spell_check.add_word(part)

            # Add our email address to the dictionary
            user_email = cfg.get('user.email')
            if user_email:
                for part in user_email.split('@'):
                    for elt in part.split('.'):
                        spell_check.add_word(elt)

            # git jargon
            spell_check.add_word('Acked')
            spell_check.add_word('Signed')
            spell_check.add_word('Closes')
            spell_check.add_word('Fixes')

        self.summary.highlighter.enable(enabled)
        self.description.highlighter.enable(enabled)

    def show_cursor_position(self, rows, cols):
        """Display the cursor position with warnings and error colors for long lines"""
        display_content = '%02d:%02d' % (rows, cols)
        try:
            max_width = max(
                len(line) for line in self.commit_message(raw=False).splitlines()
            )
        except ValueError:
            max_width = 0
        if max_width > 78:
            color = 'red'
        elif max_width > 72:
            color = '#ff8833'
        elif max_width > 64:
            color = 'yellow'
        else:
            color = ''
        if color:
            radius = defs.small_icon // 2
            stylesheet = f"""
                color: black;
                background-color: {color};
                border-radius: {radius}px;
            """
        else:
            stylesheet = ''
        self.cursor_position_label.setStyleSheet(stylesheet)
        self.cursor_position_label.setText(display_content)

    def set_commit_date(self, enabled, update=True):
        """Choose the date and time that is used when authoring commits"""
        if not enabled:
            self._git_commit_date = None
            if self.commit_date_action.isChecked():
                with qtutils.BlockSignals(self.commit_date_action):
                    self.commit_date_action.setChecked(False)
            if update:
                self.update_author_and_date()
            return
        widget = CommitDateDialog(
            self, self.context, commit_datetime=self._last_commit_datetime
        )
        if widget.exec_() == QtWidgets.QDialog.Accepted:
            commit_date = widget.commit_date()
            Interaction.log(N_('Setting commit date to %s') % commit_date)
            self._git_commit_date = commit_date
            self._last_commit_datetime = CommitDateDialog.tick_time(widget.datetime())
        else:
            self.commit_date_action.setChecked(False)
        if update:
            self.update_author_and_date()

    def set_commit_author(self, enabled, update=True):
        """Choose a commit author to override the author value when authoring commits"""
        if not enabled:
            if self._git_commit_author:
                self._last_git_commit_author = self._git_commit_author
            self._git_commit_author = None
            if self.commit_author_action.isChecked():
                with qtutils.BlockSignals(self.commit_author_action):
                    self.commit_author_action.setChecked(False)
            if update:
                self.update_author_and_date()
            return
        widget = CommitAuthorDialog(
            self,
            self.context,
            commit_author=self._git_commit_author or self._last_git_commit_author,
            commit_authors=self._commit_authors,
        )
        if widget.exec_() == QtWidgets.QDialog.Accepted:
            commit_author = widget.commit_author()
            default_author = _get_default_author(self.context)
            Interaction.log(N_('Setting commit author to %s') % commit_author)
            self._git_commit_author = commit_author
            if (
                commit_author
                and commit_author != default_author
                and commit_author not in self._commit_authors
            ):
                self._commit_authors.insert(0, commit_author)
        else:
            self._git_commit_author = None
            self.commit_author_action.setChecked(False)
        if update:
            self.update_author_and_date()

    # Qt overrides
    def showEvent(self, event):
        """Resize the position label once the sizes are known"""
        super().showEvent(event)
        if not self._widgets_initialized:
            self._widgets_initialized = True
            height = self.summary.height()
            self.commit_button.setMinimumHeight(height)
            self.cursor_position_label.setMaximumHeight(defs.small_icon + defs.spacing)
            self.commit_progress_bar.setMaximumHeight(height - 2)
            self.commit_progress_bar.setMaximumWidth(self.commit_button.width())


def _get_latest_commit_datetime(context):
    """Query the commit time from Git or fallback to the current time when unavailable"""
    commit_datetime = datetime.datetime.now()
    status, out, _ = context.git.log('-1', '--format=%aI', 'HEAD')
    if status != 0 or not out:
        return commit_datetime
    try:
        commit_datetime = datetime.datetime.fromisoformat(out)
    except ValueError:
        pass
    return commit_datetime


class CommitDateDialog(QtWidgets.QDialog):
    """Choose the date and time used when authoring commits"""

    slider_range = 500

    def __init__(self, parent, context, commit_datetime=None):
        QtWidgets.QDialog.__init__(self, parent)
        slider_range = self.slider_range
        self.context = context
        self._calendar_widget = QtWidgets.QCalendarWidget()
        self._time_widget = QtWidgets.QTimeEdit()
        self._time_widget.setDisplayFormat('hh:mm:ss AP')

        # Horizontal slider moves the date and time backwards and forwards.
        self._slider = QtWidgets.QSlider(Qt.Horizontal)
        self._slider.setRange(0, slider_range)  # Mapped from 00:00:00 to 23:59:59

        self._tick_backward = qtutils.create_toolbutton_with_callback(
            partial(self._adjust_slider, -1),
            '-',
            None,
            N_('Decrement'),
            repeat=True,
        )
        self._tick_forward = qtutils.create_toolbutton_with_callback(
            partial(self._adjust_slider, 1),
            '+',
            None,
            N_('Increment'),
            repeat=True,
        )
        self._reset_to_commit_time = qtutils.create_toolbutton_with_callback(
            self._reset_time_to_latest_commit,
            None,
            icons.sync(),
            N_('Reset time to latest commit'),
        )
        self._reset_to_current_time = qtutils.create_toolbutton_with_callback(
            lambda: self._reset_time_to_datetime(datetime.datetime.now()),
            None,
            icons.style_dialog_reset(),
            N_('Reset time to current time'),
        )

        self._cancel_button = QtWidgets.QPushButton(N_('Cancel'))
        self._cancel_button.setIcon(icons.close())

        self._set_commit_time_button = QtWidgets.QPushButton(N_('Set Date and Time'))
        self._set_commit_time_button.setDefault(True)
        self._set_commit_time_button.setIcon(icons.ok())

        button_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self._cancel_button,
            qtutils.STRETCH,
            self._set_commit_time_button,
        )
        slider_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self._tick_backward,
            self._slider,
            self._tick_forward,
            self._reset_to_commit_time,
            self._reset_to_current_time,
            self._time_widget,
        )
        layout = qtutils.vbox(
            defs.small_margin,
            defs.spacing,
            self._calendar_widget,
            slider_layout,
            defs.button_spacing,
            button_layout,
        )
        self.setLayout(layout)
        self.setWindowTitle(N_('Set Commit Date'))
        self.setWindowModality(Qt.ApplicationModal)

        if commit_datetime is None:
            commit_datetime = self.tick_time(_get_latest_commit_datetime(context))
        self._time_widget.setTime(commit_datetime.time())
        self._calendar_widget.setSelectedDate(commit_datetime.date())
        self._update_slider_from_datetime(commit_datetime)

        self._right_action = qtutils.add_action(
            self, N_('Increment'), partial(self._adjust_slider, 1), hotkeys.CTRL_RIGHT
        )
        self._left_action = qtutils.add_action(
            self, N_('Decrement'), partial(self._adjust_slider, -1), hotkeys.CTRL_LEFT
        )

        self._time_widget.timeChanged.connect(self._update_slider_from_time_signal)
        self._slider.valueChanged.connect(self._update_time_from_slider)
        self._calendar_widget.activated.connect(lambda _: self.accept())

        self._cancel_button.clicked.connect(self.reject)
        self._set_commit_time_button.clicked.connect(self.accept)

    @classmethod
    def tick_time(cls, commit_datetime):
        """Tick time forward"""
        seconds_per_day = 86400
        seconds_range = seconds_per_day - 1
        one_tick = seconds_range // cls.slider_range  # 172 seconds (2m52s)
        return commit_datetime + datetime.timedelta(seconds=one_tick)

    def datetime(self):
        """Return the calculated datetime value"""
        # Combine the calendar widget's date with the time widget's time.
        time_value = self._time_widget.time().toPyTime()
        date_value = self._calendar_widget.selectedDate().toPyDate()
        date_time = datetime.datetime(
            date_value.year,
            date_value.month,
            date_value.day,
            time_value.hour,
            time_value.minute,
            time_value.second,
        )
        return date_time.astimezone()

    def commit_date(self):
        """Return the selected datetime as a string for use by Git"""
        return display.git_commit_date(self.datetime())

    def _update_time_from_slider(self, value):
        """Map the slider value to an offset corresponding to the current time.

        The passed-in value will be between 0 and range.
        """
        seconds_per_day = 86400
        seconds_range = seconds_per_day - 1
        ratio = value / self.slider_range
        delta = datetime.timedelta(seconds=int(ratio * seconds_range))
        midnight = datetime.datetime(1999, 12, 31)
        new_time = (midnight + delta).time()
        with qtutils.BlockSignals(self._time_widget):
            self._time_widget.setTime(new_time)

    def _adjust_slider(self, amount):
        """Adjust the slider forward or backwards"""
        new_value = self._slider.value() + amount
        self._slider.setValue(new_value)

    def _update_slider_from_time_signal(self, new_time):
        """Update the time slider to match the new time"""
        self._update_slider_from_time(new_time.toPyTime())

    def _update_slider_from_datetime(self, commit_datetime):
        """Update the time slider to match the specified datetime"""
        commit_time = commit_datetime.time()
        self._update_slider_from_time(commit_time)

    def _update_slider_from_time(self, commit_time):
        """Update the slider to match the specified time."""
        seconds_since_midnight = (
            60 * 60 * commit_time.hour + 60 * commit_time.minute + commit_time.second
        )
        seconds_per_day = 86400
        seconds_range = seconds_per_day - 1
        ratio = seconds_since_midnight / seconds_range
        value = int(self.slider_range * ratio)
        with qtutils.BlockSignals(self._slider):
            self._slider.setValue(value)

    def _reset_time_to_latest_commit(self):
        """Reset the commit time to match the most recent commit"""
        commit_datetime = _get_latest_commit_datetime(self.context)
        self._reset_time_to_datetime(commit_datetime)

    def _reset_time_to_datetime(self, commit_datetime):
        """Reset the commit time to match the specified datetime"""
        with qtutils.BlockSignals(self._time_widget):
            self._time_widget.setTime(commit_datetime.time())
        with qtutils.BlockSignals(self._calendar_widget):
            self._calendar_widget.setSelectedDate(commit_datetime.date())
        self._update_slider_from_datetime(commit_datetime)


def _get_default_author(context):
    """Get the default author value"""
    name, email = context.cfg.get_author()
    return f'{name} <{email}>'


def _get_latest_commit_author(context):
    """Query the commit author from Git"""
    status, out, _ = context.git.log('-1', '--format=%aN <%aE>', 'HEAD')
    if status != 0 or not out:
        return None
    return out


class CommitAuthorDialog(QtWidgets.QDialog):
    """Override the commit author when authoring commits"""

    def __init__(self, parent, context, commit_author=None, commit_authors=None):
        QtWidgets.QDialog.__init__(self, parent)
        main_tooltip = """Override the commit author.

Specify an explicit author using the standard "A U Thor <author@example.com>" format.

Otherwise <author> is assumed to be a pattern and is used to search for an
existing commit by that author (i.e. rev-list --all -i --author=<author>);"""
        self.context = context
        self._current_author = commit_author or _get_default_author(context)

        authors = self._get_authors(commit_author, commit_authors)
        tooltip = N_('Override the commit author when authoring commits')
        self._author_combobox = qtutils.combo(authors, editable=True, tooltip=tooltip)
        self._author_combobox.setToolTip(main_tooltip)
        if authors:
            self._author_combobox.set_value(authors[0])

        self._reset_to_commit_author_button = qtutils.create_toolbutton_with_callback(
            self._reset_to_commit_author,
            None,
            icons.sync(),
            N_('Set author to match the latest commit'),
        )
        self._reset_to_current_author_button = qtutils.create_toolbutton_with_callback(
            self._reset_to_current_author,
            None,
            icons.undo(),
            N_('Reset author to the current author'),
        )
        self._reset_to_default_author_button = qtutils.create_toolbutton_with_callback(
            self._reset_to_default_author,
            None,
            icons.style_dialog_reset(),
            N_('Reset to default author'),
        )

        self._cancel_button = QtWidgets.QPushButton(N_('Cancel'))
        self._cancel_button.setIcon(icons.close())

        self._apply_button = QtWidgets.QPushButton(N_('Set Author'))
        self._apply_button.setToolTip(main_tooltip)
        self._apply_button.setDefault(True)
        self._apply_button.setIcon(icons.ok())

        button_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self._cancel_button,
            qtutils.STRETCH,
            self._apply_button,
        )
        input_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self._author_combobox,
            self._reset_to_commit_author_button,
            self._reset_to_default_author_button,
            self._reset_to_current_author_button,
        )
        layout = qtutils.vbox(
            defs.small_margin,
            defs.spacing,
            input_layout,
            qtutils.STRETCH,
            defs.button_spacing,
            button_layout,
        )
        self.setLayout(layout)
        self.setWindowTitle(N_('Set Commit Author'))
        self.setWindowModality(Qt.ApplicationModal)

        self._apply_button.clicked.connect(self.accept)
        self._cancel_button.clicked.connect(self.reject)
        self._author_combobox.currentTextChanged.connect(lambda _: self._validate())
        self._validate()

    def commit_author(self):
        """Return the selected author value"""
        return self._author_combobox.current_value().strip()

    def _validate(self):
        """Validate the author value and disable the apply button when invalid"""
        author = self.commit_author()
        self._apply_button.setEnabled(bool(author))

    def _get_authors(self, commit_author, commit_authors):
        """Build a list of authors for the combo box"""
        seen = set()
        all_authors = [commit_author]
        if commit_authors:
            all_authors.extend(commit_authors)
        all_authors.append(_get_default_author(self.context))
        # Create a final unique list of authors.
        authors = []
        for author in all_authors:
            if author and author not in seen:
                seen.add(author)
                authors.append(author)
        return authors

    def _reset_to_commit_author(self):
        """Reset the author value to the author of the most recent commit"""
        commit_author = _get_latest_commit_author(self.context)
        if commit_author:
            self._author_combobox.set_current_value(commit_author)
        else:
            self._reset_to_default_author()  # Fallback to the current author.

    def _reset_to_current_author(self):
        """Reset the author value to the current author"""
        current_author = self._current_author
        if current_author:
            self._author_combobox.set_current_value(current_author)

    def _reset_to_default_author(self):
        """Reset the author value to the default author"""
        self._author_combobox.set_current_value(_get_default_author(self.context))


class CommitSummaryLineEdit(SpellCheckLineEdit):
    """Text input field for the commit summary"""

    down_pressed = Signal()
    accepted = Signal()

    def __init__(self, context, check=None, parent=None):
        hint = N_('Commit summary')
        SpellCheckLineEdit.__init__(self, context, hint, check=check, parent=parent)
        self._comment_char = None
        self._refresh_config()

        self.textChanged.connect(self._update_summary_text, Qt.QueuedConnection)
        context.cfg.updated.connect(self._refresh_config, type=Qt.QueuedConnection)

    def _refresh_config(self):
        """Update comment char in response to config changes"""
        self._comment_char = prefs.comment_char(self.context)

    def _update_summary_text(self):
        """Prevent commit messages from starting with comment characters"""
        value = self.get()
        if self._comment_char and value.lstrip().startswith(self._comment_char):
            cursor = self.textCursor()
            position = cursor.position()

            value = value.lstrip()
            if self._comment_char:
                value = value.lstrip(self._comment_char).lstrip()

            self.set_value(value, block=True)
            value = self.get()

            if position > 1:
                position = utils.clamp_zero(position - 1, len(value))
                cursor.setPosition(position)
                self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        """Allow "Enter" to focus into the extended description field"""
        event_key = event.key()
        if event_key in (
            Qt.Key_Enter,
            Qt.Key_Return,
        ):
            self.accepted.emit()
            return
        SpellCheckLineEdit.keyPressEvent(self, event)


class CommitMessageTextEdit(SpellCheckTextEdit):
    leave = Signal()

    def __init__(self, context, check=None, parent=None):
        hint = N_('Extended description...')
        SpellCheckTextEdit.__init__(self, context, hint, check=check, parent=parent)

        self.action_emit_leave = qtutils.add_action(
            self, 'Shift Tab', self.leave.emit, hotkeys.LEAVE
        )

    def keyPressEvent(self, event):
        """Update the cursor display and move the cursor to the end and beginning"""
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            position = cursor.position()
            if position == 0:
                # The cursor is at the beginning of the line.
                # If we have a selection and shift is not held then reset the
                # cursor to clear the selection. Otherwise, emit a signal so
                # that the parent can change focus.
                shifted = is_shift_pressed(event)
                if cursor.hasSelection() and not shifted:
                    self.set_cursor_position(0)
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
                mode = event_anchor_mode(event)
                cursor.movePosition(QtGui.QTextCursor.Up, mode)
                new_position = cursor.position()
                if position == new_position:
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
                mode = event_anchor_mode(event)
                cursor.movePosition(QtGui.QTextCursor.Down, mode)
                new_position = cursor.position()
                if position == new_position:
                    cursor.setPosition(len(all_text), mode)
                self.setTextCursor(cursor)
                event.accept()
                return
        SpellCheckTextEdit.keyPressEvent(self, event)

    def setFont(self, font):
        SpellCheckTextEdit.setFont(self, font)
        width, height = qtutils.text_size(font, 'MMMM')
        self.setMinimumSize(QtCore.QSize(width, height * 2))
