"""Editor commands"""
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
from . import display
from . import gitcmds
from . import icons
from . import resources
from . import textwrap
from . import utils
from . import version
from .cmd import ContextCommand
from .git import STDOUT, transform_kwargs
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


class Messages:
    """Notification messages emitted by these commands"""

    DIFF_LOADING = object()


class EditModel(ContextCommand):
    """Commands that mutate the main model diff data"""

    UNDOABLE = True

    def __init__(self, context, finalizer=None):
        """Common edit operations on the main model"""
        super().__init__(context)

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
        self.finalizer = finalizer
        self.continuation = None  # A constructed finalizer.

    def do(self):
        """Perform the operation."""
        if not super().do():
            return
        self.model.filename = self.new_filename
        self.model.set_mode(self.new_mode)
        self.model.set_diff_text(self.new_diff_text)
        self.model.set_diff_type(self.new_diff_type)
        self.model.set_file_type(self.new_file_type)
        # Finalizers must be constructed after the command is triggered so that the
        # timestamp field and the model state fields are updated.
        if self.finalizer is not None:
            self.continuation = self.finalizer()
            self.context.command_bus.do(self.continuation)

    def undo(self):
        """Undo the operation."""
        if not super().undo():
            return
        self.model.filename = self.old_filename
        self.model.set_mode(self.old_mode)
        self.model.set_diff_text(self.old_diff_text)
        self.model.set_diff_type(self.old_diff_type)
        self.model.set_file_type(self.old_file_type)
        if self.continuation is not None:
            self.context.command_bus.undo(self.continuation)


class ConfirmAction(ContextCommand):
    """Confirm an action before running it"""

    def ok_to_run(self):
        """Return True when the command is okay to run"""
        return True

    def confirm(self):
        """Prompt for confirmation"""
        return True

    def action(self):
        """Run the command and return (status, out, err)"""
        return (-1, '', '')

    def success(self):
        """Callback run on success"""
        return

    def command(self):
        """Command name, for error messages"""
        return 'git'

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


class AbortApplyPatch(ConfirmAction):
    """Reset an in-progress "git am" patch application"""

    def confirm(self):
        title = N_('Abort Applying Patch...')
        question = N_('Aborting applying the current patch?')
        info = N_(
            'Aborting a patch can cause uncommitted changes to be lost.\n'
            'Recovering uncommitted changes is not possible.'
        )
        ok_txt = N_('Abort Applying Patch')
        return Interaction.confirm(
            title, question, info, ok_txt, default=False, icon=icons.undo()
        )

    def action(self):
        status, out, err = gitcmds.abort_apply_patch(self.context)
        self.model.update_file_merge_status()
        return status, out, err

    def success(self):
        self.model.set_commitmsg('')

    def error_message(self):
        return N_('Error')

    def command(self):
        return 'git am --abort'


class AbortCherryPick(ConfirmAction):
    """Reset an in-progress cherry-pick"""

    def confirm(self):
        title = N_('Abort Cherry-Pick...')
        question = N_('Aborting the current cherry-pick?')
        info = N_(
            'Aborting a cherry-pick can cause uncommitted changes to be lost.\n'
            'Recovering uncommitted changes is not possible.'
        )
        ok_txt = N_('Abort Cherry-Pick')
        return Interaction.confirm(
            title, question, info, ok_txt, default=False, icon=icons.undo()
        )

    def action(self):
        status, out, err = gitcmds.abort_cherry_pick(self.context)
        self.model.update_file_merge_status()
        return status, out, err

    def success(self):
        self.model.set_commitmsg('')

    def error_message(self):
        return N_('Error')

    def command(self):
        return 'git cherry-pick --abort'


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
        self.model.update_file_merge_status()
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
        super().__init__(context)
        self.skip = False
        self.amending = amend
        self.old_commit_author = self.model.commit_author
        self.old_commitmsg = self.model.commitmsg
        self.old_mode = self.model.mode

        if self.amending:
            author, commitmsg = gitcmds.prev_author_and_commitmsg(context)
            self.new_author = author
            self.new_commitmsg = commitmsg
            self.new_mode = self.model.mode_amend
            AmendMode.LAST_MESSAGE = self.model.commitmsg
            return
        # else, amend unchecked, regular commit
        self.new_author = ''
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
        super().do()
        self.model.set_commit_author(self.new_author)
        self.model.set_commitmsg(self.new_commitmsg)
        self.model.update_file_status()
        self.context.selection.reset(emit=True)

    def undo(self):
        if self.skip:
            return
        self.model.set_commit_author(self.old_commit_author)
        self.model.set_commitmsg(self.old_commitmsg)
        super().undo()
        self.model.update_file_status()
        self.context.selection.reset(emit=True)


class AnnexAdd(ContextCommand):
    """Add to Git Annex"""

    def __init__(self, context):
        super().__init__(context)
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
        super().__init__(context)
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


class ApplyPatch(ContextCommand):
    """Apply the specified patch to the worktree or index"""

    def __init__(
        self,
        context,
        patch,
        encoding,
        apply_to_worktree,
    ):
        super().__init__(context)
        self.patch = patch
        self.encoding = encoding
        self.apply_to_worktree = apply_to_worktree

    def do(self):
        context = self.context

        tmp_file = utils.tmp_filename('apply', suffix='.patch')
        try:
            core.write(tmp_file, self.patch.as_text(), encoding=self.encoding)
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
        super().__init__(context)
        self.patches = patches

    def do(self):
        status, output, err = self.git.am('-3', *self.patches)
        out = f'# git am -3 {core.list2cmdline(self.patches)}\n\n{output}'
        Interaction.command(N_('Patch failed to apply'), 'git am -3', status, out, err)
        # Display a diffstat
        self.model.update_file_status()

        patch_basenames = [os.path.basename(p) for p in self.patches]
        if len(patch_basenames) > 25:
            patch_basenames = patch_basenames[:25]
            patch_basenames.append('...')

        basenames = '\n'.join(patch_basenames)
        if status == 0:
            Interaction.information(
                N_('Patch(es) Applied'),
                (N_('%d patch(es) applied.') + '\n\n%s')
                % (len(self.patches), basenames),
            )


