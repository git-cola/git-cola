import os
import sys
from cStringIO import StringIO

import cola
from cola import core
from cola import utils
from cola import signals
from cola import cmdfactory

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


class AmendMode(Command):
    """Try to amend a commit."""
    def __init__(self, amend):
        Command.__init__(self)
        self.skip = False
        self.amending = amend
        self.old_mode = self.model.mode
        self.old_head = self.model.head
        self.old_msg = self.model.commitmsg
        self.msg = ''

        if self.amending:
            return
        # If we're going back into new-commit-mode then search the
        # undo stack for a previous amend-commid-mode and grab the
        # commit message at that point in time.
        factory = cmdfactory.factory()
        if not factory.undostack:
            return
        undo_count = len(factory.undostack)
        for i in xrange(undo_count):
            idx = undo_count - i - 1
            cmdobj = factory.undostack[idx]
            if type(cmdobj) is not AmendMode:
                continue
            if cmdobj.amending:
                self.msg = cmdobj.old_msg
            break
    
    def do(self):
        """Leave/enter amend mode."""
        if self.amending:
            self.enter_amend_mode()
        else:
            self.enter_new_commit_mode()

    def enter_amend_mode(self):
        """Attempt to enter amend mode.  Do not allow this when merging."""
        if os.path.exists(self.model.git_repo_path('MERGE_HEAD')):
            self.skip = True
            cola.notifier().broadcast(signals.amend, False)
            cola.notifier().broadcast(signals.information,
                                      'Oops! Unmerged',
                                      'You are in the middle of a merge.\n'
                                      'You cannot amend while merging.')
        else:
            self.skip = False
            cola.notifier().broadcast(signals.amend, True)
            self.model.set_head('HEAD^')
            self.model.set_mode(self.model.mode_amend)
            self.model.set_commitmsg(self.model.prev_commitmsg())
            self.model.update_status()

    def enter_new_commit_mode(self):
        """Switch back to new-commit mode."""
        cola.notifier().broadcast(signals.amend, False)
        self.model.set_head('HEAD')
        self.model.set_mode(self.model.mode_none)
        self.model.set_commitmsg(self.msg)
        self.model.update_status()

    def undo(self):
        if self.skip:
            return
        self.model.set_head(self.old_head)
        self.model.set_mode(self.old_mode)
        self.model.set_commitmsg(self.old_text)
        self.model.update_status()


class Diff(Command):
    """Perform a diff and set the model's current text."""
    def __init__(self, filenames):
        Command.__init__(self)
        self.filenames = filenames 
        self.old_mode = self.model.mode
        self.old_text = self.model.current_text

    def do(self):
        if not self.filenames:
            return
        self.model.set_mode(self.model.mode_worktree)
        filename = self.filenames[0]
        diff = self.model.diff_helper(filename=filename,
                                      ref=self.model.head,
                                      cached=False)
        self.model.set_current_text(diff)

    def undo(self):
        self.model.set_mode(self.old_mode)
        self.model.set_current_text(self.old_text)


class Diffstat(Command):
    """Perform a diffstat and set the model's current text."""
    def __init__(self):
        Command.__init__(self)
        self.old_text = self.model.current_text

    def do(self):
        self.model.set_current_text(self.model.diffstat())

    def undo(self):
        self.model.set_current_text(self.old_text)


class ResetMode(Command):
    def __init__(self, model=None):
        Command.__init__(self, model=model)
        self.old_mode = self.model.mode
        self.old_text = self.model.current_text

    def do(self):
        self.model.set_mode(self.model.mode_none)
        self.model.set_current_text('')

    def undo(self):
        self.model.set_mode(self.old_mode)
        self.model.set_current_text(self.old_text)


def register():
    """
    Register signal mappings with the factory.

    These commands are automatically created and run when
    their corresponding signal is broadcast by the notifier.

    """
    signal_to_command_map = {
        signals.amend_mode: AmendMode,
        signals.diff: Diff,
        signals.diffstat: Diffstat,
        signals.modified_summary: Diffstat,
        signals.reset_mode: ResetMode,
    }

    factory = cmdfactory.factory()
    for signal, cmd in signal_to_command_map.iteritems():
        factory.add_command(signal, cmd)
