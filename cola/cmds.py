from __future__ import division, absolute_import, unicode_literals
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
from . import fsmonitor
from . import gitcfg
from . import gitcmds
from . import icons
from . import utils
from . import resources
from .diffparse import DiffParser
from .git import STDOUT
from .i18n import N_
from .interaction import Interaction
from .models import main
from .models import prefs
from .models import selection


class UsageError(Exception):
    """Exception class for usage errors."""
    def __init__(self, title, message):
        Exception.__init__(self, message)
        self.title = title
        self.msg = message


class BaseCommand(object):
    """Base class for all commands; provides the command pattern"""

    DISABLED = False

    def __init__(self, **kwargs):
        self.undoable = False
        for k, v in kwargs.items():
            setattr(self, k, v)

    def is_undoable(self):
        """Can this be undone?"""
        return self.undoable

    @staticmethod
    def name():
        return 'Unknown'

    def do(self):
        pass

    def undo(self):
        pass


class ConfirmAction(BaseCommand):

    def __init__(self, **kwargs):
        BaseCommand.__init__(self, **kwargs)

    def ok_to_run(self):
        return True

    def confirm(self):
        return True

    def action(self):
        return (-1, '', '')

    def ok(self, status):
        return status == 0

    def success(self):
        pass

    def fail(self, status, out, err):
        title = msg = self.error_message()
        details = self.error_details() or out + err
        Interaction.critical(title, message=msg, details=details)

    def error_message(self):
        return ''

    def error_details(self):
        return ''

    def do(self):
        status = -1
        out = err = ''
        ok = self.ok_to_run() and self.confirm()
        if ok:
            status, out, err = self.action()
            if self.ok(status):
                self.success()
            else:
                self.fail(status, out, err)

        return ok, status, out, err


class ModelCommand(BaseCommand):
    """Commands that manipulate the main models"""

    def __init__(self, **kwargs):
        # Note: self.model is set before calling the base class constructor
        # to allow being having the `model` value be overridden by passing
        # `model=xxx` during construction.
        self.model = main.model()
        BaseCommand.__init__(self, **kwargs)


class Command(ModelCommand):
    """Base class for commands that modify the main model"""

    def __init__(self):
        """Initialize the command and stash away values for use in do()"""
        # These are commonly used so let's make it easier to write new commands.
        ModelCommand.__init__(self)

        self.old_diff_text = self.model.diff_text
        self.old_filename = self.model.filename
        self.old_mode = self.model.mode

        self.new_diff_text = self.old_diff_text
        self.new_filename = self.old_filename
        self.new_mode = self.old_mode

    def do(self):
        """Perform the operation."""
        self.model.set_filename(self.new_filename)
        self.model.set_mode(self.new_mode)
        self.model.set_diff_text(self.new_diff_text)

    def undo(self):
        """Undo the operation."""
        self.model.set_diff_text(self.old_diff_text)
        self.model.set_filename(self.old_filename)
        self.model.set_mode(self.old_mode)


class AmendMode(Command):
    """Try to amend a commit."""

    LAST_MESSAGE = None

    @staticmethod
    def name():
        return N_('Amend')

    def __init__(self, amend):
        Command.__init__(self)
        self.undoable = True
        self.skip = False
        self.amending = amend
        self.old_commitmsg = self.model.commitmsg
        self.old_mode = self.model.mode

        if self.amending:
            self.new_mode = self.model.mode_amend
            self.new_commitmsg = self.model.prev_commitmsg()
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
        """Attempt to enter amend mode.  Do not allow this when merging."""
        if self.amending:
            if self.model.is_merging:
                self.skip = True
                self.model.set_mode(self.old_mode)
                Interaction.information(
                        N_('Cannot Amend'),
                        N_('You are in the middle of a merge.\n'
                           'Cannot amend while merging.'))
                return
        self.skip = False
        Command.do(self)
        self.model.set_commitmsg(self.new_commitmsg)
        self.model.update_file_status()

    def undo(self):
        if self.skip:
            return
        self.model.set_commitmsg(self.old_commitmsg)
        Command.undo(self)
        self.model.update_file_status()


class ApplyDiffSelection(Command):

    def __init__(self, first_line_idx, last_line_idx, has_selection,
                 reverse, apply_to_worktree):
        Command.__init__(self)
        self.first_line_idx = first_line_idx
        self.last_line_idx = last_line_idx
        self.has_selection = has_selection
        self.reverse = reverse
        self.apply_to_worktree = apply_to_worktree

    def do(self):
        parser = DiffParser(self.model.filename, self.model.diff_text)
        if self.has_selection:
            patch = parser.generate_patch(self.first_line_idx,
                                          self.last_line_idx,
                                          reverse=self.reverse)
        else:
            patch = parser.generate_hunk_patch(self.first_line_idx,
                                               reverse=self.reverse)
        if patch is None:
            return

        cfg = gitcfg.current()
        encoding = cfg.file_encoding(self.model.filename)
        tmp_file = utils.tmp_filename('patch')
        try:
            core.write(tmp_file, patch, encoding=encoding)
            if self.apply_to_worktree:
                status, out, err = self.model.apply_diff_to_worktree(tmp_file)
            else:
                status, out, err = self.model.apply_diff(tmp_file)
        finally:
            core.unlink(tmp_file)

        Interaction.log_status(status, out, err)
        self.model.update_file_status(update_index=True)


