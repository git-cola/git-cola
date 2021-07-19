"""Editor commands"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import re
import sys
from fnmatch import fnmatch
from io import StringIO

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

from . import compat
from . import core
from . import gitcmds
from . import icons
from . import resources
from . import textwrap
from . import utils
from . import version
from .cmd import ContextCommand
from .diffparse import DiffParser
from .git import STDOUT
from .git import EMPTY_TREE_OID
from .git import MISSING_BLOB_OID
from .i18n import N_
from .interaction import Interaction
from .models import main
from .models import prefs


class UsageError(Exception):
    """Exception class for usage errors."""

    def __init__(self, title, message):
        Exception.__init__(self, message)
        self.title = title
        self.msg = message


class EditModel(ContextCommand):
    """Commands that mutate the main model diff data"""

    UNDOABLE = True

    def __init__(self, context):
        """Common edit operations on the main model"""
        super(EditModel, self).__init__(context)

        self.old_diff_text = self.model.diff_text
        self.old_filename = self.model.filename
        self.old_mode = self.model.mode
        self.old_diff_type = self.model.diff_type
        self.old_file_type = self.model.file_type

        self.new_diff_text = self.old_diff_text
        self.new_filename = self.old_filename
        self.new_mode = self.old_mode
        self.new_diff_type = self.old_diff_type
        self.new_file_type = self.old_file_type

    def do(self):
        """Perform the operation."""
        self.model.set_filename(self.new_filename)
        self.model.set_mode(self.new_mode)
        self.model.set_diff_text(self.new_diff_text)
        self.model.set_diff_type(self.new_diff_type)
        self.model.set_file_type(self.new_file_type)

    def undo(self):
        """Undo the operation."""
        self.model.set_filename(self.old_filename)
        self.model.set_mode(self.old_mode)
        self.model.set_diff_text(self.old_diff_text)
        self.model.set_diff_type(self.old_diff_type)
        self.model.set_file_type(self.old_file_type)


class ConfirmAction(ContextCommand):
    """Confirm an action before running it"""

    # pylint: disable=no-self-use
    def ok_to_run(self):
        """Return True when the command is ok to run"""
        return True

    # pylint: disable=no-self-use
    def confirm(self):
        """Prompt for confirmation"""
        return True

    # pylint: disable=no-self-use
    def action(self):
        """Run the command and return (status, out, err)"""
        return (-1, '', '')

    # pylint: disable=no-self-use
    def success(self):
        """Callback run on success"""
        return

    # pylint: disable=no-self-use
    def command(self):
        """Command name, for error messages"""
        return 'git'

    # pylint: disable=no-self-use
    def error_message(self):
        """Command error message"""
        return ''

    def do(self):
        """Prompt for confirmation before running a command"""
        status = -1
        out = err = ''
        ok = self.ok_to_run() and self.confirm()
        if ok:
            status, out, err = self.action()
            if status == 0:
                self.success()
            title = self.error_message()
            cmd = self.command()
            Interaction.command(title, cmd, status, out, err)

        return ok, status, out, err


class AbortMerge(ConfirmAction):
    """Reset an in-progress merge back to HEAD"""

    def confirm(self):
        title = N_('Abort Merge...')
        question = N_('Aborting the current merge?')
        info = N_(
            'Aborting the current merge will cause '
            '*ALL* uncommitted changes to be lost.\n'
            'Recovering uncommitted changes is not possible.'
        )
        ok_txt = N_('Abort Merge')
        return Interaction.confirm(
            title, question, info, ok_txt, default=False, icon=icons.undo()
        )

    def action(self):
        status, out, err = gitcmds.abort_merge(self.context)
        self.model.update_file_status()
        return status, out, err

    def success(self):
        self.model.set_commitmsg('')

    def error_message(self):
        return N_('Error')

    def command(self):
        return 'git merge'


class AmendMode(EditModel):
    """Try to amend a commit."""

    UNDOABLE = True
    LAST_MESSAGE = None

    @staticmethod
    def name():
        return N_('Amend')

    def __init__(self, context, amend=True):
        super(AmendMode, self).__init__(context)
        self.skip = False
        self.amending = amend
        self.old_commitmsg = self.model.commitmsg
        self.old_mode = self.model.mode

        if self.amending:
            self.new_mode = self.model.mode_amend
            self.new_commitmsg = gitcmds.prev_commitmsg(context)
            AmendMode.LAST_MESSAGE = self.model.commitmsg
            return
        # else, amend unchecked, regular commit
        self.new_mode = self.model.mode_none
        self.new_diff_text = ''
        self.new_commitmsg = self.model.commitmsg
        # If we're going back into new-commit-mode then search the
        # undo stack for a previous amend-commit-mode and grab the
        # commit message at that point in time.
        if AmendMode.LAST_MESSAGE is not None:
            self.new_commitmsg = AmendMode.LAST_MESSAGE
            AmendMode.LAST_MESSAGE = None

    def do(self):
        """Leave/enter amend mode."""
        # Attempt to enter amend mode.  Do not allow this when merging.
        if self.amending:
            if self.model.is_merging:
                self.skip = True
                self.model.set_mode(self.old_mode)
                Interaction.information(
                    N_('Cannot Amend'),
                    N_(
                        'You are in the middle of a merge.\n'
                        'Cannot amend while merging.'
                    ),
                )
                return
        self.skip = False
        super(AmendMode, self).do()
        self.model.set_commitmsg(self.new_commitmsg)
        self.model.update_file_status()

    def undo(self):
        if self.skip:
            return
        self.model.set_commitmsg(self.old_commitmsg)
        super(AmendMode, self).undo()
        self.model.update_file_status()


class AnnexAdd(ContextCommand):
    """Add to Git Annex"""

    def __init__(self, context):
        super(AnnexAdd, self).__init__(context)
        self.filename = self.selection.filename()

    def do(self):
        status, out, err = self.git.annex('add', self.filename)
        Interaction.command(N_('Error'), 'git annex add', status, out, err)
        self.model.update_status()


class AnnexInit(ContextCommand):
    """Initialize Git Annex"""

    def do(self):
        status, out, err = self.git.annex('init')
        Interaction.command(N_('Error'), 'git annex init', status, out, err)
        self.model.cfg.reset()
        self.model.emit_updated()


class LFSTrack(ContextCommand):
    """Add a file to git lfs"""

    def __init__(self, context):
        super(LFSTrack, self).__init__(context)
        self.filename = self.selection.filename()
        self.stage_cmd = Stage(context, [self.filename])

    def do(self):
        status, out, err = self.git.lfs('track', self.filename)
        Interaction.command(N_('Error'), 'git lfs track', status, out, err)
        if status == 0:
            self.stage_cmd.do()


class LFSInstall(ContextCommand):
    """Initialize git lfs"""

    def do(self):
        status, out, err = self.git.lfs('install')
        Interaction.command(N_('Error'), 'git lfs install', status, out, err)
        self.model.update_config(reset=True, emit=True)


class ApplyDiffSelection(ContextCommand):
    """Apply the selected diff to the worktree or index"""

    def __init__(
        self,
        context,
        first_line_idx,
        last_line_idx,
        has_selection,
        reverse,
        apply_to_worktree,
    ):
        super(ApplyDiffSelection, self).__init__(context)
        self.first_line_idx = first_line_idx
        self.last_line_idx = last_line_idx
        self.has_selection = has_selection
        self.reverse = reverse
        self.apply_to_worktree = apply_to_worktree

    def do(self):
        context = self.context
        cfg = self.context.cfg
        diff_text = self.model.diff_text

        parser = DiffParser(self.model.filename, diff_text)
        if self.has_selection:
            patch = parser.generate_patch(
                self.first_line_idx, self.last_line_idx, reverse=self.reverse
            )
        else:
            patch = parser.generate_hunk_patch(
                self.first_line_idx, reverse=self.reverse
            )
        if patch is None:
            return

        if isinstance(diff_text, core.UStr):
            # original encoding must prevail
            encoding = diff_text.encoding
        else:
            encoding = cfg.file_encoding(self.model.filename)

        tmp_file = utils.tmp_filename('patch')
        try:
            core.write(tmp_file, patch, encoding=encoding)
            if self.apply_to_worktree:
                status, out, err = gitcmds.apply_diff_to_worktree(context, tmp_file)
            else:
                status, out, err = gitcmds.apply_diff(context, tmp_file)
        finally:
            core.unlink(tmp_file)

        Interaction.log_status(status, out, err)
        self.model.update_file_status(update_index=True)


class ApplyPatches(ContextCommand):
    """Apply patches using the "git am" command"""

    def __init__(self, context, patches):
        super(ApplyPatches, self).__init__(context)
        self.patches = patches

    def do(self):
        status, out, err = self.git.am('-3', *self.patches)
        Interaction.log_status(status, out, err)

        # Display a diffstat
        self.model.update_file_status()

        patch_basenames = [os.path.basename(p) for p in self.patches]
        if len(patch_basenames) > 25:
            patch_basenames = patch_basenames[:25]
            patch_basenames.append('...')

        basenames = '\n'.join(patch_basenames)
        Interaction.information(
            N_('Patch(es) Applied'),
            (N_('%d patch(es) applied.') + '\n\n%s') % (len(self.patches), basenames),
        )


class Archive(ContextCommand):
    """"Export archives using the "git archive" command"""

    def __init__(self, context, ref, fmt, prefix, filename):
        super(Archive, self).__init__(context)
        self.ref = ref
        self.fmt = fmt
        self.prefix = prefix
        self.filename = filename

    def do(self):
        fp = core.xopen(self.filename, 'wb')
        cmd = ['git', 'archive', '--format=' + self.fmt]
        if self.fmt in ('tgz', 'tar.gz'):
            cmd.append('-9')
        if self.prefix:
            cmd.append('--prefix=' + self.prefix)
        cmd.append(self.ref)
        proc = core.start_command(cmd, stdout=fp)
        out, err = proc.communicate()
        fp.close()
        status = proc.returncode
        Interaction.log_status(status, out or '', err or '')


