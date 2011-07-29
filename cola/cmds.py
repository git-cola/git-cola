import os
import sys

from cStringIO import StringIO
import commands

import cola
from cola import i18n
from cola import core
from cola import errors
from cola import gitcfg
from cola import gitcmds
from cola import utils
from cola import signals
from cola import cmdfactory
from cola import difftool
from cola import version
from cola.diffparse import DiffParser
from cola.models import selection

_notifier = cola.notifier()
_factory = cmdfactory.factory()
_config = gitcfg.instance()


class Command(object):
    """Base class for all commands; provides the command pattern."""
    def __init__(self):
        """Initialize the command and stash away values for use in do()"""
        # These are commonly used so let's make it easier to write new commands.
        self.undoable = False
        self.model = cola.model()

        self.old_diff_text = self.model.diff_text
        self.old_filename = self.model.filename
        self.old_mode = self.model.mode
        self.old_head = self.model.head

        self.new_diff_text = self.old_diff_text
        self.new_filename = self.old_filename
        self.new_head = self.old_head
        self.new_mode = self.old_mode

    def do(self):
        """Perform the operation."""
        self.model.set_diff_text(self.new_diff_text)
        self.model.set_filename(self.new_filename)
        self.model.set_head(self.new_head)
        self.model.set_mode(self.new_mode)

    def is_undoable(self):
        """Can this be undone?"""
        return self.undoable

    def undo(self):
        """Undo the operation."""
        self.model.set_diff_text(self.old_diff_text)
        self.model.set_filename(self.old_filename)
        self.model.set_head(self.old_head)
        self.model.set_mode(self.old_mode)

    def name(self):
        """Return this command's name."""
        return self.__class__.__name__


class AmendMode(Command):
    """Try to amend a commit."""
    def __init__(self, amend):
        Command.__init__(self)
        self.undoable = True
        self.skip = False
        self.amending = amend
        self.old_commitmsg = self.model.commitmsg

        if self.amending:
            self.new_mode = self.model.mode_amend
            self.new_head = 'HEAD^'
            self.new_commitmsg = self.model.prev_commitmsg()
            return
        # else, amend unchecked, regular commit
        self.new_mode = self.model.mode_none
        self.new_head = 'HEAD'
        self.new_commitmsg = self.model.commitmsg
        # If we're going back into new-commit-mode then search the
        # undo stack for a previous amend-commit-mode and grab the
        # commit message at that point in time.
        if not _factory.undostack:
            return
        undo_count = len(_factory.undostack)
        for i in xrange(undo_count):
            # Find the latest AmendMode command
            idx = undo_count - i - 1
            cmdobj = _factory.undostack[idx]
            if type(cmdobj) is not AmendMode:
                continue
            if cmdobj.amending:
                self.new_commitmsg = cmdobj.old_commitmsg
                break

    def do(self):
        """Leave/enter amend mode."""
        """Attempt to enter amend mode.  Do not allow this when merging."""
        if self.amending:
            if os.path.exists(self.model.git.git_path('MERGE_HEAD')):
                self.skip = True
                _notifier.broadcast(signals.amend, False)
                _factory.prompt_user(signals.information,
                                    'Oops! Unmerged',
                                    'You are in the middle of a merge.\n'
                                    'You cannot amend while merging.')
                return
        self.skip = False
        _notifier.broadcast(signals.amend, self.amending)
        self.model.set_commitmsg(self.new_commitmsg)
        Command.do(self)
        self.model.update_file_status()

    def undo(self):
        if self.skip:
            return
        self.model.set_commitmsg(self.old_commitmsg)
        Command.undo(self)
        self.model.update_file_status()