class ApplyPatches(Command):

    def __init__(self, patches):
        Command.__init__(self)
        self.patches = patches

    def do(self):
        diff_text = ''
        num_patches = len(self.patches)
        orig_head = self.model.git.rev_parse('HEAD')[STDOUT]

        for idx, patch in enumerate(self.patches):
            status, out, err = self.model.git.am(patch)
            # Log the git-am command
            Interaction.log_status(status, out, err)

            if num_patches > 1:
                diff = self.model.git.diff('HEAD^!', stat=True)[STDOUT]
                diff_text += (N_('PATCH %(current)d/%(count)d') %
                              dict(current=idx+1, count=num_patches))
                diff_text += ' - %s:\n%s\n\n' % (os.path.basename(patch), diff)

        diff_text += N_('Summary:') + '\n'
        diff_text += self.model.git.diff(orig_head, stat=True)[STDOUT]

        # Display a diffstat
        self.model.set_diff_text(diff_text)
        self.model.update_file_status()

        basenames = '\n'.join([os.path.basename(p) for p in self.patches])
        Interaction.information(
                N_('Patch(es) Applied'),
                (N_('%d patch(es) applied.') +
                 '\n\n%s') % (len(self.patches), basenames))


class Archive(BaseCommand):

    def __init__(self, ref, fmt, prefix, filename):
        BaseCommand.__init__(self)
        self.ref = ref
        self.fmt = fmt
        self.prefix = prefix
        self.filename = filename

    def do(self):
        fp = core.xopen(self.filename, 'wb')
        cmd = ['git', 'archive', '--format='+self.fmt]
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


class Checkout(Command):
    """
    A command object for git-checkout.

    'argv' is handed off directly to git.

    """

    def __init__(self, argv, checkout_branch=False):
        Command.__init__(self)
        self.argv = argv
        self.checkout_branch = checkout_branch
        self.new_diff_text = ''

    def do(self):
        status, out, err = self.model.git.checkout(*self.argv)
        Interaction.log_status(status, out, err)
        if self.checkout_branch:
            self.model.update_status()
        else:
            self.model.update_file_status()


class BlamePaths(Command):
    """Blame view for paths."""

    def __init__(self, paths):
        Command.__init__(self)
        viewer = utils.shell_split(prefs.blame_viewer())
        self.argv = viewer + list(paths)

    def do(self):
        try:
            core.fork(self.argv)
        except Exception as e:
            _, details = utils.format_exception(e)
            title = N_('Error Launching Blame Viewer')
            msg = (N_('Cannot exec "%s": please configure a blame viewer') %
                   ' '.join(self.argv))
            Interaction.critical(title, message=msg, details=details)


class CheckoutBranch(Checkout):
    """Checkout a branch."""

    def __init__(self, branch):
        args = [branch]
        Checkout.__init__(self, args, checkout_branch=True)


class CherryPick(Command):
    """Cherry pick commits into the current branch."""

    def __init__(self, commits):
        Command.__init__(self)
        self.commits = commits

    def do(self):
        self.model.cherry_pick_list(self.commits)
        self.model.update_file_status()


class ResetMode(Command):
    """Reset the mode and clear the model's diff text."""

    def __init__(self):
        Command.__init__(self)
        self.new_mode = self.model.mode_none
        self.new_diff_text = ''

    def do(self):
        Command.do(self)
        self.model.update_file_status()


class ResetCommand(ConfirmAction):

    def __init__(self, ref):
        ConfirmAction.__init__(self, model=main.model(), ref=ref)

    def action(self):
        status, out, err = self.reset()
        Interaction.log_status(status, out, err)
        return status, out, err

    def success(self):
        self.model.update_file_status()

    def confirm(self):
        raise NotImplemented('confirm() must be overridden')

    def reset(self):
        raise NotImplemented('reset() must be overridden')


class ResetBranchHead(ResetCommand):

    def confirm(self):
        title = N_('Reset Branch')
        question = N_('Point the current branch head to a new commit?')
        info = N_('The branch will be reset using "git reset --mixed %s"')
        ok_btn = N_('Reset Branch')
        info = info % self.ref
        return Interaction.confirm(title, question, info, ok_btn)

    def reset(self):
        git = self.model.git
        return git.reset(self.ref, '--', mixed=True)


class ResetWorktree(ResetCommand):

    def confirm(self):
        title = N_('Reset Worktree')
        question = N_('Reset worktree?')
        info = N_('The worktree will be reset using "git reset --merge %s"')
        ok_btn = N_('Reset Worktree')
        info = info % self.ref
        return Interaction.confirm(title, question, info, ok_btn)

    def reset(self):
        return self.model.git.reset(self.ref, '--', merge=True)


class Commit(ResetMode):
    """Attempt to create a new commit."""

    def __init__(self, amend, msg, sign, no_verify=False):
        ResetMode.__init__(self)
        self.amend = amend
        self.msg = msg
        self.sign = sign
        self.no_verify = no_verify
        self.old_commitmsg = self.model.commitmsg
        self.new_commitmsg = ''

    def do(self):
        # Create the commit message file
        comment_char = prefs.comment_char()
        msg = self.strip_comments(self.msg, comment_char=comment_char)
        tmp_file = utils.tmp_filename('commit-message')
        try:
            core.write(tmp_file, msg)

            # Run 'git commit'
            status, out, err = self.model.git.commit(F=tmp_file,
                                                     v=True,
                                                     gpg_sign=self.sign,
                                                     amend=self.amend,
                                                     no_verify=self.no_verify)
        finally:
            core.unlink(tmp_file)

        if status == 0:
            ResetMode.do(self)
            self.model.set_commitmsg(self.new_commitmsg)
            msg = N_('Created commit: %s') % out
        else:
            msg = N_('Commit failed: %s') % out
        Interaction.log_status(status, msg, err)

        return status, out, err

    @staticmethod
    def strip_comments(msg, comment_char='#'):
        # Strip off comments
        message_lines = [line for line in msg.split('\n')
                         if not line.startswith(comment_char)]
        msg = '\n'.join(message_lines)
        if not msg.endswith('\n'):
            msg += '\n'

        return msg