class ApplyPatchesContinue(ContextCommand):
    """Run "git am --continue" to continue on the next patch in a "git am" session"""

    def do(self):
        status, out, err = self.git.am('--continue')
        Interaction.command(
            N_('Failed to commit and continue applying patches'),
            'git am --continue',
            status,
            out,
            err,
        )
        self.model.update_status()
        return status, out, err


class ApplyPatchesSkip(ContextCommand):
    """Run "git am --skip" to continue on the next patch in a "git am" session"""

    def do(self):
        status, out, err = self.git.am(skip=True)
        Interaction.command(
            N_('Failed to continue applying patches after skipping the current patch'),
            'git am --skip',
            status,
            out,
            err,
        )
        self.model.update_status()
        return status, out, err


class Archive(ContextCommand):
    """ "Export archives using the "git archive" command"""

    def __init__(self, context, ref, fmt, prefix, filename):
        super().__init__(context)
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

    The argv list is forwarded directly to git.
    """

    def __init__(self, context, argv, checkout_branch=False):
        super().__init__(context)
        self.argv = argv
        self.checkout_branch = checkout_branch
        self.new_diff_text = ''
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT

    def do(self):
        super().do()
        if prefs.verbose_simple_commands(self.context):
            cmd_args = core.list2cmdline(self.argv)
            self.context.notifier.git_cmd(f'git checkout {cmd_args}')
        status, out, err = self.git.checkout(*self.argv)
        if self.checkout_branch:
            self.model.update_status()
        else:
            self.model.update_file_status()
        Interaction.command(N_('Error'), 'git checkout', status, out, err)
        return status, out, err


class CheckoutTheirs(ConfirmAction):
    """Checkout "their" version of a file when performing a merge"""

    @staticmethod
    def name():
        return N_('Checkout files from their branch (MERGE_HEAD)')

    def confirm(self):
        title = self.name()
        question = N_('Checkout files from their branch?')
        info = N_(
            'This operation will replace the selected unmerged files with content '
            'from the branch being merged using "git checkout --theirs".\n'
            '*ALL* uncommitted changes will be lost.\n'
            'Recovering uncommitted changes is not possible.'
        )
        ok_txt = N_('Checkout Files')
        return Interaction.confirm(
            title, question, info, ok_txt, default=True, icon=icons.merge()
        )

    def action(self):
        selection = self.selection.selection()
        paths = selection.unmerged
        if not paths:
            return 0, '', ''

        argv = ['--theirs', '--'] + paths
        cmd = Checkout(self.context, argv)
        return cmd.do()

    def error_message(self):
        return N_('Error')

    def command(self):
        return 'git checkout --theirs'


class CheckoutOurs(ConfirmAction):
    """Checkout "our" version of a file when performing a merge"""

    @staticmethod
    def name():
        return N_('Checkout files from our branch (HEAD)')

    def confirm(self):
        title = self.name()
        question = N_('Checkout files from our branch?')
        info = N_(
            'This operation will replace the selected unmerged files with content '
            'from your current branch using "git checkout --ours".\n'
            '*ALL* uncommitted changes will be lost.\n'
            'Recovering uncommitted changes is not possible.'
        )
        ok_txt = N_('Checkout Files')
        return Interaction.confirm(
            title, question, info, ok_txt, default=True, icon=icons.merge()
        )

    def action(self):
        selection = self.selection.selection()
        paths = selection.unmerged
        if not paths:
            return 0, '', ''

        argv = ['--ours', '--'] + paths
        cmd = Checkout(self.context, argv)
        return cmd.do()

    def error_message(self):
        return N_('Error')

    def command(self):
        return 'git checkout --ours'


class BlamePaths(ContextCommand):
    """Blame view for paths."""

    @staticmethod
    def name():
        return N_('Blame...')

    def __init__(self, context, paths=None):
        super().__init__(context)
        if not paths:
            paths = context.selection.union()
        viewer = utils.shell_split(prefs.blame_viewer(context))
        self.argv = viewer + list(paths)

    def do(self):
        if prefs.verbose_simple_commands(self.context):
            cmd_args = core.list2cmdline(self.argv)
            self.context.notifier.git_cmd(cmd_args)
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
        super().__init__(context, args, checkout_branch=True)


class CherryPick(ContextCommand):
    """Cherry pick commits into the current branch."""

    def __init__(self, context, commits):
        super().__init__(context)
        self.commits = commits

    def do(self):
        status, out, err = gitcmds.cherry_pick(self.context, self.commits)
        self.model.update_file_merge_status()
        title = N_('Cherry-pick failed')
        Interaction.command(title, 'git cherry-pick', status, out, err)


class Revert(ContextCommand):
    """Revert a commit"""

    def __init__(self, context, oid):
        super().__init__(context)
        self.oid = oid

    def do(self):
        status, out, err = self.git.revert(self.oid, no_edit=True)
        self.model.update_file_status()
        title = N_('Revert failed')
        out = '# git revert %s\n\n' % self.oid
        Interaction.command(title, 'git revert', status, out, err)


class ResetMode(EditModel):
    """Reset the mode and clear the model's diff text."""

    def __init__(self, context):
        super().__init__(context)
        self.new_mode = self.model.mode_none
        self.new_diff_text = ''
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT
        self.new_filename = ''

    def do(self):
        super().do()
        self.model.update_file_status()
        self.context.selection.reset(emit=True)