class ApplyDiffSelection(Command):
    def __init__(self, staged, selected, offset, selection, apply_to_worktree):
        Command.__init__(self)
        self.staged = staged
        self.selected = selected
        self.offset = offset
        self.selection = selection
        self.apply_to_worktree = apply_to_worktree

    def do(self):
        if self.model.mode == self.model.mode_branch:
            # We're applying changes from a different branch!
            parser = DiffParser(self.model,
                                filename=self.model.filename,
                                cached=False,
                                branch=self.model.head)
            status, output = \
            parser.process_diff_selection(self.selected,
                                          self.offset,
                                          self.selection,
                                          apply_to_worktree=True)
        else:
            # The normal worktree vs index scenario
            parser = DiffParser(self.model,
                                filename=self.model.filename,
                                cached=self.staged,
                                reverse=self.apply_to_worktree)
            status, output = \
            parser.process_diff_selection(self.selected,
                                          self.offset,
                                          self.selection,
                                          apply_to_worktree=
                                              self.apply_to_worktree)
        _notifier.broadcast(signals.log_cmd, status, output)
        # Redo the diff to show changes
        if self.staged:
            diffcmd = DiffStaged([self.model.filename])
        else:
            diffcmd = Diff([self.model.filename])
        diffcmd.do()
        self.model.update_file_status()


class ApplyPatches(Command):
    def __init__(self, patches):
        Command.__init__(self)
        patches.sort()
        self.patches = patches

    def do(self):
        diff_text = ''
        num_patches = len(self.patches)
        orig_head = self.model.git.rev_parse('HEAD')

        for idx, patch in enumerate(self.patches):
            status, output = self.model.git.am(patch,
                                               with_status=True,
                                               with_stderr=True)
            # Log the git-am command
            _notifier.broadcast(signals.log_cmd, status, output)

            if num_patches > 1:
                diff = self.model.git.diff('HEAD^!', stat=True)
                diff_text += 'Patch %d/%d - ' % (idx+1, num_patches)
                diff_text += '%s:\n%s\n\n' % (os.path.basename(patch), diff)

        diff_text += 'Summary:\n'
        diff_text += self.model.git.diff(orig_head, stat=True)

        # Display a diffstat
        self.model.set_diff_text(diff_text)

        _factory.prompt_user(signals.information,
                            'Patch(es) Applied',
                            '%d patch(es) applied:\n\n%s' %
                            (len(self.patches),
                             '\n'.join(map(os.path.basename, self.patches))))

        self.model.update_file_status()


class HeadChangeCommand(Command):
    """Changes the model's current head."""
    def __init__(self, treeish):
        Command.__init__(self)
        self.new_head = treeish
        self.new_diff_text = ''

    def do(self):
        Command.do(self)
        self.model.update_file_status()


class BranchMode(HeadChangeCommand):
    """Enter into diff-branch mode."""
    def __init__(self, treeish, filename):
        HeadChangeCommand.__init__(self, treeish)
        self.old_filename = self.model.filename
        self.new_filename = filename
        self.new_mode = self.model.mode_branch
        self.new_diff_text = gitcmds.diff_helper(filename=filename,
                                                 cached=False,
                                                 reverse=True,
                                                 branch=treeish)
class Checkout(Command):
    """
    A command object for git-checkout.

    'argv' is handed off directly to git.

    """
    def __init__(self, argv, checkout_branch=False):
        Command.__init__(self)
        self.argv = argv
        self.checkout_branch = checkout_branch

    def do(self):
        status, output = self.model.git.checkout(with_stderr=True,
                                                 with_status=True, *self.argv)
        _notifier.broadcast(signals.log_cmd, status, output)
        self.model.set_diff_text('')
        if self.checkout_branch:
            self.model.update_status()
        else:
            self.model.update_file_status()


class CheckoutBranch(Checkout):
    """Checkout a branch."""
    def __init__(self, branch, checkout_branch=True):
        Checkout.__init__(self, [branch])


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
        self.new_head = 'HEAD'
        self.new_diff_text = ''

    def do(self):
        Command.do(self)
        self.model.update_file_status()


class Commit(ResetMode):
    """Attempt to create a new commit."""
    def __init__(self, amend, msg):
        ResetMode.__init__(self)
        self.amend = amend
        self.msg = core.encode(msg)
        self.old_commitmsg = self.model.commitmsg
        self.new_commitmsg = ''

    def do(self):
        status, output = self.model.commit_with_msg(self.msg, amend=self.amend)
        if status == 0:
            ResetMode.do(self)
            self.model.set_commitmsg(self.new_commitmsg)
            title = 'Commit: '
        else:
            title = 'Commit failed: '
        _notifier.broadcast(signals.log_cmd, status, title+output)