class Ignore(Command):
    """Add files to .gitignore"""

    def __init__(self, filenames):
        Command.__init__(self)
        self.filenames = list(filenames)

    def do(self):
        if not self.filenames:
            return
        new_additions = '\n'.join(self.filenames) + '\n'
        for_status = new_additions
        if core.exists('.gitignore'):
            current_list = core.read('.gitignore')
            new_additions = current_list.rstrip() + '\n' + new_additions
        core.write('.gitignore', new_additions)
        Interaction.log_status(0, 'Added to .gitignore:\n%s' % for_status, '')
        self.model.update_file_status()


def file_summary(files):
    txt = core.list2cmdline(files)
    if len(txt) > 768:
        txt = txt[:768].rstrip() + '...'
    return txt


class RemoteCommand(ConfirmAction):

    def __init__(self, remote):
        ConfirmAction.__init__(self)
        self.model = main.model()
        self.remote = remote

    def success(self):
        self.model.update_remotes()


class RemoteAdd(RemoteCommand):

    def __init__(self, remote, url):
        RemoteCommand.__init__(self, remote)
        self.url = url

    def action(self):
        git = self.model.git
        return git.remote('add', self.remote, self.url)

    def error_message(self):
        return N_('Error creating remote "%s"') % self.remote


class RemoteRemove(RemoteCommand):

    def confirm(self):
        title = N_('Delete Remote')
        question = N_('Delete remote?')
        info = N_('Delete remote "%s"') % self.remote
        ok_btn = N_('Delete')
        return Interaction.confirm(title, question, info, ok_btn)

    def action(self):
        git = self.model.git
        return git.remote('rm', self.remote)

    def error_message(self):
        return N_('Error deleting remote "%s"') % self.remote


class RemoteRename(RemoteCommand):

    def __init__(self, remote, new_remote):
        RemoteCommand.__init__(self, remote)
        self.new_remote = new_remote

    def confirm(self):
        title = N_('Rename Remote')
        question = N_('Rename remote?')
        info = (N_('Rename remote "%(current)s" to "%(new)s"?') %
                dict(current=self.remote, new=self.new_remote))
        ok_btn = N_('Rename')
        return Interaction.confirm(title, question, info, ok_btn)

    def action(self):
        git = self.model.git
        return git.remote('rename', self.remote, self.new_remote)


class RemoveFromSettings(ConfirmAction):

    def __init__(self, settings, repo, name, icon=None):
        ConfirmAction.__init__(self)
        self.settings = settings
        self.repo = repo
        self.name = name
        self.icon = icon

    def success(self):
        self.settings.save()


class RemoveBookmark(RemoveFromSettings):

    def confirm(self):
        name = self.name
        title = msg = N_('Delete Bookmark?')
        info = N_('%s will be removed from your bookmarks.') % name
        ok_text = N_('Delete Bookmark')
        return Interaction.confirm(title, msg, info, ok_text, icon=self.icon)

    def action(self):
        self.settings.remove_bookmark(self.repo, self.name)
        return (0, '', '')


class RemoveRecent(RemoveFromSettings):

    def confirm(self):
        repo = self.repo
        title = msg = N_('Remove %s from the recent list?') % repo
        info = N_('%s will be removed from your recent repositories.') % repo
        ok_text = N_('Remove')
        return Interaction.confirm(title, msg, info, ok_text, icon=self.icon)

    def action(self):
        self.settings.remove_recent(self.repo)
        return (0, '', '')


class RemoveFiles(Command):
    """Removes files."""

    def __init__(self, remover, filenames):
        Command.__init__(self)
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
                except:
                    bad_filenames.append(filename)

        if bad_filenames:
            Interaction.information(
                    N_('Error'),
                    N_('Deleting "%s" failed') % file_summary(files))

        if rescan:
            self.model.update_file_status()


class Delete(RemoveFiles):
    """Delete files."""

    def __init__(self, filenames):
        RemoveFiles.__init__(self, os.remove, filenames)

    def do(self):
        files = self.filenames
        if not files:
            return

        title = N_('Delete Files?')
        msg = N_('The following files will be deleted:') + '\n\n'
        msg += file_summary(files)
        info_txt = N_('Delete %d file(s)?') % len(files)
        ok_txt = N_('Delete Files')

        if not Interaction.confirm(title, msg, info_txt, ok_txt,
                                   default=True, icon=icons.remove()):
            return

        return RemoveFiles.do(self)


class MoveToTrash(RemoveFiles):
    """Move files to the trash using send2trash"""

    AVAILABLE = send2trash is not None

    def __init__(self, filenames):
        RemoveFiles.__init__(self, send2trash, filenames)


class DeleteBranch(Command):
    """Delete a git branch."""

    def __init__(self, branch):
        Command.__init__(self)
        self.branch = branch

    def do(self):
        status, out, err = self.model.delete_branch(self.branch)
        Interaction.log_status(status, out, err)


class RenameBranch(Command):
    """Rename a git branch."""

    def __init__(self, branch, new_branch):
        Command.__init__(self)
        self.branch = branch
        self.new_branch = new_branch

    def do(self):
        status, out, err = self.model.rename_branch(self.branch,
                                                    self.new_branch)
        Interaction.log_status(status, out, err)