class ResetCommand(ConfirmAction):
    """Reset state using the "git reset" command"""

    def __init__(self, context, ref):
        super().__init__(context)
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
        if prefs.verbose_simple_commands(self.context):
            self.context.notifier.git_cmd(f'git reset --mixed {self.ref} --')
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
        if prefs.verbose_simple_commands(self.context):
            self.context.notifier.git_cmd(f'git reset --keep {self.ref} --')
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
        super().__init__(context)
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
        super().__init__(context, 'HEAD^')

    def confirm(self):
        check_published = prefs.check_published_commits(self.context)
        if check_published and self.model.is_commit_published():
            return Interaction.confirm(
                N_('Rewrite Published Commit?'),
                N_(
                    'This commit has already been published.\n'
                    'This operation will rewrite published history.\n'
                    "You probably don't want to do this."
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

    def __init__(
        self, context, amend, msg, sign, no_verify=False, author=None, date=None
    ):
        super().__init__(context)
        self.amend = amend
        self.msg = msg
        self.sign = sign
        self.no_verify = no_verify
        self.old_commitmsg = self.model.commitmsg
        self.new_commitmsg = ''
        self.author = author
        self.date = date

    def do(self):
        # Create the commit message file
        context = self.context
        msg = self.msg
        tmp_file = utils.tmp_filename('commit-message')
        add_env = {
            'NO_COLOR': '1',
            'TERM': 'dumb',
        }
        add_env.update(main.autodetect_proxy_environ())
        kwargs = {}
        # Override the commit date.
        if self.date:
            add_env['GIT_AUTHOR_DATE'] = self.date
            add_env['GIT_COMMITTER_DATE'] = self.date
            kwargs['date'] = self.date
        # Override the commit author.
        if self.author:
            kwargs['author'] = self.author

        if prefs.verbose_simple_commands(self.context):
            cmd_args = ['git', 'commit']
            cmd_args.extend(
                transform_kwargs(
                    gpg_sign=self.sign,
                    amend=self.amend,
                    no_verify=self.no_verify,
                    **kwargs,
                )
            )
            self.context.notifier.git_cmd(core.list2cmdline(cmd_args))

        try:
            core.write(tmp_file, msg)
            # Run 'git commit'
            status, out, err = self.git.commit(
                _add_env=add_env,
                F=tmp_file,
                v=True,
                gpg_sign=self.sign,
                amend=self.amend,
                no_verify=self.no_verify,
                **kwargs,
            )
        finally:
            core.unlink(tmp_file)
        if status == 0:
            super().do()
            if context.cfg.get(prefs.AUTOTEMPLATE):
                template_loader = LoadCommitMessageFromTemplate(context)
                template_loader.do()
            else:
                self.model.set_commitmsg(self.new_commitmsg)

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
        super().__init__(context)
        self.filenames = list(filenames)
        self.local = local

    def do(self):
        if not self.filenames:
            return
        new_additions = '\n'.join(self.filenames) + '\n'
        for_status = new_additions
        if self.local:
            filename = self.git.git_path('info', 'exclude')
        else:
            filename = '.gitignore'
        if core.exists(filename):
            current_list = core.read(filename)
            new_additions = current_list.rstrip() + '\n' + new_additions
        core.write(filename, new_additions)
        Interaction.log_status(0, f'Added to {filename}:\n{for_status}', '')
        self.model.update_file_status()


def file_summary(files):
    txt = core.list2cmdline(files)
    if len(txt) > 768:
        txt = txt[:768].rstrip() + '...'
    wrap = textwrap.TextWrapper()
    return '\n'.join(wrap.wrap(txt))


class RemoteCommand(ConfirmAction):
    def __init__(self, context, remote):
        super().__init__(context)
        self.remote = remote

    def success(self):
        self.cfg.reset()
        self.model.update_remotes()


class RemoteAdd(RemoteCommand):
    def __init__(self, context, remote, url):
        super().__init__(context, remote)
        self.url = url

    def action(self):
        return self.git.remote('add', self.remote, self.url)

    def error_message(self):
        return N_('Error creating remote "%s"') % self.remote

    def command(self):
        return f'git remote add "{self.remote}" "{self.url}"'


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
        super().__init__(context, remote)
        self.new_name = new_name

    def confirm(self):
        title = N_('Rename Remote')
        text = N_('Rename remote "%(current)s" to "%(new)s"?') % {
            'current': self.remote,
            'new': self.new_name,
        }
        info_text = ''
        ok_text = title
        return Interaction.confirm(title, text, info_text, ok_text)

    def action(self):
        return self.git.remote('rename', self.remote, self.new_name)

    def error_message(self):
        return N_('Error renaming "%(name)s" to "%(new_name)s"') % {
            'name': self.remote,
            'new_name': self.new_name,
        }

    def command(self):
        return f'git remote rename "{self.remote}" "{self.new_name}"'


class RemoteSetURL(RemoteCommand):
    def __init__(self, context, remote, url):
        super().__init__(context, remote)
        self.url = url

    def action(self):
        return self.git.remote('set-url', self.remote, self.url)

    def error_message(self):
        return N_('Unable to set URL for "%(name)s" to "%(url)s"') % {
            'name': self.remote,
            'url': self.url,
        }

    def command(self):
        return f'git remote set-url "{self.remote}" "{self.url}"'


class Sync(ContextCommand):
    """Sync upstream changes into the current branch"""

    def do(self):
        branch_rebase = False
        pull_rebase = False
        current_branch = gitcmds.current_branch(self.context)
        pull_rebase = self.context.cfg.get(prefs.PULL_REBASE, False)
        if current_branch:
            branch_rebase = self.context.cfg.get(
                f'branch.{current_branch}.rebase', default=False
            )

        kwargs = {}
        if pull_rebase or branch_rebase:
            if pull_rebase == 'merges':
                display_command = 'git pull --autostash --rebase=merges'
                rebase = 'merges'
            else:
                rebase = True
                display_command = 'git pull --autostash --rebase'
            kwargs['rebase'] = rebase
            kwargs['autostash'] = True
        else:
            display_command = 'git pull --ff-only'
            kwargs['ff_only'] = True

        status, out, err = self.git.pull(**kwargs)

        Interaction.log_status(status, out, err)
        self.model.update_status()

        details = f'{out}\n{err}'.rstrip()
        message = Interaction.format_command_status(display_command, status)
        if status != 0:
            title = N_('Sync failed')
            Interaction.critical(title, message=message, details=details)
        else:
            title = N_('Sync complete')
            display.push_notification(self.context, title, message)

        return status, out, err


class SyncOut(ContextCommand):
    """Push local changes to the tracking branch"""

    def do(self):
        current_branch = gitcmds.current_branch(self.context)
        if not current_branch:
            title = N_('Sync out failed')
            message = N_('No current branch')
            Interaction.critical(title, message=message)
            return -1, '', message
        tracked = gitcmds.tracked_branch(self.context, current_branch)
        if not tracked:
            title = N_('Sync out failed')
            message = N_('No tracking branch configured for %s') % current_branch
            Interaction.critical(title, message=message)
            return -1, '', message
        remote, remote_branch = gitcmds.parse_remote_branch(tracked)
        if not remote or not remote_branch:
            title = N_('Sync out failed')
            message = N_('Invalid tracking branch: %s') % tracked
            Interaction.critical(title, message=message)
            return -1, '', message

        display_command = f'git push {remote} {current_branch}'
        status, out, err = self.git.push(remote, current_branch)
        Interaction.log_status(status, out, err)

        details = f'{out}\n{err}'.rstrip()
        message = Interaction.format_command_status(display_command, status)
        if status != 0:
            title = N_('Sync out failed')
            Interaction.critical(title, message=message, details=details)
        else:
            title = N_('Sync out complete')
            display.push_notification(self.context, title, message)

        return status, out, err


class RemoteEdit(ContextCommand):
    """Combine RemoteRename and RemoteSetURL"""

    def __init__(self, context, old_name, remote, url):
        super().__init__(context)
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
        super().__init__(context)
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
        super().__init__(context)
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
        super().__init__(context, os.remove, filenames)

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
            super().do()


class MoveToTrash(RemoveFiles):
    """Move files to the trash using send2trash"""

    AVAILABLE = send2trash is not None

    def __init__(self, context, filenames):
        super().__init__(context, send2trash, filenames)


class DeleteBranch(ConfirmAction):
    """Delete a git branch."""

    def __init__(self, context, branch):
        super().__init__(context)
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
        super().__init__(context)
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
        title = N_('Rename "%s"') % path

        if os.path.isdir(path):
            base_path = os.path.dirname(path)
        else:
            base_path = path
        new_path = Interaction.save_as(base_path, title)
        if not new_path:
            return False

        status, out, err = self.git.mv(path, new_path, force=True, verbose=True)
        Interaction.command(N_('Error'), 'git mv', status, out, err)
        return status == 0


class RenameBranch(ContextCommand):
    """Rename a git branch."""

    def __init__(self, context, branch, new_branch):
        super().__init__(context)
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
        super().__init__(context, branch)
        self.remote = remote

    def action(self):
        kwargs = {}
        main.autodetect_proxy(self.context, kwargs)
        main.no_color(kwargs)
        return self.git.push(self.remote, self.branch, delete=True, **kwargs)

    def success(self):
        self.model.update_status()
        Interaction.information(
            N_('Remote Branch Deleted'),
            N_('"%(branch)s" has been deleted from "%(remote)s".')
            % {
                'branch': self.branch,
                'remote': self.remote,
            },
        )

    def error_message(self):
        return N_('Error Deleting Remote Branch')

    def command(self):
        command = 'git push --delete %s %s'
        return command % (self.remote, self.branch)


def get_mode(context, filename, staged, modified, unmerged, untracked):
    model = context.model
    if staged:
        mode = model.mode_index
    elif modified or unmerged:
        mode = model.mode_worktree
    elif untracked:
        if gitcmds.is_binary(context, filename):
            mode = model.mode_untracked
        else:
            mode = model.mode_untracked_diff
    else:
        mode = model.mode
    return mode


class DiffAgainstCommitMode(ContextCommand):
    """Diff against arbitrary commits"""

    def __init__(self, context, oid):
        super().__init__(context)
        self.oid = oid

    def do(self):
        self.model.set_mode(self.model.mode_diff, head=self.oid)
        self.model.update_file_status()


class DiffText(ContextCommand):
    """Set the diff type to text"""

    def __init__(self, context):
        super().__init__(context)
        self.new_file_type = main.Types.TEXT
        self.new_diff_type = main.Types.TEXT
        self.old_file_type = self.model.file_type
        self.old_diff_type = self.model.diff_type

    def do(self):
        """Update the diff and file type"""
        if not super().do():
            return
        self.model.set_diff_type(self.new_diff_type)
        self.model.set_file_type(self.new_file_type)

    def undo(self):
        """Revert the updating of diff and file types"""
        if not super().undo():
            return
        self.model.set_diff_type(self.old_diff_type)
        self.model.set_file_type(self.old_file_type)


class ToggleDiffType(ContextCommand):
    """Toggle the diff type between image and text"""

    def __init__(self, context):
        super().__init__(context)
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
        super().__init__(context)

        self.new_filename = filename
        self.new_diff_type = self.get_diff_type(filename)
        self.new_file_type = main.Types.IMAGE
        self.new_mode = get_mode(
            context, filename, staged, modified, unmerged, untracked
        )
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
            # Check e.g. "cola.imagediff.svg" to see if we should imagediff.
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
        super().do()

    def staged_images(self):
        context = self.context
        head = self.model.head
        missing_blob_oid = self.model.missing_blob_oid
        filename = self.new_filename
        annex = self.annex

        images = []
        index = self.git.diff_index(head, '--', filename, cached=True)[STDOUT]
        if index:
            # Example:
            #  :100644 100644 fabadb8... 4866510... M      describe.c
            parts = index.split(' ')
            if len(parts) > 3:
                old_oid = parts[2]
                new_oid = parts[3]

            if old_oid != missing_blob_oid:
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

            if new_oid != missing_blob_oid:
                found_in_annex = False
                if annex and core.islink(filename):
                    status, out, _ = self.git.annex('status', '--', filename)
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
        head = self.model.head
        missing_blob_oid = self.model.missing_blob_oid
        filename = self.new_filename
        annex = self.annex

        candidate_merge_heads = ('HEAD', 'CHERRY_HEAD', 'MERGE_HEAD')
        merge_heads = [
            merge_head
            for merge_head in candidate_merge_heads
            if core.exists(self.git.git_path(merge_head))
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
        index = self.git.diff_index(head, '--', filename, cached=True, cc=True)[STDOUT]
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
                    if oid != missing_blob_oid:
                        image = gitcmds.write_blob_path(
                            context, merge_head, oid, filename
                        )
                        if image:
                            images.append((image, True))

        images.append((filename, False))
        return images

    def modified_images(self):
        context = self.context
        head = self.model.head
        missing_blob_oid = self.model.missing_blob_oid
        filename = self.new_filename
        annex = self.annex

        images = []
        annex_image = None
        if annex:  # Check for a pre-image from git-annex
            annex_image = gitcmds.annex_path(context, head, filename)
        if annex_image:
            images.append((annex_image, False))  # git annex HEAD
        else:
            worktree = self.git.diff_files('--', filename)[STDOUT]
            parts = worktree.split(' ')
            if len(parts) > 3:
                oid = parts[2]
                if oid != missing_blob_oid:
                    image = gitcmds.write_blob_path(context, head, oid, filename)
                    if image:
                        images.append((image, True))  # HEAD

        images.append((filename, False))  # worktree
        return images


class DiffLoading(ContextCommand):
    """Notify the diff viewer the a diff is loading"""

    def do(self):
        self.context.notifier.notify(Messages.DIFF_LOADING)


class Diff(EditModel):
    """Perform a diff and set the model's current text."""

    def __init__(self, context, filename, cached=False, deleted=False, finalizer=None):
        DiffLoading(context).do()
        super().__init__(context, finalizer=finalizer)
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
        DiffLoading(context).do()
        super().__init__(context)
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

    def __init__(self, context, filename, deleted=None, finalizer=None):
        super().__init__(
            context, filename, cached=True, deleted=deleted, finalizer=finalizer
        )
        self.new_mode = self.model.mode_index


class DiffStagedSummary(EditModel):
    def __init__(self, context):
        DiffLoading(context).do()
        super().__init__(context)
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


class Edit(ContextCommand):
    """Edit a file using the configured gui.editor."""

    @staticmethod
    def name():
        return N_('Launch Editor')

    def __init__(
        self,
        context,
        filenames,
        selected_filename=None,
        line_number=None,
        background_editor=False,
    ):
        super().__init__(context)
        if filenames and not selected_filename:
            selected_filename = filenames[0]
        self.filenames = filenames
        self.selected_filename = selected_filename
        self.line_number = line_number
        self.background_editor = background_editor

    def do(self):
        context = self.context
        if not self.filenames:
            return

        if self.background_editor:
            editor = prefs.background_editor(context)
        else:
            editor = prefs.editor(context)
        if self.line_number is None or self.selected_filename is None:
            args = self.filenames
        else:
            args = []
            # grep and diff are able to open files at specific line numbers.
            # We only know the line number for the first file.
            # Some editors can only apply the '+<line-number>' argument to one file.
            filename = self.selected_filename
            editor_opts = {
                '*vim*': ['+%s' % self.line_number, filename],
                '*emacs*': ['+%s' % self.line_number, filename],
                '*textpad*': [f'{filename}({self.line_number},0)'],
                '*notepad++*': ['-n%s' % self.line_number, filename],
                '*subl*': [f'{filename}:{self.line_number}'],
                'code': [f'--goto {filename}:{self.line_number}'],
                'cursor': [f'--goto {filename}:{self.line_number}'],
            }

            use_line_numbers = False
            for pattern, opts in editor_opts.items():
                if fnmatch(editor, pattern) or fnmatch(
                    os.path.basename(editor), pattern
                ):
                    args.extend(opts)
                    use_line_numbers = True
                    break
            if use_line_numbers:
                args.extend(fname for fname in self.filenames if fname != filename)
            else:
                args = self.filenames

        try:
            core.fork(utils.shell_split(editor) + args)
        except (OSError, ValueError) as err:
            message = N_('Cannot exec "%s": please configure your editor') % editor
            _, details = utils.format_exception(err)
            Interaction.critical(N_('Error Editing File'), message, details)


class FormatPatch(ContextCommand):
    """Output a patch series given all revisions and a selected subset."""

    def __init__(self, context, to_export, revs, output='patches'):
        super().__init__(context)
        self.to_export = list(to_export)
        self.revs = list(revs)
        self.output = output

    def do(self):
        context = self.context
        status, out, err = gitcmds.format_patchsets(
            context, self.to_export, self.revs, self.output
        )
        Interaction.log_status(status, out, err)


class LaunchTerminal(ContextCommand):
    @staticmethod
    def name():
        return N_('Launch Terminal')

    @staticmethod
    def is_available(context):
        return context.cfg.terminal() is not None

    def __init__(self, context, path):
        super().__init__(context)
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
            command = '/bin/sh'
            shells = ('zsh', 'fish', 'bash', 'sh')
            for basename in shells:
                executable = core.find_executable(basename)
                if executable:
                    command = executable
                    break
            argv.append(os.getenv('SHELL', command))
            shell = False

        core.fork(argv, cwd=self.path, shell=shell)


class LaunchEditor(Edit):
    @staticmethod
    def name():
        return N_('Launch Editor')

    def __init__(self, context):
        s = context.selection.selection()
        filenames = s.staged + s.unmerged + s.modified + s.untracked
        super().__init__(context, filenames, background_editor=True)


class LaunchEditorAtLine(LaunchEditor):
    """Launch an editor at the specified line"""

    def __init__(self, context):
        super().__init__(context)
        self.line_number = context.selection.line_number
        # Ensure that the model's filename is present in self.filenames otherwise we
        # will open a file that the user never requested. This constraint also ensures
        # that the line number corresponds to the selected filename.
        if context.model.filename in self.filenames:
            self.selected_filename = context.model.filename


class LoadCommitMessageFromFile(ContextCommand):
    """Loads a commit message from a path."""

    UNDOABLE = True

    def __init__(self, context, path):
        super().__init__(context)
        self.path = path
        self.old_commitmsg = self.model.commitmsg
        self.old_directory = self.model.directory

    def do(self):
        path = os.path.expanduser(self.path)
        if not path or not core.isfile(path):
            Interaction.log(N_('Error: Cannot find commit template'))
            Interaction.log(N_('%s: No such file or directory.') % path)
            return
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
        super().__init__(context, template)

    def do(self):
        if self.path is None:
            Interaction.log(N_('Error: Unconfigured commit template'))
            Interaction.log(
                N_(
                    'A commit template has not been configured.\n'
                    'Use "git config" to define "commit.template"\n'
                    'so that it points to a commit template.'
                )
            )
            return
        return LoadCommitMessageFromFile.do(self)


class LoadCommitMessageFromOID(ContextCommand):
    """Load a previous commit message"""

    UNDOABLE = True

    def __init__(self, context, oid, prefix=''):
        super().__init__(context)
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
        super().__init__(context)
        self.old_commitmsg = self.model.commitmsg

    def get_message(self):
        title = N_('Error running prepare-commitmsg hook')
        hook = gitcmds.prepare_commit_message_hook(self.context)

        if os.path.exists(hook):
            Interaction.log('hook cola-prepare-commit-msg exists: "%s"' % hook)
            filename = self.model.save_commitmsg()

            if utils.is_win32():
                # On Windows:
                # Git hooks are not executed as native Windows executables.
                # Instead, the hook script must be invoked through bash.exe so that
                # it behaves consistently with *nix environments.
                bash = utils.find_bash_exe()
                if not bash:
                    return self.old_commitmsg

                Interaction.log('bash found: "%s"' % bash)
                # Normalize path separators
                hook_rep = hook.replace('\\', '/')
                filename_rep = filename.replace('\\', '/')

                # Run the hook through bash.exe
                cmd = [bash, hook_rep, filename_rep]

                Interaction.log("running 'prepare-commit-msg': %s" % str(cmd))
                status, out, err = core.run_command(cmd)
            else:
                # On *nix:
                # The hook script is executed directly using the given path.
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
        super().__init__(context, oid, prefix='fixup! ')
        if self.new_commitmsg:
            self.new_commitmsg = self.new_commitmsg.splitlines()[0]


class Merge(ContextCommand):
    """Merge commits"""

    def __init__(self, context, revision, no_commit, squash, no_ff, sign):
        super().__init__(context)
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

        if prefs.verbose_simple_commands(self.context):
            merge_cmd = 'git merge '
            if sign:
                merge_cmd += '--gpg-sign '
            if no_ff:
                merge_cmd += '--no-ff '
            if no_commit:
                merge_cmd += '--no-commit '
            if squash:
                merge_cmd += '--squash '
            merge_cmd += revision
            self.context.notifier.git_cmd(merge_cmd)

        status, out, err = self.git.merge(
            revision, gpg_sign=sign, no_ff=no_ff, no_commit=no_commit, squash=squash
        )
        self.model.update_status()
        title = N_('Merge failed.  Conflict resolution is required.')
        self.context.notifier.command.emit(title, 'git merge', status, out, err)

        return status, out, err


class MergeBranch(Merge):
    """Merge a branch with default settings applied"""

    def __init__(self, context, branch):
        values = context.settings.get('merge')
        no_commit = not values.get('commit', True)
        squash = values.get('squash', False)
        no_ff = values.get('no-ff', False)
        sign = values.get('sign', False)
        super().__init__(context, branch, no_commit, squash, no_ff, sign)


class OpenDefaultApp(ContextCommand):
    """Open a file using the OS default."""

    @staticmethod
    def name():
        return N_('Open Using Default Application')

    def __init__(self, context, filenames):
        super().__init__(context)
        self.filenames = filenames

    def do(self):
        if not self.filenames:
            return
        utils.launch_default_app(self.filenames)


class OpenDir(OpenDefaultApp):
    """Open directories using the OS default."""

    @staticmethod
    def name():
        return N_('Open Directory')

    @property
    def _dirnames(self):
        return self.filenames

    def do(self):
        dirnames = self._dirnames
        if not dirnames:
            return
        # An empty dirname defaults to to the current directory.
        dirs = [(dirname or core.getcwd()) for dirname in dirnames]
        utils.launch_default_app(dirs)


class OpenParentDir(OpenDir):
    """Open parent directories using the OS default."""

    @staticmethod
    def name():
        return N_('Open Parent Directory')

    @property
    def _dirnames(self):
        dirnames = list({os.path.dirname(x) for x in self.filenames})
        return dirnames


class OpenWorktree(OpenDir):
    """Open worktree directory using the OS default."""

    @staticmethod
    def name():
        return N_('Open Worktree')

    # The _unused parameter is needed by worktree_dir_action() -> common.cmd_action().
    def __init__(self, context, _unused=None):
        dirnames = [context.git.worktree()]
        super().__init__(context, dirnames)


class OpenNewRepo(ContextCommand):
    """Launches git-cola on a repo."""

    def __init__(self, context, repo_path):
        super().__init__(context)
        self.repo_path = repo_path

    def do(self):
        self.model.set_directory(self.repo_path)
        core.fork([sys.executable, sys.argv[0], '--repo', self.repo_path])


class OpenRepo(EditModel):
    def __init__(self, context, repo_path):
        super().__init__(context)
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
            self.model.update_status(reset=True)
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
            super().do()
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
        super().__init__(context, path)


class Clone(ContextCommand):
    """Clones a repository and optionally spawns a new cola session."""

    def __init__(
        self, context, url, new_directory, submodules=False, shallow=False, spawn=True
    ):
        super().__init__(context)
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

        if prefs.verbose_simple_commands(self.context):
            clone_cmd = 'git clone '
            if self.shallow:
                clone_cmd += '--depth=1 '
            if recurse_submodules:
                clone_cmd += '--recurse-submodules '
            if shallow_submodules:
                clone_cmd += '--shallow-submodules '
            clone_cmd += f'{self.url} {self.new_directory}'
            self.context.notifier.git_cmd(clone_cmd)

        status, out, err = self.git.clone(
            self.url,
            self.new_directory,
            recurse_submodules=recurse_submodules,
            shallow_submodules=shallow_submodules,
            **kwargs,
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
        super().__init__(context)
        self.path = path

    def do(self):
        path = self.path
        if prefs.verbose_simple_commands(self.context):
            self.context.notifier.git_cmd(f'git init --bare --shared {path}')

        status, out, err = self.git.init(path, bare=True, shared=True)
        Interaction.command(
            N_('Error'), 'git init --bare --shared "%s"' % path, status, out, err
        )
        return status == 0


class NoOp(ContextCommand):
    """A command that does nothing"""

    def __init__(self, context, *args, **kwargs):
        super().__init__(context)

    def do(self):
        pass


def unix_path(path, is_win32=utils.is_win32):
    """Git for Windows requires Unix paths, so force them here"""
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


class SequenceEditorEnvironment:
    """Set environment variables to enable git-cola-sequence-editor"""

    def __init__(self, context, **kwargs):
        self.env = {
            'GIT_EDITOR': prefs.editor(context),
            'GIT_SEQUENCE_EDITOR': sequence_editor(),
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
        super().__init__(context)

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

        # Prompt to determine whether or not to use "git rebase --update-refs".
        update_refs = self.context.cfg.get(prefs.REBASE_UPDATE_REFS)
        has_update_refs = version.check_git(self.context, 'rebase-update-refs')
        if (
            has_update_refs
            and update_refs is None
            and not kwargs.get('update_refs', False)
        ):
            title = N_('Update stacked branches when rebasing?')
            text = N_(
                '"git rebase --update-refs" automatically force-updates any\n'
                'branches that point to commits that are being rebased.\n\n'
                'Any branches that are checked out in a worktree are not updated.\n\n'
                'Using this feature is helpful for "stacked" branch workflows.'
            )
            info = N_('Update stacked branches when rebasing?')
            ok_text = N_('Update stacked branches')
            cancel_text = N_('Do not update stacked branches')
            update_refs = Interaction.confirm(
                title,
                text,
                info,
                ok_text,
                default=True,
                cancel_text=cancel_text,
            )
            if update_refs:
                kwargs['update_refs'] = True

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

        if prefs.verbose_simple_commands(self.context):
            rebase_cmd = ['git', 'rebase']
            rebase_cmd.extend(transform_kwargs(**kwargs))
            rebase_cmd.extend(args)
            self.context.git_cmd(core.list2cmdline(rebase_cmd))

        with SequenceEditorEnvironment(
            self.context,
            GIT_COLA_SEQ_EDITOR_TITLE=N_('Rebase onto %s') % upstream_title,
            GIT_COLA_SEQ_EDITOR_ACTION=N_('Rebase'),
        ):
            # This blocks the user interface window for the duration
            # of git-cola-sequence-editor. We would need to run the command
            # in a QRunnable task to avoid blocking the main thread.
            # Alternatively, we can hide the main window while rebasing,
            # which doesn't require as much effort.
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
        if prefs.verbose_simple_commands(self.context):
            self.context.git_cmd('git rebase --edit-todo')

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
        if prefs.verbose_simple_commands(self.context):
            self.context.git_cmd('git rebase --continue')

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
        if prefs.verbose_simple_commands(self.context):
            self.context.git_cmd('git rebase --skip')

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
        if prefs.verbose_simple_commands(self.context):
            self.context.git_cmd('git rebase --abort')
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
        self.selection.selection_changed.emit()


class RefreshConfig(ContextCommand):
    """Refresh the git config cache"""

    def do(self):
        self.cfg.update()


class RevertEditsCommand(ConfirmAction):
    def __init__(self, context):
        super().__init__(context)
        self.icon = icons.undo()

    def ok_to_run(self):
        return self.model.is_undoable()

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
        if prefs.verbose_simple_commands(self.context):
            cmd_args = core.list2cmdline(checkout_args)
            self.context.notifier.git_cmd(f'git checkout {cmd_args}')
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
        super().__init__(context)
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
        super().__init__(context)
        self.repo = repo

    def do(self):
        self.cfg.set_user('cola.defaultrepo', self.repo)


class SetDiffText(EditModel):
    """Set the diff text"""

    UNDOABLE = True

    def __init__(self, context, text):
        super().__init__(context)
        self.new_diff_text = text
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT


class SetUpstreamBranch(ContextCommand):
    """Set the upstream branch"""

    def __init__(self, context, branch, remote, remote_branch):
        super().__init__(context)
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

    def __init__(self, context, filename, finalizer=None):
        super().__init__(context, finalizer=finalizer)
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
        except OSError:
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
    """Append a sign-off to the commit message"""

    UNDOABLE = True

    @staticmethod
    def name():
        return N_('Sign Off')

    def __init__(self, context):
        super().__init__(context)
        self.old_commitmsg = self.model.commitmsg

    def do(self):
        """Add a sign-off to the commit message"""
        signoff = self.signoff()
        if signoff in self.model.commitmsg:
            return
        msg = self.model.commitmsg.rstrip()
        self.model.set_commitmsg(msg + '\n' + signoff)

    def undo(self):
        """Restore the commit message"""
        self.model.set_commitmsg(self.old_commitmsg)

    def signoff(self):
        """Generate the sign-off string"""
        name, email = self.cfg.get_author()
        return f'\nSigned-off-by: {name} <{email}>'


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
        with core.xopen(path, 'rb') as f:
            for line in f:
                line = core.decode(line, errors='ignore')
                if rgx.match(line):
                    return should_stage_conflicts(path)
    except OSError:
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
        super().__init__(context)
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
        status = 0
        out = ''
        err = ''

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
        if prefs.verbose_simple_commands(self.context):
            self.context.notifier.git_cmd('git add -u -v')
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
        super().__init__(context, None)
        self.init_paths()

    def init_paths(self):
        """Initialize path data"""
        return

    def ok_to_run(self):
        """Prevent catch-all "git add -u" from adding unmerged files"""
        return self.paths or not self.model.unmerged

    def do(self):
        """Stage files when ok_to_run() return True"""
        if self.ok_to_run():
            return super().do()
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

    def stage_all(self):
        """Disable the stage_all() behavior for untracked files"""
        return (0, '', '')


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
        super().__init__(context)
        self._name = name
        self._message = message
        self._revision = revision
        self._sign = sign

    def do(self):
        result = False
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
            if prefs.verbose_simple_commands(self.context):
                cmd_args = ['git', 'tag']
                cmd_args.extend(transform_kwargs(**opts))
                cmd_args.extend((tag_name, revision))
                self.context.notifier.git_cmd(core.list2cmdline(cmd_args))
            status, out, err = self.git.tag(tag_name, revision, **opts)
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
        super().__init__(context)
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
    head = model.head
    if prefs.verbose_simple_commands(context):
        context.notifier.git_cmd('git reset -- .')
    status, out, err = context.git.reset(head, '--', '.')
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
        staged = context.selection.staged
        super().__init__(context, staged)


class Untrack(ContextCommand):
    """Unstage a set of paths."""

    def __init__(self, context, paths):
        super().__init__(context)
        self.paths = paths

    def do(self):
        msg = N_('Untracking: %s') % (', '.join(self.paths))
        Interaction.log(msg)
        status, out, err = self.model.untrack_paths(self.paths)
        Interaction.log_status(status, out, err)


class UnmergedSummary(EditModel):
    """List unmerged files in the diff text."""

    def __init__(self, context):
        super().__init__(context)
        unmerged = self.model.unmerged
        io = StringIO()
        io.write('# %s unmerged  file(s)\n' % len(unmerged))
        if unmerged:
            io.write('\n'.join(unmerged) + '\n')
        self.new_diff_text = io.getvalue()
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT
        self.new_mode = self.model.mode_display


class UntrackedSummary(EditModel):
    """List possible .gitignore rules as the diff text."""

    def __init__(self, context):
        super().__init__(context)
        untracked = self.model.untracked
        io = StringIO()
        io.write('# %s untracked file(s)\n' % len(untracked))
        if untracked:
            io.write('# Add these lines to ".gitignore" to ignore these files:\n')
            io.write('\n'.join('/' + filename for filename in untracked) + '\n')
        self.new_diff_text = io.getvalue()
        self.new_diff_type = main.Types.TEXT
        self.new_file_type = main.Types.TEXT
        self.new_mode = self.model.mode_display


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
        super().__init__(context)
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
        super().__init__(context)
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
        super().__init__(context)
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
        args = self.get_args()
        if prefs.verbose_simple_commands(self.context):
            cmd_args = core.list2cmdline(args)
            self.context.notifier.git_cmd(f'git submodule add {cmd_args}')
        return self.git.submodule('add', *args)

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
        super().__init__(context)
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
        args = self.get_args()
        if prefs.verbose_simple_commands(self.context):
            cmd_args = core.list2cmdline(args)
            self.context.notifier.git_cmd(f'git submodule {cmd_args}')
        return self.git.submodule(*args)

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
        args = self.get_args()
        if prefs.verbose_simple_commands(self.context):
            cmd_args = core.list2cmdline(args)
            self.context.notifier.git_cmd(f'git submodule {cmd_args}')
        return self.git.submodule(*args)

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
            return do(cls, *args, **opts)
        return do(cls, *local_args, **local_opts)

    return runner


def do(cls, *args, **opts):
    """Run a command in-place"""
    try:
        cmd = cls(*args, **opts)
        return cmd.do()
    except Exception as e:
        msg, details = utils.format_exception(e)
        if hasattr(cls, '__name__'):
            msg = f'{cls.__name__} exception:\n{msg}'
        Interaction.critical(N_('Error'), message=msg, details=details)
    return None