class Ignore(Command):
    """Add files to .gitignore"""
    def __init__(self, filenames):
        Command.__init__(self)
        self.filenames = filenames

    def do(self):
        new_additions = ''
        for fname in self.filenames:
            new_additions = new_additions + fname + '\n'
        for_status = new_additions
        if new_additions:
            if '.gitignore' in gitcmds.all_files():
                current_list = utils.slurp('.gitignore')
                new_additions = new_additions + current_list
            utils.write('.gitignore', new_additions)
            _notifier.broadcast(signals.log_cmd,
                                0,
                                'Added to .gitignore:\n%s' % for_status)
            self.model.update_file_status()


class Delete(Command):
    """Simply delete files."""
    def __init__(self, filenames):
        Command.__init__(self)
        self.filenames = filenames
        # We could git-hash-object stuff and provide undo-ability
        # as an option.  Heh.
    def do(self):
        rescan = False
        for filename in self.filenames:
            if filename:
                try:
                    os.remove(filename)
                    rescan=True
                except:
                    _factory.prompt_user(signals.information,
                                        'Error'
                                        'Deleting "%s" failed.' % filename)
        if rescan:
            self.model.update_file_status()

class DeleteBranch(Command):
    """Delete a git branch."""
    def __init__(self, branch):
        Command.__init__(self)
        self.branch = branch

    def do(self):
        status, output = self.model.delete_branch(self.branch)
        title = ''
        if output.startswith('error:'):
            output = 'E' + output[1:]
        else:
            title = 'Info: '
        _notifier.broadcast(signals.log_cmd, status, title + output)


class Diff(Command):
    """Perform a diff and set the model's current text."""
    def __init__(self, filenames, cached=False):
        Command.__init__(self)
        opts = {}
        if cached:
            cached = not self.model.read_only()
            opts = dict(ref=self.model.head)

        self.new_filename = filenames[0]
        self.old_filename = self.model.filename
        if not self.model.read_only():
            if self.model.mode != self.model.mode_amend:
                self.new_mode = self.model.mode_worktree
        self.new_diff_text = gitcmds.diff_helper(filename=self.new_filename,
                                                 cached=cached, **opts)


class DiffMode(HeadChangeCommand):
    """Enter diff mode and clear the model's diff text."""
    def __init__(self, treeish):
        HeadChangeCommand.__init__(self, treeish)
        self.new_mode = self.model.mode_diff


class DiffExprMode(HeadChangeCommand):
    """Enter diff-expr mode and clear the model's diff text."""
    def __init__(self, treeish):
        HeadChangeCommand.__init__(self, treeish)
        self.new_mode = self.model.mode_diff_expr


class Diffstat(Command):
    """Perform a diffstat and set the model's diff text."""
    def __init__(self):
        Command.__init__(self)
        diff = self.model.git.diff(self.model.head,
                                   unified=_config.get('diff.context', 3),
                                   no_color=True,
                                   M=True,
                                   stat=True)
        self.new_diff_text = core.decode(diff)
        self.new_mode = self.model.mode_worktree


class DiffStaged(Diff):
    """Perform a staged diff on a file."""
    def __init__(self, filenames):
        Diff.__init__(self, filenames, cached=True)
        if not self.model.read_only():
            if self.model.mode != self.model.mode_amend:
                self.new_mode = self.model.mode_index


class DiffStagedSummary(Command):
    def __init__(self):
        Command.__init__(self)
        cached = not self.model.read_only()
        diff = self.model.git.diff(self.model.head,
                                   cached=cached,
                                   no_color=True,
                                   patch_with_stat=True,
                                   M=True)
        self.new_diff_text = core.decode(diff)
        if not self.model.read_only():
            if self.model.mode != self.model.mode_amend:
                self.new_mode = self.model.mode_index


