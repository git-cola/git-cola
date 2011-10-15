import cola
from cola import observable
from cola import signals
from cola.git import git
from cola.cmds import BaseCommand


class StashModel(observable.Observable):
    def __init__(self):
        observable.Observable.__init__(self)

    def stash_list(self):
        return git.stash('list').splitlines()

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
        diffstat = git.stash('show', rev)
        diff = git.stash('show', '-p', rev)
        return diffstat + '\n\n' + diff


class ApplyStash(BaseCommand):
    command = 'apply_stash'
    def __init__(self, selection, index):
        BaseCommand.__init__(self)
        self.selection = selection
        self.index = index

    def do(self):
        if self.index:
            args = ['apply', '--index', self.selection]
        else:
            args = ['apply', self.selection]
        status, output = git.stash(with_stderr=True, with_status=True, *args)
        cola.notifier().broadcast(signals.log_cmd, status, output)


command_directory = {
    ApplyStash.command: ApplyStash,
}