class Checkout(EditModel):
    """A command object for git-checkout.

    'argv' is handed off directly to git.

    """

    def __init__(self, context, argv, checkout_branch=False):
        super(Checkout, self).__init__(context)
        self.argv = argv
        self.checkout_branch = checkout_branch
        self.new_diff_text = ''
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT

    def do(self):
        super(Checkout, self).do()
        status, out, err = self.git.checkout(*self.argv)
        if self.checkout_branch:
            self.model.update_status()
        else:
            self.model.update_file_status()
        Interaction.command(N_('Error'), 'git checkout', status, out, err)


class BlamePaths(ContextCommand):
    """Blame view for paths."""

    @staticmethod
    def name():
        return N_('Blame...')

    def __init__(self, context, paths=None):
        super(BlamePaths, self).__init__(context)
        if not paths:
            paths = context.selection.union()
        viewer = utils.shell_split(prefs.blame_viewer(context))
        self.argv = viewer + list(paths)

    def do(self):
        try:
            core.fork(self.argv)
        except OSError as e:
            _, details = utils.format_exception(e)
            title = N_('Error Launching Blame Viewer')
            msg = N_('Cannot exec "%s": please configure a blame viewer') % ' '.join(
                self.argv
            )
            Interaction.critical(title, message=msg, details=details)


class CheckoutBranch(Checkout):
    """Checkout a branch."""

    def __init__(self, context, branch):
        args = [branch]
        super(CheckoutBranch, self).__init__(context, args, checkout_branch=True)


class CherryPick(ContextCommand):
    """Cherry pick commits into the current branch."""

    def __init__(self, context, commits):
        super(CherryPick, self).__init__(context)
        self.commits = commits

    def do(self):
        self.model.cherry_pick_list(self.commits)
        self.model.update_file_status()


class Revert(ContextCommand):
    """Cherry pick commits into the current branch."""

    def __init__(self, context, oid):
        super(Revert, self).__init__(context)
        self.oid = oid

    def do(self):
        self.git.revert(self.oid, no_edit=True)
        self.model.update_file_status()


class ResetMode(EditModel):
    """Reset the mode and clear the model's diff text."""

    def __init__(self, context):
        super(ResetMode, self).__init__(context)
        self.new_mode = self.model.mode_none
        self.new_diff_text = ''
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT
        self.new_filename = ''

    def do(self):
        super(ResetMode, self).do()
        self.model.update_file_status()


class ResetCommand(ConfirmAction):
    """Reset state using the "git reset" command"""

    def __init__(self, context, ref):
        super(ResetCommand, self).__init__(context)
        self.ref = ref

    def action(self):
        return self.reset()

    def command(self):
        return 'git reset'

    def error_message(self):
        return N_('Error')

    def success(self):
        self.model.update_file_status()

    def confirm(self):
        raise NotImplementedError('confirm() must be overridden')

    def reset(self):
        raise NotImplementedError('reset() must be overridden')


class ResetMixed(ResetCommand):
    @staticmethod
    def tooltip(ref):
        tooltip = N_('The branch will be reset using "git reset --mixed %s"')
        return tooltip % ref

    def confirm(self):
        title = N_('Reset Branch and Stage (Mixed)')
        question = N_('Point the current branch head to a new commit?')
        info = self.tooltip(self.ref)
        ok_text = N_('Reset Branch')
        return Interaction.confirm(title, question, info, ok_text)

    def reset(self):
        return self.git.reset(self.ref, '--', mixed=True)


class ResetKeep(ResetCommand):
    @staticmethod
    def tooltip(ref):
        tooltip = N_('The repository will be reset using "git reset --keep %s"')
        return tooltip % ref

    def confirm(self):
        title = N_('Restore Worktree and Reset All (Keep Unstaged Changes)')
        question = N_('Restore worktree, reset, and preserve unstaged edits?')
        info = self.tooltip(self.ref)
        ok_text = N_('Reset and Restore')
        return Interaction.confirm(title, question, info, ok_text)

    def reset(self):
        return self.git.reset(self.ref, '--', keep=True)


class ResetMerge(ResetCommand):
    @staticmethod
    def tooltip(ref):
        tooltip = N_('The repository will be reset using "git reset --merge %s"')
        return tooltip % ref

    def confirm(self):
        title = N_('Restore Worktree and Reset All (Merge)')
        question = N_('Reset Worktree and Reset All?')
        info = self.tooltip(self.ref)
        ok_text = N_('Reset and Restore')
        return Interaction.confirm(title, question, info, ok_text)

    def reset(self):
        return self.git.reset(self.ref, '--', merge=True)


class ResetSoft(ResetCommand):
    @staticmethod
    def tooltip(ref):
        tooltip = N_('The branch will be reset using "git reset --soft %s"')
        return tooltip % ref

    def confirm(self):
        title = N_('Reset Branch (Soft)')
        question = N_('Reset branch?')
        info = self.tooltip(self.ref)
        ok_text = N_('Reset Branch')
        return Interaction.confirm(title, question, info, ok_text)

    def reset(self):
        return self.git.reset(self.ref, '--', soft=True)


class ResetHard(ResetCommand):
    @staticmethod
    def tooltip(ref):
        tooltip = N_('The repository will be reset using "git reset --hard %s"')
        return tooltip % ref

    def confirm(self):
        title = N_('Restore Worktree and Reset All (Hard)')
        question = N_('Restore Worktree and Reset All?')
        info = self.tooltip(self.ref)
        ok_text = N_('Reset and Restore')
        return Interaction.confirm(title, question, info, ok_text)

    def reset(self):
        return self.git.reset(self.ref, '--', hard=True)


class RestoreWorktree(ConfirmAction):
    """Reset the worktree using the "git read-tree" command"""

    @staticmethod
    def tooltip(ref):
        tooltip = N_(
            'The worktree will be restored using "git read-tree --reset -u %s"'
        )
        return tooltip % ref

    def __init__(self, context, ref):
        super(RestoreWorktree, self).__init__(context)
        self.ref = ref

    def action(self):
        return self.git.read_tree(self.ref, reset=True, u=True)

    def command(self):
        return 'git read-tree --reset -u %s' % self.ref

    def error_message(self):
        return N_('Error')

    def success(self):
        self.model.update_file_status()

    def confirm(self):
        title = N_('Restore Worktree')
        question = N_('Restore Worktree to %s?') % self.ref
        info = self.tooltip(self.ref)
        ok_text = N_('Restore Worktree')
        return Interaction.confirm(title, question, info, ok_text)


class UndoLastCommit(ResetCommand):
    """Undo the last commit"""

    # NOTE: this is the similar to ResetSoft() with an additional check for
    # published commits and different messages.
    def __init__(self, context):
        super(UndoLastCommit, self).__init__(context, 'HEAD^')

    def confirm(self):
        check_published = prefs.check_published_commits(self.context)
        if check_published and self.model.is_commit_published():
            return Interaction.confirm(
                N_('Rewrite Published Commit?'),
                N_(
                    'This commit has already been published.\n'
                    'This operation will rewrite published history.\n'
                    'You probably don\'t want to do this.'
                ),
                N_('Undo the published commit?'),
                N_('Undo Last Commit'),
                default=False,
                icon=icons.save(),
            )

        title = N_('Undo Last Commit')
        question = N_('Undo last commit?')
        info = N_('The branch will be reset using "git reset --soft %s"')
        ok_text = N_('Undo Last Commit')
        info_text = info % self.ref
        return Interaction.confirm(title, question, info_text, ok_text)

    def reset(self):
        return self.git.reset('HEAD^', '--', soft=True)


class Commit(ResetMode):
    """Attempt to create a new commit."""

    def __init__(self, context, amend, msg, sign, no_verify=False):
        super(Commit, self).__init__(context)
        self.amend = amend
        self.msg = msg
        self.sign = sign
        self.no_verify = no_verify
        self.old_commitmsg = self.model.commitmsg
        self.new_commitmsg = ''

    def do(self):
        # Create the commit message file
        context = self.context
        comment_char = prefs.comment_char(context)
        msg = self.strip_comments(self.msg, comment_char=comment_char)
        tmp_file = utils.tmp_filename('commit-message')
        try:
            core.write(tmp_file, msg)
            # Run 'git commit'
            status, out, err = self.git.commit(
                F=tmp_file,
                v=True,
                gpg_sign=self.sign,
                amend=self.amend,
                no_verify=self.no_verify,
            )
        finally:
            core.unlink(tmp_file)
        if status == 0:
            super(Commit, self).do()
            if context.cfg.get(prefs.AUTOTEMPLATE):
                template_loader = LoadCommitMessageFromTemplate(context)
                template_loader.do()
            else:
                self.model.set_commitmsg(self.new_commitmsg)

        title = N_('Commit failed')
        Interaction.command(title, 'git commit', status, out, err)

        return status, out, err

    @staticmethod
    def strip_comments(msg, comment_char='#'):
        # Strip off comments
        message_lines = [
            line for line in msg.split('\n') if not line.startswith(comment_char)
        ]
        msg = '\n'.join(message_lines)
        if not msg.endswith('\n'):
            msg += '\n'

        return msg


class CycleReferenceSort(ContextCommand):
    """Choose the next reference sort type"""

    def do(self):
        self.model.cycle_ref_sort()


class Ignore(ContextCommand):
    """Add files to an exclusion file"""

    def __init__(self, context, filenames, local=False):
        super(Ignore, self).__init__(context)
        self.filenames = list(filenames)
        self.local = local

    def do(self):
        if not self.filenames:
            return
        new_additions = '\n'.join(self.filenames) + '\n'
        for_status = new_additions
        if self.local:
            filename = os.path.join('.git', 'info', 'exclude')
        else:
            filename = '.gitignore'
        if core.exists(filename):
            current_list = core.read(filename)
            new_additions = current_list.rstrip() + '\n' + new_additions
        core.write(filename, new_additions)
        Interaction.log_status(0, 'Added to %s:\n%s' % (filename, for_status), '')
        self.model.update_file_status()


def file_summary(files):
    txt = core.list2cmdline(files)
    if len(txt) > 768:
        txt = txt[:768].rstrip() + '...'
    wrap = textwrap.TextWrapper()
    return '\n'.join(wrap.wrap(txt))


