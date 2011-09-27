import cola
from cola import git
from cola import observable


class StashModel(observable.Observable):
    def __init__(self):
        observable.Observable.__init__(self)
        self.git = git.instance()

    def stash_list(self):
        return self.git.stash('list').splitlines()

    def has_stashable_changes(self):
        model = cola.model()
        return bool(model.modified + model.staged)

    def stash_info(self, revids=False, names=False):
        """Parses "git stash list" and returns a list of stashes."""
        stashes = self.stash_list()
        revids = [s[:s.index(':')] for s in stashes]
        names = [s.split(': ', 2)[-1] for s in stashes]

        return stashes, revids, names

    def stash_diff(self, rev):
        diffstat = self.git.stash('show', rev)
        diff = self.git.stash('show', '-p', rev)
        return diffstat + '\n\n' + diff