class Difftool(Command):
    """Run git-difftool limited by path."""
    def __init__(self, staged, filenames):
        Command.__init__(self)
        self.staged = staged
        self.filenames = filenames

    def do(self):
        if not self.filenames:
            return
        args = []
        if self.staged and not self.model.read_only():
            args.append('--cached')
        if self.model.head != 'HEAD':
            args.append(self.model.head)
        args.append('--')
        args.extend(self.filenames)
        difftool.launch(args)


class Edit(Command):
    """Edit a file using the configured gui.editor."""
    def __init__(self, filenames, line_number=None):
        Command.__init__(self)
        self.filenames = filenames
        self.line_number = line_number

    def do(self):
        filename = self.filenames[0]
        if not os.path.exists(filename):
            return
        editor = self.model.editor()
        if 'vi' in editor and self.line_number:
            utils.fork([editor, filename, '+'+self.line_number])
        else:
            utils.fork([editor, filename])


class FormatPatch(Command):
    """Output a patch series given all revisions and a selected subset."""
    def __init__(self, to_export, revs):
        Command.__init__(self)
        self.to_export = to_export
        self.revs = revs

    def do(self):
        status, output = gitcmds.format_patchsets(self.to_export, self.revs)
        _notifier.broadcast(signals.log_cmd, status, output)


class GrepMode(Command):
    def __init__(self, txt):
        """Perform a git-grep."""
        Command.__init__(self)
        self.new_mode = self.model.mode_grep
        self.new_diff_text = self.model.git.grep(txt, n=True)


class LoadCommitMessage(Command):
    """Loads a commit message from a path."""
    def __init__(self, path):
        Command.__init__(self)
        self.undoable = True
        self.path = path
        self.old_commitmsg = self.model.commitmsg
        self.old_directory = self.model.directory

    def do(self):
        path = self.path
        if not path or not os.path.isfile(path):
            raise errors.UsageError('Error: cannot find commit template',
                                    '%s: No such file or directory.' % path)
        self.model.set_directory(os.path.dirname(path))
        self.model.set_commitmsg(utils.slurp(path))

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)
        self.model.set_directory(self.old_directory)


class LoadCommitTemplate(LoadCommitMessage):
    """Loads the commit message template specified by commit.template."""
    def __init__(self):
        LoadCommitMessage.__init__(self, _config.get('commit.template'))

    def do(self):
        if self.path is None:
            raise errors.UsageError('Error: unconfigured commit template',
                    'A commit template has not been configured.\n'
                    'Use "git config" to define "commit.template"\n'
                    'so that it points to a commit template.')
        return LoadCommitMessage.do(self)


class Mergetool(Command):
    """Launch git-mergetool on a list of paths."""
    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        if not self.paths:
            return
        if version.check('mergetool-no-prompt',
                         self.model.git.version().split()[-1]):
            utils.fork(['git', 'mergetool', '--no-prompt', '--'] + self.paths)
        else:
            utils.fork(['xterm', '-e', 'git', 'mergetool', '--'] + self.paths)


class OpenRepo(Command):
    """Launches git-cola on a repo."""
    def __init__(self, dirname):
        Command.__init__(self)
        self.new_directory = utils.quote_repopath(dirname)

    def do(self):
        self.model.set_directory(self.new_directory)
        utils.fork([sys.executable, sys.argv[0], '--repo', self.new_directory])


class Clone(Command):
    """Clones a repository and optionally spawns a new cola session."""
    def __init__(self, url, destdir, spawn=True):
        Command.__init__(self)
        self.url = url
        self.new_directory = utils.quote_repopath(destdir)
        self.spawn = spawn

    def do(self):
        self.model.git.clone(self.url, self.new_directory,
                             with_stderr=True, with_status=True)
        if self.spawn:
            utils.fork(['python', sys.argv[0], '--repo', self.new_directory])


class Rescan(Command):
    """Rescans for changes."""
    def do(self):
        self.model.update_status(update_index=True)