class RemoteCommand(ConfirmAction):
    def __init__(self, context, remote):
        super(RemoteCommand, self).__init__(context)
        self.remote = remote

    def success(self):
        self.cfg.reset()
        self.model.update_remotes()


class RemoteAdd(RemoteCommand):
    def __init__(self, context, remote, url):
        super(RemoteAdd, self).__init__(context, remote)
        self.url = url

    def action(self):
        return self.git.remote('add', self.remote, self.url)

    def error_message(self):
        return N_('Error creating remote "%s"') % self.remote

    def command(self):
        return 'git remote add "%s" "%s"' % (self.remote, self.url)


class RemoteRemove(RemoteCommand):
    def confirm(self):
        title = N_('Delete Remote')
        question = N_('Delete remote?')
        info = N_('Delete remote "%s"') % self.remote
        ok_text = N_('Delete')
        return Interaction.confirm(title, question, info, ok_text)

    def action(self):
        return self.git.remote('rm', self.remote)

    def error_message(self):
        return N_('Error deleting remote "%s"') % self.remote

    def command(self):
        return 'git remote rm "%s"' % self.remote


class RemoteRename(RemoteCommand):
    def __init__(self, context, remote, new_name):
        super(RemoteRename, self).__init__(context, remote)
        self.new_name = new_name

    def confirm(self):
        title = N_('Rename Remote')
        text = N_('Rename remote "%(current)s" to "%(new)s"?') % dict(
            current=self.remote, new=self.new_name
        )
        info_text = ''
        ok_text = title
        return Interaction.confirm(title, text, info_text, ok_text)

    def action(self):
        return self.git.remote('rename', self.remote, self.new_name)

    def error_message(self):
        return N_('Error renaming "%(name)s" to "%(new_name)s"') % dict(
            name=self.remote, new_name=self.new_name
        )

    def command(self):
        return 'git remote rename "%s" "%s"' % (self.remote, self.new_name)


class RemoteSetURL(RemoteCommand):
    def __init__(self, context, remote, url):
        super(RemoteSetURL, self).__init__(context, remote)
        self.url = url

    def action(self):
        return self.git.remote('set-url', self.remote, self.url)

    def error_message(self):
        return N_('Unable to set URL for "%(name)s" to "%(url)s"') % dict(
            name=self.remote, url=self.url
        )

    def command(self):
        return 'git remote set-url "%s" "%s"' % (self.remote, self.url)


class RemoteEdit(ContextCommand):
    """Combine RemoteRename and RemoteSetURL"""

    def __init__(self, context, old_name, remote, url):
        super(RemoteEdit, self).__init__(context)
        self.rename = RemoteRename(context, old_name, remote)
        self.set_url = RemoteSetURL(context, remote, url)

    def do(self):
        result = self.rename.do()
        name_ok = result[0]
        url_ok = False
        if name_ok:
            result = self.set_url.do()
            url_ok = result[0]
        return name_ok, url_ok


class RemoveFromSettings(ConfirmAction):
    def __init__(self, context, repo, entry, icon=None):
        super(RemoveFromSettings, self).__init__(context)
        self.context = context
        self.repo = repo
        self.entry = entry
        self.icon = icon

    def success(self):
        self.context.settings.save()


class RemoveBookmark(RemoveFromSettings):
    def confirm(self):
        entry = self.entry
        title = msg = N_('Delete Bookmark?')
        info = N_('%s will be removed from your bookmarks.') % entry
        ok_text = N_('Delete Bookmark')
        return Interaction.confirm(title, msg, info, ok_text, icon=self.icon)

    def action(self):
        self.context.settings.remove_bookmark(self.repo, self.entry)
        return (0, '', '')


class RemoveRecent(RemoveFromSettings):
    def confirm(self):
        repo = self.repo
        title = msg = N_('Remove %s from the recent list?') % repo
        info = N_('%s will be removed from your recent repositories.') % repo
        ok_text = N_('Remove')
        return Interaction.confirm(title, msg, info, ok_text, icon=self.icon)

    def action(self):
        self.context.settings.remove_recent(self.repo)
        return (0, '', '')


class RemoveFiles(ContextCommand):
    """Removes files"""

    def __init__(self, context, remover, filenames):
        super(RemoveFiles, self).__init__(context)
        if remover is None:
            remover = os.remove
        self.remover = remover
        self.filenames = filenames
        # We could git-hash-object stuff and provide undo-ability
        # as an option.  Heh.

    def do(self):
        files = self.filenames
        if not files:
            return

        rescan = False
        bad_filenames = []
        remove = self.remover
        for filename in files:
            if filename:
                try:
                    remove(filename)
                    rescan = True
                except OSError:
                    bad_filenames.append(filename)

        if bad_filenames:
            Interaction.information(
                N_('Error'), N_('Deleting "%s" failed') % file_summary(bad_filenames)
            )

        if rescan:
            self.model.update_file_status()


class Delete(RemoveFiles):
    """Delete files."""

    def __init__(self, context, filenames):
        super(Delete, self).__init__(context, os.remove, filenames)

    def do(self):
        files = self.filenames
        if not files:
            return

        title = N_('Delete Files?')
        msg = N_('The following files will be deleted:') + '\n\n'
        msg += file_summary(files)
        info_txt = N_('Delete %d file(s)?') % len(files)
        ok_txt = N_('Delete Files')

        if Interaction.confirm(
            title, msg, info_txt, ok_txt, default=True, icon=icons.remove()
        ):
            super(Delete, self).do()


class MoveToTrash(RemoveFiles):
    """Move files to the trash using send2trash"""

    AVAILABLE = send2trash is not None

    def __init__(self, context, filenames):
        super(MoveToTrash, self).__init__(context, send2trash, filenames)


class DeleteBranch(ConfirmAction):
    """Delete a git branch."""

    def __init__(self, context, branch):
        super(DeleteBranch, self).__init__(context)
        self.branch = branch

    def confirm(self):
        title = N_('Delete Branch')
        question = N_('Delete branch "%s"?') % self.branch
        info = N_('The branch will be no longer available.')
        ok_txt = N_('Delete Branch')
        return Interaction.confirm(
            title, question, info, ok_txt, default=True, icon=icons.discard()
        )

    def action(self):
        return self.model.delete_branch(self.branch)

    def error_message(self):
        return N_('Error deleting branch "%s"' % self.branch)

    def command(self):
        command = 'git branch -D %s'
        return command % self.branch


class Rename(ContextCommand):
    """Rename a set of paths."""

    def __init__(self, context, paths):
        super(Rename, self).__init__(context)
        self.paths = paths

    def do(self):
        msg = N_('Untracking: %s') % (', '.join(self.paths))
        Interaction.log(msg)

        for path in self.paths:
            ok = self.rename(path)
            if not ok:
                return

        self.model.update_status()

    def rename(self, path):
        git = self.git
        title = N_('Rename "%s"') % path

        if os.path.isdir(path):
            base_path = os.path.dirname(path)
        else:
            base_path = path
        new_path = Interaction.save_as(base_path, title)
        if not new_path:
            return False

        status, out, err = git.mv(path, new_path, force=True, verbose=True)
        Interaction.command(N_('Error'), 'git mv', status, out, err)
        return status == 0


class RenameBranch(ContextCommand):
    """Rename a git branch."""

    def __init__(self, context, branch, new_branch):
        super(RenameBranch, self).__init__(context)
        self.branch = branch
        self.new_branch = new_branch

    def do(self):
        branch = self.branch
        new_branch = self.new_branch
        status, out, err = self.model.rename_branch(branch, new_branch)
        Interaction.log_status(status, out, err)


class DeleteRemoteBranch(DeleteBranch):
    """Delete a remote git branch."""

    def __init__(self, context, remote, branch):
        super(DeleteRemoteBranch, self).__init__(context, branch)
        self.remote = remote

    def action(self):
        return self.git.push(self.remote, self.branch, delete=True)

    def success(self):
        self.model.update_status()
        Interaction.information(
            N_('Remote Branch Deleted'),
            N_('"%(branch)s" has been deleted from "%(remote)s".')
            % dict(branch=self.branch, remote=self.remote),
        )

    def error_message(self):
        return N_('Error Deleting Remote Branch')

    def command(self):
        command = 'git push --delete %s %s'
        return command % (self.remote, self.branch)


def get_mode(model, staged, modified, unmerged, untracked):
    if staged:
        mode = model.mode_index
    elif modified or unmerged:
        mode = model.mode_worktree
    elif untracked:
        mode = model.mode_untracked
    else:
        mode = model.mode
    return mode


class DiffText(EditModel):
    """Set the diff type to text"""

    def __init__(self, context):
        super(DiffText, self).__init__(context)
        self.new_file_type = main.Types.TEXT
        self.new_diff_type = main.Types.TEXT


class ToggleDiffType(ContextCommand):
    """Toggle the diff type between image and text"""

    def __init__(self, context):
        super(ToggleDiffType, self).__init__(context)
        if self.model.diff_type == main.Types.IMAGE:
            self.new_diff_type = main.Types.TEXT
            self.new_value = False
        else:
            self.new_diff_type = main.Types.IMAGE
            self.new_value = True

    def do(self):
        diff_type = self.new_diff_type
        value = self.new_value

        self.model.set_diff_type(diff_type)

        filename = self.model.filename
        _, ext = os.path.splitext(filename)
        if ext.startswith('.'):
            cfg = 'cola.imagediff' + ext
            self.cfg.set_repo(cfg, value)