class DeleteRemoteBranch(Command):
    """Delete a remote git branch."""

    def __init__(self, remote, branch):
        Command.__init__(self)
        self.remote = remote
        self.branch = branch

    def do(self):
        status, out, err = self.model.git.push(self.remote, self.branch,
                                               delete=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()

        if status == 0:
            Interaction.information(
                N_('Remote Branch Deleted'),
                N_('"%(branch)s" has been deleted from "%(remote)s".')
                % dict(branch=self.branch, remote=self.remote))
        else:
            command = 'git push'
            message = (N_('"%(command)s" returned exit status %(status)d') %
                       dict(command=command, status=status))

            Interaction.critical(N_('Error Deleting Remote Branch'),
                                 message, out + err)


class Diff(Command):
    """Perform a diff and set the model's current text."""

    def __init__(self, filename, cached=False, deleted=False):
        Command.__init__(self)
        opts = {}
        if cached:
            opts['ref'] = self.model.head
        self.new_filename = filename
        self.new_mode = self.model.mode_worktree
        self.new_diff_text = gitcmds.diff_helper(filename=filename,
                                                 cached=cached,
                                                 deleted=deleted,
                                                 **opts)


class Diffstat(Command):
    """Perform a diffstat and set the model's diff text."""

    def __init__(self):
        Command.__init__(self)
        cfg = gitcfg.current()
        diff_context = cfg.get('diff.context', 3)
        diff = self.model.git.diff(self.model.head,
                                   unified=diff_context,
                                   no_ext_diff=True,
                                   no_color=True,
                                   M=True,
                                   stat=True)[STDOUT]
        self.new_diff_text = diff
        self.new_mode = self.model.mode_diffstat


class DiffStaged(Diff):
    """Perform a staged diff on a file."""

    def __init__(self, filename, deleted=None):
        Diff.__init__(self, filename, cached=True, deleted=deleted)
        self.new_mode = self.model.mode_index


class DiffStagedSummary(Command):

    def __init__(self):
        Command.__init__(self)
        diff = self.model.git.diff(self.model.head,
                                   cached=True,
                                   no_color=True,
                                   no_ext_diff=True,
                                   patch_with_stat=True,
                                   M=True)[STDOUT]
        self.new_diff_text = diff
        self.new_mode = self.model.mode_index


class Difftool(Command):
    """Run git-difftool limited by path."""

    def __init__(self, staged, filenames):
        Command.__init__(self)
        self.staged = staged
        self.filenames = filenames

    def do(self):
        difftool_launch_with_head(self.filenames, self.staged, self.model.head)


class Edit(Command):
    """Edit a file using the configured gui.editor."""

    @staticmethod
    def name():
        return N_('Launch Editor')

    def __init__(self, filenames, line_number=None):
        Command.__init__(self)
        self.filenames = filenames
        self.line_number = line_number

    def do(self):
        if not self.filenames:
            return
        filename = self.filenames[0]
        if not core.exists(filename):
            return
        editor = prefs.editor()
        opts = []

        if self.line_number is None:
            opts = self.filenames
        else:
            # Single-file w/ line-numbers (likely from grep)
            editor_opts = {
                    '*vim*': ['+'+self.line_number, filename],
                    '*emacs*': ['+'+self.line_number, filename],
                    '*textpad*': ['%s(%s,0)' % (filename, self.line_number)],
                    '*notepad++*': ['-n'+self.line_number, filename],
            }

            opts = self.filenames
            for pattern, opt in editor_opts.items():
                if fnmatch(editor, pattern):
                    opts = opt
                    break

        try:
            core.fork(utils.shell_split(editor) + opts)
        except Exception as e:
            message = (N_('Cannot exec "%s": please configure your editor')
                       % editor)
            details = core.decode(e.strerror)
            Interaction.critical(N_('Error Editing File'), message, details)


class FormatPatch(Command):
    """Output a patch series given all revisions and a selected subset."""

    def __init__(self, to_export, revs):
        Command.__init__(self)
        self.to_export = list(to_export)
        self.revs = list(revs)

    def do(self):
        status, out, err = gitcmds.format_patchsets(self.to_export, self.revs)
        Interaction.log_status(status, out, err)


class LaunchDifftool(BaseCommand):

    @staticmethod
    def name():
        return N_('Launch Diff Tool')

    def __init__(self):
        BaseCommand.__init__(self)

    def do(self):
        s = selection.selection()
        if s.unmerged:
            paths = s.unmerged
            if utils.is_win32():
                core.fork(['git', 'mergetool', '--no-prompt', '--'] + paths)
            else:
                cfg = gitcfg.current()
                cmd = cfg.terminal()
                argv = utils.shell_split(cmd)
                mergetool = ['git', 'mergetool', '--no-prompt', '--']
                mergetool.extend(paths)
                needs_shellquote = set(['gnome-terminal', 'xfce4-terminal'])
                if os.path.basename(argv[0]) in needs_shellquote:
                    argv.append(core.list2cmdline(mergetool))
                else:
                    argv.extend(mergetool)
                core.fork(argv)
        else:
            difftool_run()


class LaunchTerminal(BaseCommand):

    @staticmethod
    def name():
        return N_('Launch Terminal')

    def __init__(self, path):
        BaseCommand.__init__(self)
        self.path = path

    def do(self):
        cfg = gitcfg.current()
        cmd = cfg.terminal()
        argv = utils.shell_split(cmd)
        argv.append(os.getenv('SHELL', '/bin/sh'))
        core.fork(argv, cwd=self.path)


class LaunchEditor(Edit):

    @staticmethod
    def name():
        return N_('Launch Editor')

    def __init__(self):
        s = selection.selection()
        allfiles = s.staged + s.unmerged + s.modified + s.untracked
        Edit.__init__(self, allfiles)


class LoadCommitMessageFromFile(Command):
    """Loads a commit message from a path."""

    def __init__(self, path):
        Command.__init__(self)
        self.undoable = True
        self.path = path
        self.old_commitmsg = self.model.commitmsg
        self.old_directory = self.model.directory

    def do(self):
        path = os.path.expanduser(self.path)
        if not path or not core.isfile(path):
            raise UsageError(N_('Error: Cannot find commit template'),
                             N_('%s: No such file or directory.') % path)
        self.model.set_directory(os.path.dirname(path))
        self.model.set_commitmsg(core.read(path))

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)
        self.model.set_directory(self.old_directory)


