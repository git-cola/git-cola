import os
import sys
from cStringIO import StringIO

import cola
from cola import core
from cola import utils
from cola import signals
from cola import cmdfactory
from cola.diffparse import DiffParser

_notifier = cola.notifier()
_factory = cmdfactory.factory()

class Command(object):
    """Base class for all commands; provides the command pattern."""
    def __init__(self, update=False):
        """Initialize the command and stash away values for use in do()"""
        # These are commonly used so let's make it easier to write new commands.
        self.model = cola.model()
        self.update = update

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
        if self.update:
            self.model.update_status()

    def is_undoable(self):
        """Can this be undone?"""
        return True

    def undo(self):
        """Undo the operation."""
        self.model.set_diff_text(self.old_diff_text)
        self.model.set_filename(self.old_filename)
        self.model.set_head(self.old_head)
        self.model.set_mode(self.old_mode)
        if self.update:
            self.model.update_status()

    def name(self):
        """Return this command's name."""
        return self.__class__.__name__

class AddSignoff(Command):
    """Add a signed-off-by to the commit message."""
    def __init__(self):
        Command.__init__(self)
        self.old_commitmsg = self.model.commitmsg
        self.new_commitmsg = self.old_commitmsg
        signoff = ('\nSigned-off-by: %s <%s>\n' %
                    (self.model.local_user_name, self.model.local_user_email))
        if signoff not in self.new_commitmsg:
            self.new_commitmsg += ('\n' + signoff)

    def do(self):
        self.model.set_commitmsg(self.new_commitmsg)

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)


class AmendMode(Command):
    """Try to amend a commit."""
    def __init__(self, amend):
        Command.__init__(self, update=True)
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
        # undo stack for a previous amend-commid-mode and grab the
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
            if os.path.exists(self.model.git_repo_path('MERGE_HEAD')):
                self.skip = True
                _notifier.broadcast(signals.amend, False)
                _notifier.broadcast(signals.information,
                                    'Oops! Unmerged',
                                    'You are in the middle of a merge.\n'
                                    'You cannot amend while merging.')
                return
        self.skip = False
        _notifier.broadcast(signals.amend, self.amending)
        self.model.set_commitmsg(self.new_commitmsg)
        Command.do(self)

    def undo(self):
        if self.skip:
            return
        self.model.set_commitmsg(self.old_commitmsg)
        Command.undo(self)

class ApplyDiffSelection(Command):
    def __init__(self, staged, selected, offset, selection, apply_to_worktree):
        Command.__init__(self, update=True)
        self.staged = staged
        self.selected = selected
        self.offset = offset
        self.selection = selection
        self.apply_to_worktree = apply_to_worktree

    def is_undoable(self):
        return False

    def do(self):
        if self.model.mode == self.model.mode_branch:
            # We're applying changes from a different branch!
            parser = DiffParser(self.model,
                                filename=self.model.filename,
                                cached=False,
                                branch=self.model.head)
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
            parser.process_diff_selection(self.selected,
                                          self.offset,
                                          self.selection,
                                          apply_to_worktree=
                                          self.apply_to_worktree)


class HeadChangeCommand(Command):
    """Changes the model's current head."""
    def __init__(self, treeish):
        Command.__init__(self, update=True)
        self.new_head = treeish
        self.new_diff_text = ''


class BranchMode(HeadChangeCommand):
    """Enter into diff-branch mode."""
    def __init__(self, treeish, filename):
        HeadChangeCommand.__init__(self, treeish)
        self.old_filename = self.model.filename
        self.new_filename = filename
        self.new_mode = self.model.mode_branch
        self.new_diff_text = self.model.diff_helper(filename=filename,
                                                    cached=False,
                                                    reverse=True,
                                                    branch=treeish)

class Commit(Command):
    """Attempt to create a new commit."""
    def __init__(self, amend, msg):
        Command.__init__(self)
        self.amend = amend
        self.msg = core.encode(msg)
        self.old_commitmsg = self.model.commitmsg
        self.new_mode = self.model.mode_none
        self.new_commitmsg = ''

    def do(self):
        status, output = self.model.commit_with_msg(self.msg, amend=self.amend)
        if status == 0:
            self.model.set_mode(self.new_mode)
            self.model.set_commitmsg(self.new_commitmsg)
            self.model.update_status()
            _notifier.broadcast(signals.amend, False)

    def is_undoable(self):
        return False