class DiffImage(EditModel):
    def __init__(
        self, context, filename, deleted, staged, modified, unmerged, untracked
    ):
        super(DiffImage, self).__init__(context)

        self.new_filename = filename
        self.new_diff_type = self.get_diff_type(filename)
        self.new_file_type = main.Types.IMAGE
        self.new_mode = get_mode(self.model, staged, modified, unmerged, untracked)
        self.staged = staged
        self.modified = modified
        self.unmerged = unmerged
        self.untracked = untracked
        self.deleted = deleted
        self.annex = self.cfg.is_annex()

    def get_diff_type(self, filename):
        """Query the diff type to use based on cola.imagediff.<extension>"""
        _, ext = os.path.splitext(filename)
        if ext.startswith('.'):
            # Check eg. "cola.imagediff.svg" to see if we should imagediff.
            cfg = 'cola.imagediff' + ext
            if self.cfg.get(cfg, True):
                result = main.Types.IMAGE
            else:
                result = main.Types.TEXT
        else:
            result = main.Types.IMAGE
        return result

    def do(self):
        filename = self.new_filename

        if self.staged:
            images = self.staged_images()
        elif self.modified:
            images = self.modified_images()
        elif self.unmerged:
            images = self.unmerged_images()
        elif self.untracked:
            images = [(filename, False)]
        else:
            images = []

        self.model.set_images(images)
        super(DiffImage, self).do()

    def staged_images(self):
        context = self.context
        git = self.git
        head = self.model.head
        filename = self.new_filename
        annex = self.annex

        images = []
        index = git.diff_index(head, '--', filename, cached=True)[STDOUT]
        if index:
            # Example:
            #  :100644 100644 fabadb8... 4866510... M      describe.c
            parts = index.split(' ')
            if len(parts) > 3:
                old_oid = parts[2]
                new_oid = parts[3]

            if old_oid != MISSING_BLOB_OID:
                # First, check if we can get a pre-image from git-annex
                annex_image = None
                if annex:
                    annex_image = gitcmds.annex_path(context, head, filename)
                if annex_image:
                    images.append((annex_image, False))  # git annex HEAD
                else:
                    image = gitcmds.write_blob_path(context, head, old_oid, filename)
                    if image:
                        images.append((image, True))

            if new_oid != MISSING_BLOB_OID:
                found_in_annex = False
                if annex and core.islink(filename):
                    status, out, _ = git.annex('status', '--', filename)
                    if status == 0:
                        details = out.split(' ')
                        if details and details[0] == 'A':  # newly added file
                            images.append((filename, False))
                            found_in_annex = True

                if not found_in_annex:
                    image = gitcmds.write_blob(context, new_oid, filename)
                    if image:
                        images.append((image, True))

        return images

    def unmerged_images(self):
        context = self.context
        git = self.git
        head = self.model.head
        filename = self.new_filename
        annex = self.annex

        candidate_merge_heads = ('HEAD', 'CHERRY_HEAD', 'MERGE_HEAD')
        merge_heads = [
            merge_head
            for merge_head in candidate_merge_heads
            if core.exists(git.git_path(merge_head))
        ]

        if annex:  # Attempt to find files in git-annex
            annex_images = []
            for merge_head in merge_heads:
                image = gitcmds.annex_path(context, merge_head, filename)
                if image:
                    annex_images.append((image, False))
            if annex_images:
                annex_images.append((filename, False))
                return annex_images

        # DIFF FORMAT FOR MERGES
        # "git-diff-tree", "git-diff-files" and "git-diff --raw"
        # can take -c or --cc option to generate diff output also
        # for merge commits. The output differs from the format
        # described above in the following way:
        #
        #  1. there is a colon for each parent
        #  2. there are more "src" modes and "src" sha1
        #  3. status is concatenated status characters for each parent
        #  4. no optional "score" number
        #  5. single path, only for "dst"
        # Example:
        #  ::100644 100644 100644 fabadb8... cc95eb0... 4866510... \
        #  MM      describe.c
        images = []
        index = git.diff_index(head, '--', filename, cached=True, cc=True)[STDOUT]
        if index:
            parts = index.split(' ')
            if len(parts) > 3:
                first_mode = parts[0]
                num_parents = first_mode.count(':')
                # colon for each parent, but for the index, the "parents"
                # are really entries in stages 1,2,3 (head, base, remote)
                # remote, base, head
                for i in range(num_parents):
                    offset = num_parents + i + 1
                    oid = parts[offset]
                    try:
                        merge_head = merge_heads[i]
                    except IndexError:
                        merge_head = 'HEAD'
                    if oid != MISSING_BLOB_OID:
                        image = gitcmds.write_blob_path(
                            context, merge_head, oid, filename
                        )
                        if image:
                            images.append((image, True))

        images.append((filename, False))
        return images

    def modified_images(self):
        context = self.context
        git = self.git
        head = self.model.head
        filename = self.new_filename
        annex = self.annex

        images = []
        annex_image = None
        if annex:  # Check for a pre-image from git-annex
            annex_image = gitcmds.annex_path(context, head, filename)
        if annex_image:
            images.append((annex_image, False))  # git annex HEAD
        else:
            worktree = git.diff_files('--', filename)[STDOUT]
            parts = worktree.split(' ')
            if len(parts) > 3:
                oid = parts[2]
                if oid != MISSING_BLOB_OID:
                    image = gitcmds.write_blob_path(context, head, oid, filename)
                    if image:
                        images.append((image, True))  # HEAD

        images.append((filename, False))  # worktree
        return images


class Diff(EditModel):
    """Perform a diff and set the model's current text."""

    def __init__(self, context, filename, cached=False, deleted=False):
        super(Diff, self).__init__(context)
        opts = {}
        if cached and gitcmds.is_valid_ref(context, self.model.head):
            opts['ref'] = self.model.head
        self.new_filename = filename
        self.new_mode = self.model.mode_worktree
        self.new_diff_text = gitcmds.diff_helper(
            self.context, filename=filename, cached=cached, deleted=deleted, **opts
        )


class Diffstat(EditModel):
    """Perform a diffstat and set the model's diff text."""

    def __init__(self, context):
        super(Diffstat, self).__init__(context)
        cfg = self.cfg
        diff_context = cfg.get('diff.context', 3)
        diff = self.git.diff(
            self.model.head,
            unified=diff_context,
            no_ext_diff=True,
            no_color=True,
            M=True,
            stat=True,
        )[STDOUT]
        self.new_diff_text = diff
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT
        self.new_mode = self.model.mode_diffstat


class DiffStaged(Diff):
    """Perform a staged diff on a file."""

    def __init__(self, context, filename, deleted=None):
        super(DiffStaged, self).__init__(
            context, filename, cached=True, deleted=deleted
        )
        self.new_mode = self.model.mode_index


class DiffStagedSummary(EditModel):
    def __init__(self, context):
        super(DiffStagedSummary, self).__init__(context)
        diff = self.git.diff(
            self.model.head,
            cached=True,
            no_color=True,
            no_ext_diff=True,
            patch_with_stat=True,
            M=True,
        )[STDOUT]
        self.new_diff_text = diff
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT
        self.new_mode = self.model.mode_index


class Difftool(ContextCommand):
    """Run git-difftool limited by path."""

    def __init__(self, context, staged, filenames):
        super(Difftool, self).__init__(context)
        self.staged = staged
        self.filenames = filenames

    def do(self):
        difftool_launch_with_head(
            self.context, self.filenames, self.staged, self.model.head
        )


class Edit(ContextCommand):
    """Edit a file using the configured gui.editor."""

    @staticmethod
    def name():
        return N_('Launch Editor')

    def __init__(self, context, filenames, line_number=None, background_editor=False):
        super(Edit, self).__init__(context)
        self.filenames = filenames
        self.line_number = line_number
        self.background_editor = background_editor

    def do(self):
        context = self.context
        if not self.filenames:
            return
        filename = self.filenames[0]
        if not core.exists(filename):
            return
        if self.background_editor:
            editor = prefs.background_editor(context)
        else:
            editor = prefs.editor(context)
        opts = []

        if self.line_number is None:
            opts = self.filenames
        else:
            # Single-file w/ line-numbers (likely from grep)
            editor_opts = {
                '*vim*': [filename, '+%s' % self.line_number],
                '*emacs*': ['+%s' % self.line_number, filename],
                '*textpad*': ['%s(%s,0)' % (filename, self.line_number)],
                '*notepad++*': ['-n%s' % self.line_number, filename],
                '*subl*': ['%s:%s' % (filename, self.line_number)],
            }

            opts = self.filenames
            for pattern, opt in editor_opts.items():
                if fnmatch(editor, pattern):
                    opts = opt
                    break

        try:
            core.fork(utils.shell_split(editor) + opts)
        except (OSError, ValueError) as e:
            message = N_('Cannot exec "%s": please configure your editor') % editor
            _, details = utils.format_exception(e)
            Interaction.critical(N_('Error Editing File'), message, details)


class FormatPatch(ContextCommand):
    """Output a patch series given all revisions and a selected subset."""

    def __init__(self, context, to_export, revs, output='patches'):
        super(FormatPatch, self).__init__(context)
        self.to_export = list(to_export)
        self.revs = list(revs)
        self.output = output

    def do(self):
        context = self.context
        status, out, err = gitcmds.format_patchsets(
            context, self.to_export, self.revs, self.output
        )
        Interaction.log_status(status, out, err)


class LaunchDifftool(ContextCommand):
    @staticmethod
    def name():
        return N_('Launch Diff Tool')

    def do(self):
        s = self.selection.selection()
        if s.unmerged:
            paths = s.unmerged
            if utils.is_win32():
                core.fork(['git', 'mergetool', '--no-prompt', '--'] + paths)
            else:
                cfg = self.cfg
                cmd = cfg.terminal()
                argv = utils.shell_split(cmd)

                terminal = os.path.basename(argv[0])
                shellquote_terms = set(['xfce4-terminal'])
                shellquote_default = terminal in shellquote_terms

                mergetool = ['git', 'mergetool', '--no-prompt', '--']
                mergetool.extend(paths)
                needs_shellquote = cfg.get(
                    'cola.terminalshellquote', shellquote_default
                )

                if needs_shellquote:
                    argv.append(core.list2cmdline(mergetool))
                else:
                    argv.extend(mergetool)

                core.fork(argv)
        else:
            difftool_run(self.context)


class LaunchTerminal(ContextCommand):
    @staticmethod
    def name():
        return N_('Launch Terminal')

    @staticmethod
    def is_available(context):
        return context.cfg.terminal() is not None

    def __init__(self, context, path):
        super(LaunchTerminal, self).__init__(context)
        self.path = path

    def do(self):
        cmd = self.context.cfg.terminal()
        if cmd is None:
            return
        if utils.is_win32():
            argv = ['start', '', cmd, '--login']
            shell = True
        else:
            argv = utils.shell_split(cmd)
            argv.append(os.getenv('SHELL', '/bin/sh'))
            shell = False
        core.fork(argv, cwd=self.path, shell=shell)