class LoadCommitMessageFromTemplate(LoadCommitMessageFromFile):
    """Loads the commit message template specified by commit.template."""

    def __init__(self):
        cfg = gitcfg.current()
        template = cfg.get('commit.template')
        LoadCommitMessageFromFile.__init__(self, template)

    def do(self):
        if self.path is None:
            raise UsageError(
                    N_('Error: Unconfigured commit template'),
                    N_('A commit template has not been configured.\n'
                       'Use "git config" to define "commit.template"\n'
                       'so that it points to a commit template.'))
        return LoadCommitMessageFromFile.do(self)


class LoadCommitMessageFromOID(Command):
    """Load a previous commit message"""

    def __init__(self, oid, prefix=''):
        Command.__init__(self)
        self.oid = oid
        self.old_commitmsg = self.model.commitmsg
        self.new_commitmsg = prefix + self.model.prev_commitmsg(oid)
        self.undoable = True

    def do(self):
        self.model.set_commitmsg(self.new_commitmsg)

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)


class PrepareCommitMessageHook(Command):
    """Use the cola-prepare-commit-msg hook to prepare the commit message
    """
    def __init__(self):
        Command.__init__(self)
        self.old_commitmsg = self.model.commitmsg
        self.undoable = True

    def get_message(self):

        title = N_('Error running prepare-commitmsg hook')
        hook = gitcmds.prepare_commit_message_hook()

        if os.path.exists(hook):
            filename = self.model.save_commitmsg()
            status, out, err = core.run_command([hook, filename])

            if status == 0:
                result = core.read(filename)
            else:
                result = self.old_commitmsg
                details = out or ''
                if err:
                    if details and not details.endswith('\n'):
                        details += '\n'
                    details += err
                message = N_('"%s" returned exit status %d') % (hook, status)
                Interaction.critical(title, message=message, details=details)
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

    def __init__(self, oid):
        LoadCommitMessageFromOID.__init__(self, oid, prefix='fixup! ')
        if self.new_commitmsg:
            self.new_commitmsg = self.new_commitmsg.splitlines()[0]


class Merge(Command):
    """Merge commits"""

    def __init__(self, revision, no_commit, squash, no_ff, sign):
        Command.__init__(self)
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

        status, out, err = self.model.git.merge(revision,
                                                gpg_sign=sign,
                                                no_ff=no_ff,
                                                no_commit=no_commit,
                                                squash=squash)
        Interaction.log_status(status, out, err)
        self.model.update_status()


class OpenDefaultApp(BaseCommand):
    """Open a file using the OS default."""

    @staticmethod
    def name():
        return N_('Open Using Default Application')

    def __init__(self, filenames):
        BaseCommand.__init__(self)
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

    def __init__(self, filenames):
        OpenDefaultApp.__init__(self, filenames)

    def do(self):
        if not self.filenames:
            return
        dirnames = list(set([os.path.dirname(x) for x in self.filenames]))
        # os.path.dirname() can return an empty string so we fallback to
        # the current directory
        dirs = [(dirname or core.getcwd()) for dirname in dirnames]
        core.fork([self.launcher] + dirs)


class OpenNewRepo(Command):
    """Launches git-cola on a repo."""

    def __init__(self, repo_path):
        Command.__init__(self)
        self.repo_path = repo_path

    def do(self):
        self.model.set_directory(self.repo_path)
        core.fork([sys.executable, sys.argv[0], '--repo', self.repo_path])


class OpenRepo(Command):
    def __init__(self, repo_path):
        Command.__init__(self)
        self.repo_path = repo_path

    def do(self):
        git = self.model.git
        old_repo = git.getcwd()
        if self.model.set_worktree(self.repo_path):
            fsmonitor.current().stop()
            fsmonitor.current().start()
            self.model.update_status()
        else:
            self.model.set_worktree(old_repo)


class Clone(Command):
    """Clones a repository and optionally spawns a new cola session."""

    def __init__(self, url, new_directory, spawn=True):
        Command.__init__(self)
        self.url = url
        self.new_directory = new_directory
        self.spawn = spawn

        self.ok = False
        self.error_message = ''
        self.error_details = ''

    def do(self):
        status, out, err = self.model.git.clone(self.url, self.new_directory)
        self.ok = status == 0

        if self.ok:
            if self.spawn:
                core.fork([sys.executable, sys.argv[0],
                           '--repo', self.new_directory])
        else:
            self.error_message = N_('Error: could not clone "%s"') % self.url
            self.error_details = (
                    (N_('git clone returned exit code %s') % status) +
                    ((out+err) and ('\n\n' + out + err) or ''))

        return self


def unix_path(path, is_win32=utils.is_win32):
    """Git for Windows requires unix paths, so force them here
    """
    unix_path = path
    if is_win32():
        first = path[0]
        second = path[1]
        if second == ':':  # sanity check, this better be a Windows-style path
            unix_path = '/' + first + path[2:].replace('\\', '/')

    return unix_path