class ReviewBranchMode(Command):
    """Enter into review-branch mode."""
    def __init__(self, branch):
        Command.__init__(self)
        self.new_mode = self.model.mode_review
        self.new_head = gitcmds.merge_base_parent(branch)
        self.new_diff_text = ''

    def do(self):
        Command.do(self)
        self.model.update_status()


class RunConfigAction(Command):
    """Run a user-configured action, typically from the "Tools" menu"""
    def __init__(self, name):
        Command.__init__(self)
        self.name = name
        self.model = cola.model()

    def do(self):
        for env in ('FILENAME', 'REVISION', 'ARGS'):
            try:
                del os.environ[env]
            except KeyError:
                pass
        rev = None
        args = None
        opts = _config.get_guitool_opts(self.name)
        cmd = opts.get('cmd')
        if 'title' not in opts:
            opts['title'] = cmd

        if 'prompt' not in opts or opts.get('prompt') is True:
            prompt = i18n.gettext('Are you sure you want to run %s?') % cmd
            opts['prompt'] = prompt

        if opts.get('needsfile'):
            filename = selection.filename()
            if not filename:
                _factory.prompt_user(signals.information,
                                     'Please select a file',
                                     '"%s" requires a selected file' % cmd)
                return
            os.environ['FILENAME'] = commands.mkarg(filename)


        if opts.get('revprompt') or opts.get('argprompt'):
            while True:
                ok = _factory.prompt_user(signals.run_config_action, cmd, opts)
                if not ok:
                    return
                rev = opts.get('revision')
                args = opts.get('args')
                if opts.get('revprompt') and not rev:
                    msg = ('Invalid revision:\n\n'
                           'Revision expression is empty')
                    title = 'Oops!'
                    _factory.prompt_user(signals.information, title, msg)
                    continue
                break

        elif opts.get('confirm'):
            title = os.path.expandvars(opts.get('title'))
            prompt = os.path.expandvars(opts.get('prompt'))
            if not _factory.prompt_user(signals.question, title, prompt):
                return
        if rev:
            os.environ['REVISION'] = rev
        if args:
            os.environ['ARGS'] = args
        title = os.path.expandvars(cmd)
        _notifier.broadcast(signals.log_cmd, 0, 'running: ' + title)
        cmd = ['sh', '-c', cmd]

        if opts.get('noconsole'):
            status, out, err = utils.run_command(cmd, flag_error=False)
        else:
            status, out, err = _factory.prompt_user(signals.run_command,
                                                    title, cmd)

        _notifier.broadcast(signals.log_cmd, status,
                            'stdout: %s\nstatus: %s\nstderr: %s' %
                                (out.rstrip(), status, err.rstrip()))

        if not opts.get('norescan'):
            self.model.update_status()
        return status


class ShowUntracked(Command):
    """Show an untracked file."""
    # We don't actually do anything other than set the mode right now.
    # TODO check the mimetype for the file and handle things
    # generically.
    def __init__(self, filenames):
        Command.__init__(self)
        self.new_mode = self.model.mode_worktree
        # TODO new_diff_text = utils.file_preview(filenames[0])


class Stage(Command):
    """Stage a set of paths."""
    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        msg = 'Staging: %s' % (', '.join(self.paths))
        _notifier.broadcast(signals.log_cmd, 0, msg)
        self.model.stage_paths(self.paths)


class StageModified(Stage):
    """Stage all modified files."""
    def __init__(self):
        Stage.__init__(self, None)
        self.paths = self.model.modified


class StageUntracked(Stage):
    """Stage all untracked files."""
    def __init__(self):
        Stage.__init__(self, None)
        self.paths = self.model.untracked

