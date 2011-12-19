import cola
from cola import gitcmds
from cola import observable
from cola import signals
from cola.cmds import BaseCommand, VisualizeRevision, visualize_revision


class MergeModel(observable.Observable):
    message_updated = 'updated'

    def __init__(self):
        observable.Observable.__init__(self)
        self.model = cola.model()
        # Relay the "updated" message
        msg = self.model.message_updated
        self.model.add_observer(msg, self.notify_updated)

    def notify_updated(self):
        self.notify_observers(self.message_updated)

    def update_status(self):
        self.model.update_status()

    def current_branch(self):
        return self.model.currentbranch

    def local_branches(self):
        return self.model.local_branches

    def remote_branches(self):
        return self.model.remote_branches

    def tags(self):
        return self.model.tags

    def merge(self, revision, no_commit, squash):
        msg = gitcmds.merge_message(revision)
        status, output = self.model.git.merge('-m'+msg,
                                              revision,
                                              no_commit=no_commit,
                                              squash=squash,
                                              with_stderr=True,
                                              with_status=True)
        return status, output


# Merge command
merge = 'merge'

class Merge(BaseCommand):
    def __init__(self, revision, no_commit, squash):
        BaseCommand.__init__(self)
        self.revision = revision
        self.no_commit = no_commit
        self.squash = squash

    def do(self):
        squash = self.squash
        revision = self.revision
        no_commit = self.no_commit
        status, output = self.context.merge(revision, no_commit, squash)
        notifier = cola.notifier()
        notifier.broadcast(signals.log_cmd, status, output)
        self.context.update_status()


command_directory = {
    merge: Merge,
    visualize_revision: VisualizeRevision,
}