class GitXBaseContext(object):

    def __init__(self, **kwargs):
        self.env = {'GIT_EDITOR': prefs.editor()}
        self.env.update(kwargs)

    def __enter__(self):
        compat.setenv('GIT_SEQUENCE_EDITOR',
                      unix_path(resources.share('bin', 'git-xbase')))
        for var, value in self.env.items():
            compat.setenv(var, value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        compat.unsetenv('GIT_SEQUENCE_EDITOR')
        for var in self.env:
            compat.unsetenv(var)


class Rebase(Command):

    def __init__(self,
                 upstream=None, branch=None, capture_output=True, **kwargs):
        """Start an interactive rebase session

        :param upstream: upstream branch
        :param branch: optional branch to checkout
        :param capture_output: whether to capture stdout and stderr
        :param kwargs: forwarded directly to `git.rebase()`

        """
        Command.__init__(self)

        self.upstream = upstream
        self.branch = branch
        self.capture_output = capture_output
        self.kwargs = kwargs

    def prepare_arguments(self):
        args = []
        kwargs = {}

        if self.capture_output:
            kwargs['_stderr'] = None
            kwargs['_stdout'] = None

        # Rebase actions must be the only option specified
        for action in ('continue', 'abort', 'skip', 'edit_todo'):
            if self.kwargs.get(action, False):
                kwargs[action] = self.kwargs[action]
                return args, kwargs

        kwargs['interactive'] = True
        kwargs['autosquash'] = self.kwargs.get('autosquash', True)
        kwargs.update(self.kwargs)

        if self.upstream:
            args.append(self.upstream)
        if self.branch:
            args.append(self.branch)

        return args, kwargs

    def do(self):
        (status, out, err) = (1, '', '')
        args, kwargs = self.prepare_arguments()
        upstream_title = self.upstream or '@{upstream}'
        with GitXBaseContext(
                GIT_XBASE_TITLE=N_('Rebase onto %s') % upstream_title,
                GIT_XBASE_ACTION=N_('Rebase')):
                # XXX this blocks the user interface window for the duration of our
                # git-xbase's invocation. would need to implement signals for
                # QProcess and continue running the main thread. alternatively we
                # could hide the main window while rebasing. that doesn't require
                # as much effort.
                status, out, err = self.model.git.rebase(*args, _no_win32_startupinfo=True, **kwargs)
        Interaction.log_status(status, out, err)
        self.model.update_status()
        return status, out, err


class RebaseEditTodo(Command):

    def do(self):
        (status, out, err) = (1, '', '')
        with GitXBaseContext(
                GIT_XBASE_TITLE=N_('Edit Rebase'),
                GIT_XBASE_ACTION=N_('Save')):
            status, out, err = self.model.git.rebase(edit_todo=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()
        return status, out, err


class RebaseContinue(Command):

    def do(self):
        (status, out, err) = (1, '', '')
        with GitXBaseContext(
                GIT_XBASE_TITLE=N_('Rebase'),
                GIT_XBASE_ACTION=N_('Rebase')):
            status, out, err = self.model.git.rebase('--continue')
        Interaction.log_status(status, out, err)
        self.model.update_status()
        return status, out, err


class RebaseSkip(Command):

    def do(self):
        (status, out, err) = (1, '', '')
        with GitXBaseContext(
                GIT_XBASE_TITLE=N_('Rebase'),
                GIT_XBASE_ACTION=N_('Rebase')):
            status, out, err = self.model.git.rebase(skip=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()
        return status, out, err


class RebaseAbort(Command):

    def do(self):
        status, out, err = self.model.git.rebase(abort=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()


class Rescan(Command):
    """Rescan for changes"""

    def do(self):
        self.model.update_status()


class Refresh(Command):
    """Update refs and refresh the index"""

    @staticmethod
    def name():
        return N_('Refresh')

    def do(self):
        self.model.update_status(update_index=True)
        fsmonitor.current().refresh()


class RevertEditsCommand(ConfirmAction):

    def __init__(self):
        ConfirmAction.__init__(self)
        self.model = main.model()
        self.icon = icons.undo()

    def ok_to_run(self):
        return self.model.undoable()

    def checkout_from_head(self):
        return False

    def checkout_args(self):
        args = []
        s = selection.selection()
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
        git = self.model.git
        checkout_args = self.checkout_args()
        return git.checkout(*checkout_args)

    def success(self):
        self.model.update_file_status()


class RevertUnstagedEdits(RevertEditsCommand):

    @staticmethod
    def name():
        return N_('Revert Unstaged Edits...')

    def checkout_from_head(self):
        # If we are amending and a modified file is selected
        # then we should include "HEAD^" on the command-line.
        selected = selection.selection()
        return not selected.staged and self.model.amending()

    def confirm(self):
        title = N_('Revert Unstaged Changes?')
        text = N_('This operation drops unstaged changes.\n'
                  'These changes cannot be recovered.')
        info = N_('Revert the unstaged changes?')
        ok_text = N_('Revert Unstaged Changes')
        return Interaction.confirm(title, text, info, ok_text,
                                   default=True, icon=self.icon)


class RevertUncommittedEdits(RevertEditsCommand):

    @staticmethod
    def name():
        return N_('Revert Uncommitted Edits...')

    def checkout_from_head(self):
        return True

    def confirm(self):
        title = N_('Revert Uncommitted Changes?')
        text = N_('This operation drops uncommitted changes.\n'
                  'These changes cannot be recovered.')
        info = N_('Revert the uncommitted changes?')
        ok_text = N_('Revert Uncommitted Changes')
        return Interaction.confirm(title, text, info, ok_text,
                                   default=True, icon=self.icon)


class RunConfigAction(Command):
    """Run a user-configured action, typically from the "Tools" menu"""

    def __init__(self, action_name):
        Command.__init__(self)
        self.action_name = action_name
        self.model = main.model()

    def do(self):
        for env in ('ARGS', 'DIRNAME', 'FILENAME', 'REVISION'):
            try:
                compat.unsetenv(env)
            except KeyError:
                pass
        rev = None
        args = None
        cfg = gitcfg.current()
        opts = cfg.get_guitool_opts(self.action_name)
        cmd = opts.get('cmd')
        if 'title' not in opts:
            opts['title'] = cmd

        if 'prompt' not in opts or opts.get('prompt') is True:
            prompt = N_('Run "%s"?') % cmd
            opts['prompt'] = prompt

        if opts.get('needsfile'):
            filename = selection.filename()
            if not filename:
                Interaction.information(
                        N_('Please select a file'),
                        N_('"%s" requires a selected file.') % cmd)
                return False
            dirname = utils.dirname(filename, current_dir='.')
            compat.setenv('FILENAME', filename)
            compat.setenv('DIRNAME', dirname)

        if opts.get('revprompt') or opts.get('argprompt'):
            while True:
                ok = Interaction.confirm_config_action(cmd, opts)
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
                return
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

        Interaction.log_status(status,
                               out and (N_('Output: %s') % out) or '',
                               err and (N_('Errors: %s') % err) or '')

        if not opts.get('background') and not opts.get('norescan'):
            self.model.update_status()
        return status


class SetDefaultRepo(Command):

    def __init__(self, repo, name):
        Command.__init__(self)
        self.repo = repo
        self.name = name

    def do(self):
        gitcfg.current().set_user('cola.defaultrepo', self.repo)


class SetDiffText(Command):

    def __init__(self, text):
        Command.__init__(self)
        self.undoable = True
        self.new_diff_text = text


class ShowUntracked(Command):
    """Show an untracked file."""

    def __init__(self, filename):
        Command.__init__(self)
        self.new_filename = filename
        self.new_mode = self.model.mode_untracked
        self.new_diff_text = self.diff_text_for(filename)

    def diff_text_for(self, filename):
        cfg = gitcfg.current()
        size = cfg.get('cola.readsize', 1024 * 2)
        try:
            result = core.read(filename, size=size,
                               encoding='utf-8', errors='ignore')
        except:
            result = ''

        if len(result) == size:
            result += '...'
        return result


class SignOff(Command):

    @staticmethod
    def name():
        return N_('Sign Off')

    def __init__(self):
        Command.__init__(self)
        self.undoable = True
        self.old_commitmsg = self.model.commitmsg

    def do(self):
        signoff = self.signoff()
        if signoff in self.model.commitmsg:
            return
        self.model.set_commitmsg(self.model.commitmsg + '\n' + signoff)

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)

    def signoff(self):
        try:
            import pwd
            user = pwd.getpwuid(os.getuid()).pw_name
        except ImportError:
            user = os.getenv('USER', N_('unknown'))

        cfg = gitcfg.current()
        name = cfg.get('user.name', user)
        email = cfg.get('user.email', '%s@%s' % (user, core.node()))
        return '\nSigned-off-by: %s <%s>' % (name, email)


def check_conflicts(unmerged):
    """Check paths for conflicts

    Conflicting files can be filtered out one-by-one.

    """
    if prefs.check_conflicts():
        unmerged = [path for path in unmerged if is_conflict_free(path)]
    return unmerged


def is_conflict_free(path):
    """Return True if `path` contains no conflict markers
    """
    rgx = re.compile(r'^(<<<<<<<|\|\|\|\|\|\|\||>>>>>>>) ')
    try:
        with core.xopen(path, 'r') as f:
            for line in f:
                line = core.decode(line, errors='ignore')
                if rgx.match(line):
                    if should_stage_conflicts(path):
                        return True
                    else:
                        return False
    except IOError:
        # We can't read this file ~ we may be staging a removal
        pass
    return True


def should_stage_conflicts(path):
    """Inform the user that a file contains merge conflicts

    Return `True` if we should stage the path nonetheless.

    """
    title = msg = N_('Stage conflicts?')
    info = N_('%s appears to contain merge conflicts.\n\n'
              'You should probably skip this file.\n'
              'Stage it anyways?') % path
    ok_text = N_('Stage conflicts')
    cancel_text = N_('Skip')
    return Interaction.confirm(title, msg, info, ok_text,
                               default=False, cancel_text=cancel_text)


class Stage(Command):
    """Stage a set of paths."""

    @staticmethod
    def name():
        return N_('Stage')

    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        msg = N_('Staging: %s') % (', '.join(self.paths))
        Interaction.log(msg)
        # Prevent external updates while we are staging files.
        # We update file stats at the end of this operation
        # so there's no harm in ignoring updates from other threads
        # (e.g. the file system change monitor).
        with CommandDisabled(UpdateFileStatus):
            self.model.stage_paths(self.paths)


class StageCarefully(Stage):
    """Only stage when the path list is non-empty

    We use "git add -u -- <pathspec>" to stage, and it stages everything by
    default when no pathspec is specified, so this class ensures that paths
    are specified before calling git.

    When no paths are specified, the command does nothing.

    """
    def __init__(self):
        Stage.__init__(self, None)
        self.init_paths()

    def init_paths(self):
        pass

    def ok_to_run(self):
        """Prevent catch-all "git add -u" from adding unmerged files"""
        return self.paths or not self.model.unmerged

    def do(self):
        if self.ok_to_run():
            Stage.do(self)


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
        self.paths = check_conflicts(self.model.unmerged)


class StageUntracked(StageCarefully):
    """Stage all untracked files."""

    @staticmethod
    def name():
        return N_('Stage Untracked')

    def init_paths(self):
        self.paths = self.model.untracked


class StageOrUnstage(Command):
    """If the selection is staged, unstage it, otherwise stage"""

    @staticmethod
    def name():
        return N_('Stage / Unstage')

    def do(self):
        s = selection.selection()
        if s.staged:
            do(Unstage, s.staged)

        unstaged = []
        unmerged = check_conflicts(s.unmerged)
        if unmerged:
            unstaged.extend(unmerged)
        if s.modified:
            unstaged.extend(s.modified)
        if s.untracked:
            unstaged.extend(s.untracked)
        if unstaged:
            do(Stage, unstaged)


class Tag(Command):
    """Create a tag object."""

    def __init__(self, name, revision, sign=False, message=''):
        Command.__init__(self)
        self._name = name
        self._message = message
        self._revision = revision
        self._sign = sign

    def do(self):
        log_msg = (N_('Tagging "%(revision)s" as "%(name)s"') %
                   dict(revision=self._revision, name=self._name))
        opts = {}
        tmp_file = None
        try:
            if self._message:
                tmp_file = utils.tmp_filename('tag-message')
                opts['F'] = tmp_file
                core.write(tmp_file, self._message)

            if self._sign:
                log_msg += ' (%s)' % N_('GPG-signed')
                opts['s'] = True
            else:
                opts['a'] = bool(self._message)
            status, output, err = self.model.git.tag(self._name,
                                                     self._revision, **opts)
        finally:
            if tmp_file:
                core.unlink(tmp_file)

        if output:
            log_msg += '\n' + (N_('Output: %s') % output)

        Interaction.log_status(status, log_msg, err)
        if status == 0:
            self.model.update_status()
        return (status, output, err)


class Unstage(Command):
    """Unstage a set of paths."""

    @staticmethod
    def name():
        return N_('Unstage')

    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        msg = N_('Unstaging: %s') % (', '.join(self.paths))
        Interaction.log(msg)
        with CommandDisabled(UpdateFileStatus):
            self.model.unstage_paths(self.paths)


class UnstageAll(Command):
    """Unstage all files; resets the index."""

    def do(self):
        self.model.unstage_all()


class UnstageSelected(Unstage):
    """Unstage selected files."""

    def __init__(self):
        Unstage.__init__(self, selection.selection_model().staged)


class Untrack(Command):
    """Unstage a set of paths."""

    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        msg = N_('Untracking: %s') % (', '.join(self.paths))
        Interaction.log(msg)
        with CommandDisabled(UpdateFileStatus):
            status, out, err = self.model.untrack_paths(self.paths)
        Interaction.log_status(status, out, err)


class UntrackedSummary(Command):
    """List possible .gitignore rules as the diff text."""

    def __init__(self):
        Command.__init__(self)
        untracked = self.model.untracked
        suffix = len(untracked) > 1 and 's' or ''
        io = StringIO()
        io.write('# %s untracked file%s\n' % (len(untracked), suffix))
        if untracked:
            io.write('# possible .gitignore rule%s:\n' % suffix)
            for u in untracked:
                io.write('/'+u+'\n')
        self.new_diff_text = io.getvalue()
        self.new_mode = self.model.mode_untracked


class UpdateFileStatus(Command):
    """Rescans for changes."""

    def do(self):
        self.model.update_file_status()


class VisualizeAll(Command):
    """Visualize all branches."""

    def do(self):
        browser = utils.shell_split(prefs.history_browser())
        launch_history_browser(browser + ['--all'])


class VisualizeCurrent(Command):
    """Visualize all branches."""

    def do(self):
        browser = utils.shell_split(prefs.history_browser())
        launch_history_browser(browser + [self.model.currentbranch])


class VisualizePaths(Command):
    """Path-limited visualization."""

    def __init__(self, paths):
        Command.__init__(self)
        browser = utils.shell_split(prefs.history_browser())
        if paths:
            self.argv = browser + list(paths)
        else:
            self.argv = browser

    def do(self):
        launch_history_browser(self.argv)


class VisualizeRevision(Command):
    """Visualize a specific revision."""

    def __init__(self, revision, paths=None):
        Command.__init__(self)
        self.revision = revision
        self.paths = paths

    def do(self):
        argv = utils.shell_split(prefs.history_browser())
        if self.revision:
            argv.append(self.revision)
        if self.paths:
            argv.append('--')
            argv.extend(self.paths)
        launch_history_browser(argv)


def launch_history_browser(argv):
    try:
        core.fork(argv)
    except Exception as e:
        _, details = utils.format_exception(e)
        title = N_('Error Launching History Browser')
        msg = (N_('Cannot exec "%s": please configure a history browser') %
               ' '.join(argv))
        Interaction.critical(title, message=msg, details=details)


def run(cls, *args, **opts):
    """
    Returns a callback that runs a command

    If the caller of run() provides args or opts then those are
    used instead of the ones provided by the invoker of the callback.

    """
    def runner(*local_args, **local_opts):
        if args or opts:
            do(cls, *args, **opts)
        else:
            do(cls, *local_args, **local_opts)

    return runner


class CommandDisabled(object):

    """Context manager to temporarily disable a command from running"""
    def __init__(self, cmdclass):
        self.cmdclass = cmdclass

    def __enter__(self):
        self.cmdclass.DISABLED = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cmdclass.DISABLED = False


def do(cls, *args, **opts):
    """Run a command in-place"""
    return do_cmd(cls(*args, **opts))


def do_cmd(cmd):
    if hasattr(cmd, 'DISABLED') and cmd.DISABLED:
        return None
    try:
        return cmd.do()
    except Exception as e:
        msg, details = utils.format_exception(e)
        Interaction.critical(N_('Error'), message=msg, details=details)
        return None


def difftool_run():
    """Start a default difftool session"""
    files = selection.selected_group()
    if not files:
        return
    s = selection.selection()
    model = main.model()
    difftool_launch_with_head(files, bool(s.staged), model.head)


def difftool_launch_with_head(filenames, staged, head):
    """Launch difftool against the provided head"""
    if head == 'HEAD':
        left = None
    else:
        left = head
    difftool_launch(left=left, staged=staged, paths=filenames)


def difftool_launch(left=None, right=None, paths=None,
                    staged=False, dir_diff=False,
                    left_take_magic=False, left_take_parent=False):
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
            suffix = left_take_magic and '^!' or '~'
            # Check root commit (no parents and thus cannot execute '~')
            model = main.model()
            git = model.git
            status, out, err = git.rev_list(left, parents=True, n=1)
            Interaction.log_status(status, out, err)
            if status:
                raise OSError('git rev-list command failed')

            if len(out.split()) >= 2:
                # Commit has a parent, so we can take its child as requested
                left += suffix
            else:
                # No parent, assume it's the root commit, so we have to diff
                # against the empty tree.  Git's empty tree is a built-in
                # constant object name.
                left = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
                if not right and left_take_magic:
                    right = left
        difftool_args.append(left)

    if right:
        difftool_args.append(right)

    if paths:
        difftool_args.append('--')
        difftool_args.extend(paths)

    core.fork(difftool_args)