class Tag(Command):
    """Create a tag object."""
    def __init__(self, name, revision, sign=False, message=''):
        Command.__init__(self)
        self._name = name
        self._message = core.encode(message)
        self._revision = revision
        self._sign = sign

    def do(self):
        log_msg = 'Tagging: "%s" as "%s"' % (self._revision, self._name)
        opts = {}
        if self._message:
            opts['F'] = self.model.tmp_filename()
            utils.write(opts['F'], self._message)

        if self._sign:
            log_msg += ', GPG-signed'
            opts['s'] = True
            status, output = self.model.git.tag(self._name,
                                                self._revision,
                                                with_status=True,
                                                with_stderr=True,
                                                **opts)
        else:
            opts['a'] = bool(self._message)
            status, output = self.model.git.tag(self._name,
                                                self._revision,
                                                with_status=True,
                                                with_stderr=True,
                                                **opts)
        if 'F' in opts:
            os.unlink(opts['F'])

        if output:
            log_msg += '\nOutput:\n%s' % output

        _notifier.broadcast(signals.log_cmd, status, log_msg)
        if status == 0:
            self.model.update_status()


class Unstage(Command):
    """Unstage a set of paths."""
    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        msg = 'Unstaging: %s' % (', '.join(self.paths))
        _notifier.broadcast(signals.log_cmd, 0, msg)
        self.model.unstage_paths(self.paths)


class UnstageAll(Command):
    """Unstage all files; resets the index."""
    def do(self):
        self.model.unstage_all()


class UnstageSelected(Unstage):
    """Unstage selected files."""
    def __init__(self):
        Unstage.__init__(self, cola.selection_model().staged)


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
                io.write('/'+core.encode(u))
        self.new_diff_text = core.decode(io.getvalue())


class VisualizeAll(Command):
    """Visualize all branches."""
    def do(self):
        browser = self.model.history_browser()
        utils.fork([browser, '--all'])


class VisualizeCurrent(Command):
    """Visualize all branches."""
    def do(self):
        browser = self.model.history_browser()
        utils.fork([browser, self.model.currentbranch])


class VisualizePaths(Command):
    """Path-limited visualization."""
    def __init__(self, paths):
        Command.__init__(self)
        browser = self.model.history_browser()
        if paths:
            self.argv = [browser] + paths
        else:
            self.argv = [browser]

    def do(self):
        utils.fork(self.argv)


def register():
    """
    Register signal mappings with the factory.

    These commands are automatically created and run when
    their corresponding signal is broadcast by the notifier.

    """
    signal_to_command_map = {
        signals.amend_mode: AmendMode,
        signals.apply_diff_selection: ApplyDiffSelection,
        signals.apply_patches: ApplyPatches,
        signals.branch_mode: BranchMode,
        signals.clone: Clone,
        signals.checkout: Checkout,
        signals.checkout_branch: CheckoutBranch,
        signals.cherry_pick: CherryPick,
        signals.commit: Commit,
        signals.delete: Delete,
        signals.delete_branch: DeleteBranch,
        signals.diff: Diff,
        signals.diff_mode: DiffMode,
        signals.diff_expr_mode: DiffExprMode,
        signals.diff_staged: DiffStaged,
        signals.diffstat: Diffstat,
        signals.difftool: Difftool,
        signals.edit: Edit,
        signals.format_patch: FormatPatch,
        signals.grep: GrepMode,
        signals.ignore: Ignore,
        signals.load_commit_message: LoadCommitMessage,
        signals.load_commit_template: LoadCommitTemplate,
        signals.modified_summary: Diffstat,
        signals.mergetool: Mergetool,
        signals.open_repo: OpenRepo,
        signals.rescan: Rescan,
        signals.reset_mode: ResetMode,
        signals.review_branch_mode: ReviewBranchMode,
        signals.run_config_action: RunConfigAction,
        signals.show_untracked: ShowUntracked,
        signals.stage: Stage,
        signals.stage_modified: StageModified,
        signals.stage_untracked: StageUntracked,
        signals.staged_summary: DiffStagedSummary,
        signals.tag: Tag,
        signals.unstage: Unstage,
        signals.unstage_all: UnstageAll,
        signals.unstage_selected: UnstageSelected,
        signals.untracked_summary: UntrackedSummary,
        signals.visualize_all: VisualizeAll,
        signals.visualize_current: VisualizeCurrent,
        signals.visualize_paths: VisualizePaths,
    }

    for signal, cmd in signal_to_command_map.iteritems():
        _factory.add_command(signal, cmd)