class LaunchEditor(Edit):
    @staticmethod
    def name():
        return N_('Launch Editor')

    def __init__(self, context):
        s = context.selection.selection()
        filenames = s.staged + s.unmerged + s.modified + s.untracked
        super(LaunchEditor, self).__init__(context, filenames, background_editor=True)


class LaunchEditorAtLine(LaunchEditor):
    """Launch an editor at the specified line"""

    def __init__(self, context):
        super(LaunchEditorAtLine, self).__init__(context)
        self.line_number = context.selection.line_number


class LoadCommitMessageFromFile(ContextCommand):
    """Loads a commit message from a path."""

    UNDOABLE = True

    def __init__(self, context, path):
        super(LoadCommitMessageFromFile, self).__init__(context)
        self.path = path
        self.old_commitmsg = self.model.commitmsg
        self.old_directory = self.model.directory

    def do(self):
        path = os.path.expanduser(self.path)
        if not path or not core.isfile(path):
            raise UsageError(
                N_('Error: Cannot find commit template'),
                N_('%s: No such file or directory.') % path,
            )
        self.model.set_directory(os.path.dirname(path))
        self.model.set_commitmsg(core.read(path))

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)
        self.model.set_directory(self.old_directory)


class LoadCommitMessageFromTemplate(LoadCommitMessageFromFile):
    """Loads the commit message template specified by commit.template."""

    def __init__(self, context):
        cfg = context.cfg
        template = cfg.get('commit.template')
        super(LoadCommitMessageFromTemplate, self).__init__(context, template)

    def do(self):
        if self.path is None:
            raise UsageError(
                N_('Error: Unconfigured commit template'),
                N_(
                    'A commit template has not been configured.\n'
                    'Use "git config" to define "commit.template"\n'
                    'so that it points to a commit template.'
                ),
            )
        return LoadCommitMessageFromFile.do(self)


class LoadCommitMessageFromOID(ContextCommand):
    """Load a previous commit message"""

    UNDOABLE = True

    def __init__(self, context, oid, prefix=''):
        super(LoadCommitMessageFromOID, self).__init__(context)
        self.oid = oid
        self.old_commitmsg = self.model.commitmsg
        self.new_commitmsg = prefix + gitcmds.prev_commitmsg(context, oid)

    def do(self):
        self.model.set_commitmsg(self.new_commitmsg)

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)


class PrepareCommitMessageHook(ContextCommand):
    """Use the cola-prepare-commit-msg hook to prepare the commit message"""

    UNDOABLE = True

    def __init__(self, context):
        super(PrepareCommitMessageHook, self).__init__(context)
        self.old_commitmsg = self.model.commitmsg

    def get_message(self):

        title = N_('Error running prepare-commitmsg hook')
        hook = gitcmds.prepare_commit_message_hook(self.context)

        if os.path.exists(hook):
            filename = self.model.save_commitmsg()
            status, out, err = core.run_command([hook, filename])

            if status == 0:
                result = core.read(filename)
            else:
                result = self.old_commitmsg
                Interaction.command_error(title, hook, status, out, err)
        else:
            message = N_('A hook must be provided at "%s"') % hook
            Interaction.critical(title, message=message)
            result = self.old_commitmsg

        return result

    def do(self):
        msg = self.get_message()
        self.model.set_commitmsg(msg)

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)


class LoadFixupMessage(LoadCommitMessageFromOID):
    """Load a fixup message"""

    def __init__(self, context, oid):
        super(LoadFixupMessage, self).__init__(context, oid, prefix='fixup! ')
        if self.new_commitmsg:
            self.new_commitmsg = self.new_commitmsg.splitlines()[0]


class Merge(ContextCommand):
    """Merge commits"""

    def __init__(self, context, revision, no_commit, squash, no_ff, sign):
        super(Merge, self).__init__(context)
        self.revision = revision
        self.no_ff = no_ff
        self.no_commit = no_commit
        self.squash = squash
        self.sign = sign

    def do(self):
        squash = self.squash
        revision = self.revision
        no_ff = self.no_ff
        no_commit = self.no_commit
        sign = self.sign

        status, out, err = self.git.merge(
            revision, gpg_sign=sign, no_ff=no_ff, no_commit=no_commit, squash=squash
        )
        self.model.update_status()
        title = N_('Merge failed.  Conflict resolution is required.')
        Interaction.command(title, 'git merge', status, out, err)

        return status, out, err


class OpenDefaultApp(ContextCommand):
    """Open a file using the OS default."""

    @staticmethod
    def name():
        return N_('Open Using Default Application')

    def __init__(self, context, filenames):
        super(OpenDefaultApp, self).__init__(context)
        if utils.is_darwin():
            launcher = 'open'
        else:
            launcher = 'xdg-open'
        self.launcher = launcher
        self.filenames = filenames

    def do(self):
        if not self.filenames:
            return
        core.fork([self.launcher] + self.filenames)


class OpenParentDir(OpenDefaultApp):
    """Open parent directories using the OS default."""

    @staticmethod
    def name():
        return N_('Open Parent Directory')

    def __init__(self, context, filenames):
        OpenDefaultApp.__init__(self, context, filenames)

    def do(self):
        if not self.filenames:
            return
        dirnames = list(set([os.path.dirname(x) for x in self.filenames]))
        # os.path.dirname() can return an empty string so we fallback to
        # the current directory
        dirs = [(dirname or core.getcwd()) for dirname in dirnames]
        core.fork([self.launcher] + dirs)


class OpenNewRepo(ContextCommand):
    """Launches git-cola on a repo."""

    def __init__(self, context, repo_path):
        super(OpenNewRepo, self).__init__(context)
        self.repo_path = repo_path

    def do(self):
        self.model.set_directory(self.repo_path)
        core.fork([sys.executable, sys.argv[0], '--repo', self.repo_path])


class OpenRepo(EditModel):
    def __init__(self, context, repo_path):
        super(OpenRepo, self).__init__(context)
        self.repo_path = repo_path
        self.new_mode = self.model.mode_none
        self.new_diff_text = ''
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT
        self.new_commitmsg = ''
        self.new_filename = ''

    def do(self):
        old_repo = self.git.getcwd()
        if self.model.set_worktree(self.repo_path):
            self.fsmonitor.stop()
            self.fsmonitor.start()
            self.model.update_status()
            # Check if template should be loaded
            if self.context.cfg.get(prefs.AUTOTEMPLATE):
                template_loader = LoadCommitMessageFromTemplate(self.context)
                template_loader.do()
            else:
                self.model.set_commitmsg(self.new_commitmsg)
            settings = self.context.settings
            settings.load()
            settings.add_recent(self.repo_path, prefs.maxrecent(self.context))
            settings.save()
            super(OpenRepo, self).do()
        else:
            self.model.set_worktree(old_repo)


class OpenParentRepo(OpenRepo):
    def __init__(self, context):
        path = ''
        if version.check_git(context, 'show-superproject-working-tree'):
            status, out, _ = context.git.rev_parse(show_superproject_working_tree=True)
            if status == 0:
                path = out
        if not path:
            path = os.path.dirname(core.getcwd())
        super(OpenParentRepo, self).__init__(context, path)


class Clone(ContextCommand):
    """Clones a repository and optionally spawns a new cola session."""

    def __init__(
        self, context, url, new_directory, submodules=False, shallow=False, spawn=True
    ):
        super(Clone, self).__init__(context)
        self.url = url
        self.new_directory = new_directory
        self.submodules = submodules
        self.shallow = shallow
        self.spawn = spawn
        self.status = -1
        self.out = ''
        self.err = ''

    def do(self):
        kwargs = {}
        if self.shallow:
            kwargs['depth'] = 1
        recurse_submodules = self.submodules
        shallow_submodules = self.submodules and self.shallow

        status, out, err = self.git.clone(
            self.url,
            self.new_directory,
            recurse_submodules=recurse_submodules,
            shallow_submodules=shallow_submodules,
            **kwargs
        )

        self.status = status
        self.out = out
        self.err = err
        if status == 0 and self.spawn:
            executable = sys.executable
            core.fork([executable, sys.argv[0], '--repo', self.new_directory])
        return self


class NewBareRepo(ContextCommand):
    """Create a new shared bare repository"""

    def __init__(self, context, path):
        super(NewBareRepo, self).__init__(context)
        self.path = path

    def do(self):
        path = self.path
        status, out, err = self.git.init(path, bare=True, shared=True)
        Interaction.command(
            N_('Error'), 'git init --bare --shared "%s"' % path, status, out, err
        )
        return status == 0


def unix_path(path, is_win32=utils.is_win32):
    """Git for Windows requires unix paths, so force them here"""
    if is_win32():
        path = path.replace('\\', '/')
        first = path[0]
        second = path[1]
        if second == ':':  # sanity check, this better be a Windows-style path
            path = '/' + first + path[2:]

    return path


def sequence_editor():
    """Set GIT_SEQUENCE_EDITOR for running git-cola-sequence-editor"""
    xbase = unix_path(resources.command('git-cola-sequence-editor'))
    if utils.is_win32():
        editor = core.list2cmdline([unix_path(sys.executable), xbase])
    else:
        editor = core.list2cmdline([xbase])
    return editor