class Delete(Command):
    """Simply delete files."""
    def __init__(self, filenames):
        Command.__init__(self)
        self.filenames = filenames

    def is_undoable(self):
        # We could git-hash-object stuff and provide undo-ability
        # as an option.  Heh.
        return False

    def do(self):
        rescan = False
        for filename in self.filenames:
            if filename:
                try:
                    os.remove(filename)
                    rescan=True
                except:
                    _notifier.broadcast(signals.information,
                                        'Error'
                                        'Deleting "%s" failed.' % filename)
        if rescan:
            self.model.update_status()


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
            self.new_mode = self.model.mode_worktree
        self.new_diff_text = self.model.diff_helper(filename=self.new_filename,
                                                    cached=cached, **opts)

    def do(self):
        self.model.set_filename(self.new_filename)
        Command.do(self)

    def undo(self):
        self.model.set_filename(self.old_filename)
        Command.undo(self)


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
                                   unified=self.model.diff_context,
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

    def is_undoable(self):
        return False


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
        self.path = path
        self.old_commitmsg = self.model.commitmsg
        self.old_directory = self.model.directory

    def do(self):
        self.model.set_directory(os.path.dirname(self.path))
        fh = open(self.path, 'r')
        contents = core.decode(core.read_nointr(fh))
        fh.close()
        self.model.set_commitmsg(contents)

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)
        self.model.set_directory(self.old_directory)


class OpenRepo(Command):
    """Launches git-cola on a repo."""
    def __init__(self, dirname):
        Command.__init__(self)
        self.new_directory = utils.quote_repopath(dirname)

    def do(self):
        self.model.set_directory(self.new_directory)
        utils.fork(['python', sys.argv[0], '--repo', self.new_directory])

    def is_undoable(self):
        return False


class Clone(Command):
    """Clones a repository and launches a new cola session."""
    def __init__(self, url, destdir):
        Command.__init__(self)
        self.url = url
        self.new_directory = utils.quote_repopath(destdir)

    def is_undoable(self):
        return False

    def do(self):
        self.model.git.clone(self.url, self.new_directory,
                             with_stderr=True, with_status=True)
        utils.fork(['python', sys.argv[0], '--repo', self.new_directory])


class Rescan(Command):
    """Rescans for changes."""
    def __init__(self):
        Command.__init__(self, update=True)


class ResetMode(Command):
    """Reset the mode and clear the model's diff text."""
    def __init__(self):
        Command.__init__(self, update=True)
        self.new_mode = self.model.mode_none
        self.new_head = 'HEAD'
        self.new_diff_text = ''


class ReviewBranchMode(Command):
    """Enter into review-branch mode."""
    def __init__(self, branch):
        Command.__init__(self, update=True)
        self.new_mode = self.model.mode_review
        self.new_head = self.model.merge_base_to(branch)
        self.new_diff_text = ''


class ShowUntracked(Command):
    """Show an untracked file."""
    # We don't actually do anything other than set the mode right now.
    # We could probably check the mimetype for the file and handle things
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
        self.model.stage_paths(self.paths)

    def is_undoable(self):
        return False


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


class Unstage(Command):
    """Unstage a set of paths."""
    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        self.model.unstage_paths(self.paths)

    def is_undoable(self):
        return False


class UnstageAll(Command):
    """Unstage all files; resets the index."""
    def __init__(self):
        Command.__init__(self, update=True)

    def is_undoable(self):
        return False

    def do(self):
        self.model.unstage_all()


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
                io.write('/%s\n' % u)
        self.new_diff_text = io.getvalue()


class VisualizeAll(Command):
    """Visualize all branches."""
    def is_undoable(self):
        return False

    def do(self):
        browser = self.model.history_browser()
        utils.fork(['sh', '-c', browser, '--all'])


class VisualizeCurrent(Command):
    """Visualize all branches."""
    def is_undoable(self):
        return False

    def do(self):
        browser = self.model.history_browser()
        utils.fork(['sh', '-c', browser, self.model.currentbranch])


def register():
    """
    Register signal mappings with the factory.

    These commands are automatically created and run when
    their corresponding signal is broadcast by the notifier.

    """
    signal_to_command_map = {
        signals.add_signoff: AddSignoff,
        signals.apply_diff_selection: ApplyDiffSelection,
        signals.amend_mode: AmendMode,
        signals.branch_mode: BranchMode,
        signals.clone: Clone,
        signals.commit: Commit,
        signals.delete: Delete,
        signals.diff: Diff,
        signals.diff_mode: DiffMode,
        signals.diff_expr_mode: DiffExprMode,
        signals.diff_staged: DiffStaged,
        signals.diffstat: Diffstat,
        signals.edit: Edit,
        signals.grep: GrepMode,
        signals.modified_summary: Diffstat,
        signals.open_repo: OpenRepo,
        signals.rescan: Rescan,
        signals.reset_mode: ResetMode,
        signals.review_branch_mode: ReviewBranchMode,
        signals.show_untracked: ShowUntracked,
        signals.stage: Stage,
        signals.stage_modified: StageModified,
        signals.stage_untracked: StageUntracked,
        signals.staged_summary: DiffStagedSummary,
        signals.unstage: Unstage,
        signals.unstage_all: UnstageAll,
        signals.untracked_summary: UntrackedSummary,
        signals.visualize_all: VisualizeAll,
        signals.visualize_current: VisualizeCurrent,
    }

    for signal, cmd in signal_to_command_map.iteritems():
        _factory.add_command(signal, cmd)
