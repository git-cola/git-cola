from __future__ import division, absolute_import, unicode_literals

from cola import observable
from cola.git import git
from cola.git import STDOUT
from cola.interaction import Interaction
from cola.models import main


class StashModel(observable.Observable):
    def __init__(self):
        observable.Observable.__init__(self)

    def stash_list(self):
        return git.stash('list')[STDOUT].splitlines()

    def has_stashable_changes(self):
        model = main.model()
        return bool(model.modified + model.staged)

    def stash_info(self, revids=False, names=False):
        """Parses "git stash list" and returns a list of stashes."""
        stashes = self.stash_list()
        revids = [s[:s.index(':')] for s in stashes]
        names = [s.split(': ', 2)[-1] for s in stashes]

        return stashes, revids, names

    def stash_diff(self, rev):
        diffstat = git.stash('show', rev)[STDOUT]
        diff = git.stash('show', '-p', '--no-ext-diff', rev)[STDOUT]
        return diffstat + '\n\n' + diff


class ApplyStash(object):
    def __init__(self, selection, index):
        self.selection = selection
        self.index = index

    def is_undoable(self):
        return False

    def do(self):
        if self.index:
            args = ['apply', '--index', self.selection]
        else:
            args = ['apply', self.selection]
        status, out, err = git.stash(*args)
        Interaction.log_status(status, out, err)


class DropStash(object):
    def __init__(self, stash_sha1):
        self.stash_sha1 = stash_sha1

    def is_undoable(self):
        return False

    def do(self):
        status, out, err = git.stash('drop', self.stash_sha1)
        Interaction.log_status(status, out, err)


class SaveStash(object):

    def __init__(self, stash_name, keep_index):
        self.stash_name = stash_name
        self.keep_index = keep_index

    def is_undoable(self):
        return False

    def do(self):
        if self.keep_index:
            args = ['save', '--keep-index', self.stash_name]
        else:
            args = ['save', self.stash_name]
        status, out, err = git.stash(*args)
        Interaction.log_status(status, out, err)