class SequenceEditorEnvironment(object):
    """Set environment variables to enable git-cola-sequence-editor"""

    def __init__(self, context, **kwargs):
        self.env = {
            'GIT_EDITOR': prefs.editor(context),
            'GIT_SEQUENCE_EDITOR': sequence_editor(),
            'GIT_COLA_SEQ_EDITOR_CANCEL_ACTION': 'save',
        }
        self.env.update(kwargs)

    def __enter__(self):
        for var, value in self.env.items():
            compat.setenv(var, value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for var in self.env:
            compat.unsetenv(var)


class Rebase(ContextCommand):
    def __init__(self, context, upstream=None, branch=None, **kwargs):
        """Start an interactive rebase session

        :param upstream: upstream branch
        :param branch: optional branch to checkout
        :param kwargs: forwarded directly to `git.rebase()`

        """
        super(Rebase, self).__init__(context)

        self.upstream = upstream
        self.branch = branch
        self.kwargs = kwargs

    def prepare_arguments(self, upstream):
        args = []
        kwargs = {}

        # Rebase actions must be the only option specified
        for action in ('continue', 'abort', 'skip', 'edit_todo'):
            if self.kwargs.get(action, False):
                kwargs[action] = self.kwargs[action]
                return args, kwargs

        kwargs['interactive'] = True
        kwargs['autosquash'] = self.kwargs.get('autosquash', True)
        kwargs.update(self.kwargs)

        if upstream:
            args.append(upstream)
        if self.branch:
            args.append(self.branch)

        return args, kwargs

    def do(self):
        (status, out, err) = (1, '', '')
        context = self.context
        cfg = self.cfg
        model = self.model

        if not cfg.get('rebase.autostash', False):
            if model.staged or model.unmerged or model.modified:
                Interaction.information(
                    N_('Unable to rebase'),
                    N_('You cannot rebase with uncommitted changes.'),
                )
                return status, out, err

        upstream = self.upstream or Interaction.choose_ref(
            context,
            N_('Select New Upstream'),
            N_('Interactive Rebase'),
            default='@{upstream}',
        )
        if not upstream:
            return status, out, err

        self.model.is_rebasing = True
        self.model.emit_updated()

        args, kwargs = self.prepare_arguments(upstream)
        upstream_title = upstream or '@{upstream}'
        with SequenceEditorEnvironment(
            self.context,
            GIT_COLA_SEQ_EDITOR_TITLE=N_('Rebase onto %s') % upstream_title,
            GIT_COLA_SEQ_EDITOR_ACTION=N_('Rebase'),
        ):
            # TODO this blocks the user interface window for the duration
            # of git-cola-sequence-editor. We would need to implement
            # signals for QProcess and continue running the main thread.
            # Alternatively, we can hide the main window while rebasing.
            # That doesn't require as much effort.
            status, out, err = self.git.rebase(
                *args, _no_win32_startupinfo=True, **kwargs
            )
        self.model.update_status()
        if err.strip() != 'Nothing to do':
            title = N_('Rebase stopped')
            Interaction.command(title, 'git rebase', status, out, err)
        return status, out, err


class RebaseEditTodo(ContextCommand):
    def do(self):
        (status, out, err) = (1, '', '')
        with SequenceEditorEnvironment(
            self.context,
            GIT_COLA_SEQ_EDITOR_TITLE=N_('Edit Rebase'),
            GIT_COLA_SEQ_EDITOR_ACTION=N_('Save'),
        ):
            status, out, err = self.git.rebase(edit_todo=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()
        return status, out, err


class RebaseContinue(ContextCommand):
    def do(self):
        (status, out, err) = (1, '', '')
        with SequenceEditorEnvironment(
            self.context,
            GIT_COLA_SEQ_EDITOR_TITLE=N_('Rebase'),
            GIT_COLA_SEQ_EDITOR_ACTION=N_('Rebase'),
        ):
            status, out, err = self.git.rebase('--continue')
        Interaction.log_status(status, out, err)
        self.model.update_status()
        return status, out, err


class RebaseSkip(ContextCommand):
    def do(self):
        (status, out, err) = (1, '', '')
        with SequenceEditorEnvironment(
            self.context,
            GIT_COLA_SEQ_EDITOR_TITLE=N_('Rebase'),
            GIT_COLA_SEQ_EDITOR_ACTION=N_('Rebase'),
        ):
            status, out, err = self.git.rebase(skip=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()
        return status, out, err


class RebaseAbort(ContextCommand):
    def do(self):
        status, out, err = self.git.rebase(abort=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()


class Rescan(ContextCommand):
    """Rescan for changes"""

    def do(self):
        self.model.update_status()


class Refresh(ContextCommand):
    """Update refs, refresh the index, and update config"""

    @staticmethod
    def name():
        return N_('Refresh')

    def do(self):
        self.model.update_status(update_index=True)
        self.cfg.update()
        self.fsmonitor.refresh()


class RefreshConfig(ContextCommand):
    """Refresh the git config cache"""

    def do(self):
        self.cfg.update()


class RevertEditsCommand(ConfirmAction):
    def __init__(self, context):
        super(RevertEditsCommand, self).__init__(context)
        self.icon = icons.undo()

    def ok_to_run(self):
        return self.model.undoable()

    # pylint: disable=no-self-use
    def checkout_from_head(self):
        return False

    def checkout_args(self):
        args = []
        s = self.selection.selection()
        if self.checkout_from_head():
            args.append(self.model.head)
        args.append('--')

        if s.staged:
            items = s.staged
        else:
            items = s.modified
        args.extend(items)

        return args

    def action(self):
        checkout_args = self.checkout_args()
        return self.git.checkout(*checkout_args)

    def success(self):
        self.model.set_diff_type(main.Types.TEXT)
        self.model.update_file_status()


class RevertUnstagedEdits(RevertEditsCommand):
    @staticmethod
    def name():
        return N_('Revert Unstaged Edits...')

    def checkout_from_head(self):
        # Being in amend mode should not affect the behavior of this command.
        # The only sensible thing to do is to checkout from the index.
        return False

    def confirm(self):
        title = N_('Revert Unstaged Changes?')
        text = N_(
            'This operation removes unstaged edits from selected files.\n'
            'These changes cannot be recovered.'
        )
        info = N_('Revert the unstaged changes?')
        ok_text = N_('Revert Unstaged Changes')
        return Interaction.confirm(
            title, text, info, ok_text, default=True, icon=self.icon
        )


class RevertUncommittedEdits(RevertEditsCommand):
    @staticmethod
    def name():
        return N_('Revert Uncommitted Edits...')

    def checkout_from_head(self):
        return True

    def confirm(self):
        """Prompt for reverting changes"""
        title = N_('Revert Uncommitted Changes?')
        text = N_(
            'This operation removes uncommitted edits from selected files.\n'
            'These changes cannot be recovered.'
        )
        info = N_('Revert the uncommitted changes?')
        ok_text = N_('Revert Uncommitted Changes')
        return Interaction.confirm(
            title, text, info, ok_text, default=True, icon=self.icon
        )


class RunConfigAction(ContextCommand):
    """Run a user-configured action, typically from the "Tools" menu"""

    def __init__(self, context, action_name):
        super(RunConfigAction, self).__init__(context)
        self.action_name = action_name

    def do(self):
        """Run the user-configured action"""
        for env in ('ARGS', 'DIRNAME', 'FILENAME', 'REVISION'):
            try:
                compat.unsetenv(env)
            except KeyError:
                pass
        rev = None
        args = None
        context = self.context
        cfg = self.cfg
        opts = cfg.get_guitool_opts(self.action_name)
        cmd = opts.get('cmd')
        if 'title' not in opts:
            opts['title'] = cmd

        if 'prompt' not in opts or opts.get('prompt') is True:
            prompt = N_('Run "%s"?') % cmd
            opts['prompt'] = prompt

        if opts.get('needsfile'):
            filename = self.selection.filename()
            if not filename:
                Interaction.information(
                    N_('Please select a file'),
                    N_('"%s" requires a selected file.') % cmd,
                )
                return False
            dirname = utils.dirname(filename, current_dir='.')
            compat.setenv('FILENAME', filename)
            compat.setenv('DIRNAME', dirname)

        if opts.get('revprompt') or opts.get('argprompt'):
            while True:
                ok = Interaction.confirm_config_action(context, cmd, opts)
                if not ok:
                    return False
                rev = opts.get('revision')
                args = opts.get('args')
                if opts.get('revprompt') and not rev:
                    title = N_('Invalid Revision')
                    msg = N_('The revision expression cannot be empty.')
                    Interaction.critical(title, msg)
                    continue
                break

        elif opts.get('confirm'):
            title = os.path.expandvars(opts.get('title'))
            prompt = os.path.expandvars(opts.get('prompt'))
            if not Interaction.question(title, prompt):
                return False
        if rev:
            compat.setenv('REVISION', rev)
        if args:
            compat.setenv('ARGS', args)
        title = os.path.expandvars(cmd)
        Interaction.log(N_('Running command: %s') % title)
        cmd = ['sh', '-c', cmd]

        if opts.get('background'):
            core.fork(cmd)
            status, out, err = (0, '', '')
        elif opts.get('noconsole'):
            status, out, err = core.run_command(cmd)
        else:
            status, out, err = Interaction.run_command(title, cmd)

        if not opts.get('background') and not opts.get('norescan'):
            self.model.update_status()

        title = N_('Error')
        Interaction.command(title, cmd, status, out, err)

        return status == 0


class SetDefaultRepo(ContextCommand):
    """Set the default repository"""

    def __init__(self, context, repo):
        super(SetDefaultRepo, self).__init__(context)
        self.repo = repo

    def do(self):
        self.cfg.set_user('cola.defaultrepo', self.repo)


class SetDiffText(EditModel):
    """Set the diff text"""

    UNDOABLE = True

    def __init__(self, context, text):
        super(SetDiffText, self).__init__(context)
        self.new_diff_text = text
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT


class SetUpstreamBranch(ContextCommand):
    """Set the upstream branch"""

    def __init__(self, context, branch, remote, remote_branch):
        super(SetUpstreamBranch, self).__init__(context)
        self.branch = branch
        self.remote = remote
        self.remote_branch = remote_branch

    def do(self):
        cfg = self.cfg
        remote = self.remote
        branch = self.branch
        remote_branch = self.remote_branch
        cfg.set_repo('branch.%s.remote' % branch, remote)
        cfg.set_repo('branch.%s.merge' % branch, 'refs/heads/' + remote_branch)


def format_hex(data):
    """Translate binary data into a hex dump"""
    hexdigits = '0123456789ABCDEF'
    result = ''
    offset = 0
    byte_offset_to_int = compat.byte_offset_to_int_converter()
    while offset < len(data):
        result += '%04u |' % offset
        textpart = ''
        for i in range(0, 16):
            if i > 0 and i % 4 == 0:
                result += ' '
            if offset < len(data):
                v = byte_offset_to_int(data[offset])
                result += ' ' + hexdigits[v >> 4] + hexdigits[v & 0xF]
                textpart += chr(v) if 32 <= v < 127 else '.'
                offset += 1
            else:
                result += '   '
                textpart += ' '
        result += ' | ' + textpart + ' |\n'

    return result


class ShowUntracked(EditModel):
    """Show an untracked file."""

    def __init__(self, context, filename):
        super(ShowUntracked, self).__init__(context)
        self.new_filename = filename
        if gitcmds.is_binary(context, filename):
            self.new_mode = self.model.mode_untracked
            self.new_diff_text = self.read(filename)
        else:
            self.new_mode = self.model.mode_untracked_diff
            self.new_diff_text = gitcmds.diff_helper(
                self.context, filename=filename, cached=False, untracked=True
            )
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT

    def read(self, filename):
        """Read file contents"""
        cfg = self.cfg
        size = cfg.get('cola.readsize', 2048)
        try:
            result = core.read(filename, size=size, encoding='bytes')
        except (IOError, OSError):
            result = ''

        truncated = len(result) == size

        encoding = cfg.file_encoding(filename) or core.ENCODING
        try:
            text_result = core.decode_maybe(result, encoding)
        except UnicodeError:
            text_result = format_hex(result)

        if truncated:
            text_result += '...'
        return text_result


class SignOff(ContextCommand):
    """Append a signoff to the commit message"""

    UNDOABLE = True

    @staticmethod
    def name():
        return N_('Sign Off')

    def __init__(self, context):
        super(SignOff, self).__init__(context)
        self.old_commitmsg = self.model.commitmsg

    def do(self):
        """Add a signoff to the commit message"""
        signoff = self.signoff()
        if signoff in self.model.commitmsg:
            return
        msg = self.model.commitmsg.rstrip()
        self.model.set_commitmsg(msg + '\n' + signoff)

    def undo(self):
        """Restore the commit message"""
        self.model.set_commitmsg(self.old_commitmsg)

    def signoff(self):
        """Generate the signoff string"""
        try:
            import pwd  # pylint: disable=all

            user = pwd.getpwuid(os.getuid()).pw_name
        except ImportError:
            user = os.getenv('USER', N_('unknown'))

        cfg = self.cfg
        name = cfg.get('user.name', user)
        email = cfg.get('user.email', '%s@%s' % (user, core.node()))
        return '\nSigned-off-by: %s <%s>' % (name, email)


def check_conflicts(context, unmerged):
    """Check paths for conflicts

    Conflicting files can be filtered out one-by-one.

    """
    if prefs.check_conflicts(context):
        unmerged = [path for path in unmerged if is_conflict_free(path)]
    return unmerged


def is_conflict_free(path):
    """Return True if `path` contains no conflict markers"""
    rgx = re.compile(r'^(<<<<<<<|\|\|\|\|\|\|\||>>>>>>>) ')
    try:
        with core.xopen(path, 'r') as f:
            for line in f:
                line = core.decode(line, errors='ignore')
                if rgx.match(line):
                    return should_stage_conflicts(path)
    except IOError:
        # We can't read this file ~ we may be staging a removal
        pass
    return True


def should_stage_conflicts(path):
    """Inform the user that a file contains merge conflicts

    Return `True` if we should stage the path nonetheless.

    """
    title = msg = N_('Stage conflicts?')
    info = (
        N_(
            '%s appears to contain merge conflicts.\n\n'
            'You should probably skip this file.\n'
            'Stage it anyways?'
        )
        % path
    )
    ok_text = N_('Stage conflicts')
    cancel_text = N_('Skip')
    return Interaction.confirm(
        title, msg, info, ok_text, default=False, cancel_text=cancel_text
    )


class Stage(ContextCommand):
    """Stage a set of paths."""

    @staticmethod
    def name():
        return N_('Stage')

    def __init__(self, context, paths):
        super(Stage, self).__init__(context)
        self.paths = paths

    def do(self):
        msg = N_('Staging: %s') % (', '.join(self.paths))
        Interaction.log(msg)
        return self.stage_paths()

    def stage_paths(self):
        """Stages add/removals to git."""
        context = self.context
        paths = self.paths
        if not paths:
            if self.model.cfg.get('cola.safemode', False):
                return (0, '', '')
            return self.stage_all()

        add = []
        remove = []

        for path in set(paths):
            if core.exists(path) or core.islink(path):
                if path.endswith('/'):
                    path = path.rstrip('/')
                add.append(path)
            else:
                remove.append(path)

        self.model.emit_about_to_update()

        # `git add -u` doesn't work on untracked files
        if add:
            status, out, err = gitcmds.add(context, add)
            Interaction.command(N_('Error'), 'git add', status, out, err)

        # If a path doesn't exist then that means it should be removed
        # from the index.   We use `git add -u` for that.
        if remove:
            status, out, err = gitcmds.add(context, remove, u=True)
            Interaction.command(N_('Error'), 'git add -u', status, out, err)

        self.model.update_files(emit=True)
        return status, out, err

    def stage_all(self):
        """Stage all files"""
        status, out, err = self.git.add(v=True, u=True)
        Interaction.command(N_('Error'), 'git add -u', status, out, err)
        self.model.update_file_status()
        return (status, out, err)


class StageCarefully(Stage):
    """Only stage when the path list is non-empty

    We use "git add -u -- <pathspec>" to stage, and it stages everything by
    default when no pathspec is specified, so this class ensures that paths
    are specified before calling git.

    When no paths are specified, the command does nothing.

    """

    def __init__(self, context):
        super(StageCarefully, self).__init__(context, None)
        self.init_paths()

    # pylint: disable=no-self-use
    def init_paths(self):
        """Initialize path data"""
        return

    def ok_to_run(self):
        """Prevent catch-all "git add -u" from adding unmerged files"""
        return self.paths or not self.model.unmerged

    def do(self):
        """Stage files when ok_to_run() return True"""
        if self.ok_to_run():
            return super(StageCarefully, self).do()
        return (0, '', '')


class StageModified(StageCarefully):
    """Stage all modified files."""

    @staticmethod
    def name():
        return N_('Stage Modified')

    def init_paths(self):
        self.paths = self.model.modified


class StageUnmerged(StageCarefully):
    """Stage unmerged files."""

    @staticmethod
    def name():
        return N_('Stage Unmerged')

    def init_paths(self):
        self.paths = check_conflicts(self.context, self.model.unmerged)


class StageUntracked(StageCarefully):
    """Stage all untracked files."""

    @staticmethod
    def name():
        return N_('Stage Untracked')

    def init_paths(self):
        self.paths = self.model.untracked


class StageModifiedAndUntracked(StageCarefully):
    """Stage all untracked files."""

    @staticmethod
    def name():
        return N_('Stage Modified and Untracked')

    def init_paths(self):
        self.paths = self.model.modified + self.model.untracked


class StageOrUnstageAll(ContextCommand):
    """If the selection is staged, unstage it, otherwise stage"""
    @staticmethod
    def name():
        return N_('Stage / Unstage All')

    def do(self):
        if self.model.staged:
            do(Unstage, self.context, self.model.staged)
        else:
            if self.cfg.get('cola.safemode', False):
                unstaged = self.model.modified
            else:
                unstaged = self.model.modified + self.model.untracked
            do(Stage, self.context, unstaged)


class StageOrUnstage(ContextCommand):
    """If the selection is staged, unstage it, otherwise stage"""

    @staticmethod
    def name():
        return N_('Stage / Unstage')

    def do(self):
        s = self.selection.selection()
        if s.staged:
            do(Unstage, self.context, s.staged)

        unstaged = []
        unmerged = check_conflicts(self.context, s.unmerged)
        if unmerged:
            unstaged.extend(unmerged)
        if s.modified:
            unstaged.extend(s.modified)
        if s.untracked:
            unstaged.extend(s.untracked)
        if unstaged:
            do(Stage, self.context, unstaged)


class Tag(ContextCommand):
    """Create a tag object."""

    def __init__(self, context, name, revision, sign=False, message=''):
        super(Tag, self).__init__(context)
        self._name = name
        self._message = message
        self._revision = revision
        self._sign = sign

    def do(self):
        result = False
        git = self.git
        revision = self._revision
        tag_name = self._name
        tag_message = self._message

        if not revision:
            Interaction.critical(
                N_('Missing Revision'), N_('Please specify a revision to tag.')
            )
            return result

        if not tag_name:
            Interaction.critical(
                N_('Missing Name'), N_('Please specify a name for the new tag.')
            )
            return result

        title = N_('Missing Tag Message')
        message = N_('Tag-signing was requested but the tag message is empty.')
        info = N_(
            'An unsigned, lightweight tag will be created instead.\n'
            'Create an unsigned tag?'
        )
        ok_text = N_('Create Unsigned Tag')
        sign = self._sign
        if sign and not tag_message:
            # We require a message in order to sign the tag, so if they
            # choose to create an unsigned tag we have to clear the sign flag.
            if not Interaction.confirm(
                title, message, info, ok_text, default=False, icon=icons.save()
            ):
                return result
            sign = False

        opts = {}
        tmp_file = None
        try:
            if tag_message:
                tmp_file = utils.tmp_filename('tag-message')
                opts['file'] = tmp_file
                core.write(tmp_file, tag_message)

            if sign:
                opts['sign'] = True
            if tag_message:
                opts['annotate'] = True
            status, out, err = git.tag(tag_name, revision, **opts)
        finally:
            if tmp_file:
                core.unlink(tmp_file)

        title = N_('Error: could not create tag "%s"') % tag_name
        Interaction.command(title, 'git tag', status, out, err)

        if status == 0:
            result = True
            self.model.update_status()
            Interaction.information(
                N_('Tag Created'),
                N_('Created a new tag named "%s"') % tag_name,
                details=tag_message or None,
            )

        return result


class Unstage(ContextCommand):
    """Unstage a set of paths."""

    @staticmethod
    def name():
        return N_('Unstage')

    def __init__(self, context, paths):
        super(Unstage, self).__init__(context)
        self.paths = paths

    def do(self):
        """Unstage paths"""
        context = self.context
        head = self.model.head
        paths = self.paths

        msg = N_('Unstaging: %s') % (', '.join(paths))
        Interaction.log(msg)
        if not paths:
            return unstage_all(context)
        status, out, err = gitcmds.unstage_paths(context, paths, head=head)
        Interaction.command(N_('Error'), 'git reset', status, out, err)
        self.model.update_file_status()
        return (status, out, err)


class UnstageAll(ContextCommand):
    """Unstage all files; resets the index."""

    def do(self):
        return unstage_all(self.context)


def unstage_all(context):
    """Unstage all files, even while amending"""
    model = context.model
    git = context.git
    head = model.head
    status, out, err = git.reset(head, '--', '.')
    Interaction.command(N_('Error'), 'git reset', status, out, err)
    model.update_file_status()
    return (status, out, err)


class StageSelected(ContextCommand):
    """Stage selected files, or all files if no selection exists."""

    def do(self):
        context = self.context
        paths = self.selection.unstaged
        if paths:
            do(Stage, context, paths)
        elif self.cfg.get('cola.safemode', False):
            do(StageModified, context)


class UnstageSelected(Unstage):
    """Unstage selected files."""

    def __init__(self, context):
        staged = self.selection.staged
        super(UnstageSelected, self).__init__(context, staged)


class Untrack(ContextCommand):
    """Unstage a set of paths."""

    def __init__(self, context, paths):
        super(Untrack, self).__init__(context)
        self.paths = paths

    def do(self):
        msg = N_('Untracking: %s') % (', '.join(self.paths))
        Interaction.log(msg)
        status, out, err = self.model.untrack_paths(self.paths)
        Interaction.log_status(status, out, err)


class UntrackedSummary(EditModel):
    """List possible .gitignore rules as the diff text."""

    def __init__(self, context):
        super(UntrackedSummary, self).__init__(context)
        untracked = self.model.untracked
        suffix = 's' if untracked else ''
        io = StringIO()
        io.write('# %s untracked file%s\n' % (len(untracked), suffix))
        if untracked:
            io.write('# possible .gitignore rule%s:\n' % suffix)
            for u in untracked:
                io.write('/' + u + '\n')
        self.new_diff_text = io.getvalue()
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT
        self.new_mode = self.model.mode_untracked


class VisualizeAll(ContextCommand):
    """Visualize all branches."""

    def do(self):
        context = self.context
        browser = utils.shell_split(prefs.history_browser(context))
        launch_history_browser(browser + ['--all'])


class VisualizeCurrent(ContextCommand):
    """Visualize all branches."""

    def do(self):
        context = self.context
        browser = utils.shell_split(prefs.history_browser(context))
        launch_history_browser(browser + [self.model.currentbranch] + ['--'])


class VisualizePaths(ContextCommand):
    """Path-limited visualization."""

    def __init__(self, context, paths):
        super(VisualizePaths, self).__init__(context)
        context = self.context
        browser = utils.shell_split(prefs.history_browser(context))
        if paths:
            self.argv = browser + ['--'] + list(paths)
        else:
            self.argv = browser

    def do(self):
        launch_history_browser(self.argv)


class VisualizeRevision(ContextCommand):
    """Visualize a specific revision."""

    def __init__(self, context, revision, paths=None):
        super(VisualizeRevision, self).__init__(context)
        self.revision = revision
        self.paths = paths

    def do(self):
        context = self.context
        argv = utils.shell_split(prefs.history_browser(context))
        if self.revision:
            argv.append(self.revision)
        if self.paths:
            argv.append('--')
            argv.extend(self.paths)
        launch_history_browser(argv)


class SubmoduleAdd(ConfirmAction):
    """Add specified submodules"""

    def __init__(self, context, url, path, branch, depth, reference):
        super(SubmoduleAdd, self).__init__(context)
        self.url = url
        self.path = path
        self.branch = branch
        self.depth = depth
        self.reference = reference

    def confirm(self):
        title = N_('Add Submodule...')
        question = N_('Add this submodule?')
        info = N_('The submodule will be added using\n' '"%s"' % self.command())
        ok_txt = N_('Add Submodule')
        return Interaction.confirm(title, question, info, ok_txt, icon=icons.ok())

    def action(self):
        context = self.context
        args = self.get_args()
        return context.git.submodule('add', *args)

    def success(self):
        self.model.update_file_status()
        self.model.update_submodules_list()

    def error_message(self):
        return N_('Error updating submodule %s' % self.path)

    def command(self):
        cmd = ['git', 'submodule', 'add']
        cmd.extend(self.get_args())
        return core.list2cmdline(cmd)

    def get_args(self):
        args = []
        if self.branch:
            args.extend(['--branch', self.branch])
        if self.reference:
            args.extend(['--reference', self.reference])
        if self.depth:
            args.extend(['--depth', '%d' % self.depth])
        args.extend(['--', self.url])
        if self.path:
            args.append(self.path)
        return args


class SubmoduleUpdate(ConfirmAction):
    """Update specified submodule"""

    def __init__(self, context, path):
        super(SubmoduleUpdate, self).__init__(context)
        self.path = path

    def confirm(self):
        title = N_('Update Submodule...')
        question = N_('Update this submodule?')
        info = N_('The submodule will be updated using\n' '"%s"' % self.command())
        ok_txt = N_('Update Submodule')
        return Interaction.confirm(
            title, question, info, ok_txt, default=False, icon=icons.pull()
        )

    def action(self):
        context = self.context
        args = self.get_args()
        return context.git.submodule(*args)

    def success(self):
        self.model.update_file_status()

    def error_message(self):
        return N_('Error updating submodule %s' % self.path)

    def command(self):
        cmd = ['git', 'submodule']
        cmd.extend(self.get_args())
        return core.list2cmdline(cmd)

    def get_args(self):
        cmd = ['update']
        if version.check_git(self.context, 'submodule-update-recursive'):
            cmd.append('--recursive')
        cmd.extend(['--', self.path])
        return cmd


class SubmodulesUpdate(ConfirmAction):
    """Update all submodules"""

    def confirm(self):
        title = N_('Update submodules...')
        question = N_('Update all submodules?')
        info = N_('All submodules will be updated using\n' '"%s"' % self.command())
        ok_txt = N_('Update Submodules')
        return Interaction.confirm(
            title, question, info, ok_txt, default=False, icon=icons.pull()
        )

    def action(self):
        context = self.context
        args = self.get_args()
        return context.git.submodule(*args)

    def success(self):
        self.model.update_file_status()

    def error_message(self):
        return N_('Error updating submodules')

    def command(self):
        cmd = ['git', 'submodule']
        cmd.extend(self.get_args())
        return core.list2cmdline(cmd)

    def get_args(self):
        cmd = ['update']
        if version.check_git(self.context, 'submodule-update-recursive'):
            cmd.append('--recursive')
        return cmd


def launch_history_browser(argv):
    """Launch the configured history browser"""
    try:
        core.fork(argv)
    except OSError as e:
        _, details = utils.format_exception(e)
        title = N_('Error Launching History Browser')
        msg = N_('Cannot exec "%s": please configure a history browser') % ' '.join(
            argv
        )
        Interaction.critical(title, message=msg, details=details)


def run(cls, *args, **opts):
    """
    Returns a callback that runs a command

    If the caller of run() provides args or opts then those are
    used instead of the ones provided by the invoker of the callback.

    """

    def runner(*local_args, **local_opts):
        """Closure return by run() which runs the command"""
        if args or opts:
            do(cls, *args, **opts)
        else:
            do(cls, *local_args, **local_opts)

    return runner


def do(cls, *args, **opts):
    """Run a command in-place"""
    try:
        cmd = cls(*args, **opts)
        return cmd.do()
    except Exception as e:  # pylint: disable=broad-except
        msg, details = utils.format_exception(e)
        if hasattr(cls, '__name__'):
            msg = '%s exception:\n%s' % (cls.__name__, msg)
        Interaction.critical(N_('Error'), message=msg, details=details)
        return None


def difftool_run(context):
    """Start a default difftool session"""
    selection = context.selection
    files = selection.group()
    if not files:
        return
    s = selection.selection()
    head = context.model.head
    difftool_launch_with_head(context, files, bool(s.staged), head)


def difftool_launch_with_head(context, filenames, staged, head):
    """Launch difftool against the provided head"""
    if head == 'HEAD':
        left = None
    else:
        left = head
    difftool_launch(context, left=left, staged=staged, paths=filenames)


def difftool_launch(
    context,
    left=None,
    right=None,
    paths=None,
    staged=False,
    dir_diff=False,
    left_take_magic=False,
    left_take_parent=False,
):
    """Launches 'git difftool' with given parameters

    :param left: first argument to difftool
    :param right: second argument to difftool_args
    :param paths: paths to diff
    :param staged: activate `git difftool --staged`
    :param dir_diff: activate `git difftool --dir-diff`
    :param left_take_magic: whether to append the magic ^! diff expression
    :param left_take_parent: whether to append the first-parent ~ for diffing

    """

    difftool_args = ['git', 'difftool', '--no-prompt']
    if staged:
        difftool_args.append('--cached')
    if dir_diff:
        difftool_args.append('--dir-diff')

    if left:
        if left_take_parent or left_take_magic:
            suffix = '^!' if left_take_magic else '~'
            # Check root commit (no parents and thus cannot execute '~')
            git = context.git
            status, out, err = git.rev_list(left, parents=True, n=1)
            Interaction.log_status(status, out, err)
            if status:
                raise OSError('git rev-list command failed')

            if len(out.split()) >= 2:
                # Commit has a parent, so we can take its child as requested
                left += suffix
            else:
                # No parent, assume it's the root commit, so we have to diff
                # against the empty tree.
                left = EMPTY_TREE_OID
                if not right and left_take_magic:
                    right = left
        difftool_args.append(left)

    if right:
        difftool_args.append(right)

    if paths:
        difftool_args.append('--')
        difftool_args.extend(paths)

    runtask = context.runtask
    if runtask:
        Interaction.async_command(N_('Difftool'), difftool_args, runtask)
    else:
        core.fork(difftool_args)
