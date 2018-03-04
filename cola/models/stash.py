from __future__ import division, absolute_import, unicode_literals

from .. import core
from .. import observable
from .. import gitcmds
from .. import utils
from ..i18n import N_
from ..git import git
from ..git import STDOUT
from ..interaction import Interaction
from ..models import main


class StashModel(observable.Observable):

    def __init__(self):
        observable.Observable.__init__(self)
        self.model = model = main.model()
        if not model.initialized:
            model.update_status()

    def stash_list(self):
        return git.stash('list')[STDOUT].splitlines()

    def is_staged(self):
        return bool(self.model.staged)

    def is_changed(self):
        model = self.model
        return bool(model.modified or model.staged)

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


class CommandMixin(object):

    def is_undoable(self):
        return False


class ApplyStash(CommandMixin):

    def __init__(self, stash_name, index):
        self.stash_ref = stash_name
        self.index = index

    def do(self):
        ref = self.stash_ref
        if self.index:
            args = ['apply', '--index', ref]
        else:
            args = ['apply', ref]
        status, out, err = git.stash(*args)
        if status == 0:
            Interaction.log_status(status, out, err)
        else:
            title = N_('Error')
            Interaction.command_error(
                title, 'git stash apply ' + ref, status, out, err)


class DropStash(CommandMixin):

    def __init__(self, stash_oid):
        self.stash_oid = stash_oid

    def do(self):
        ref = 'refs/' + self.stash_oid
        status, out, err = git.stash('drop', self.stash_oid)
        if status != 0:
            pass
        else:
            Interaction.log_status(status, out, err)


class SaveStash(CommandMixin):

    def __init__(self, stash_name, keep_index):
        self.stash_name = stash_name
        self.keep_index = keep_index

    def do(self):
        if self.keep_index:
            args = ['save', '--keep-index', self.stash_name]
        else:
            args = ['save', self.stash_name]
        status, out, err = git.stash(*args)
        Interaction.log_status(status, out, err)


class StashIndex(CommandMixin):
    """Stash the index away"""

    def __init__(self, stash_name):
        self.stash_name = stash_name

    def do(self):
        # Manually create a stash representing the index state
        name = self.stash_name
        branch = gitcmds.current_branch()
        head = gitcmds.rev_parse('HEAD')
        message = 'On %s: %s' % (branch, name)

        # Get the message used for the "index" commit
        status, out, err = git.rev_list('HEAD', '--', oneline=True, n=1)
        if status != 0:
            stash_error('rev-list', status, out, err)
            return
        head_msg = out.strip()

        # Create a commit representing the index
        status, out, err = git.write_tree()
        if status != 0:
            stash_error('write-tree', status, out, err)
            return
        index_tree = out.strip()

        status, out, err = git.commit_tree(
            '-m', 'index on %s: %s' % (branch, head_msg),
            '-p', head,
            index_tree)
        if status != 0:
            stash_error('commit-tree', status, out, err)
            return
        index_commit = out.strip()

        # Create a commit representing the worktree
        status, out, err = git.commit_tree(
            '-p', head, '-p', index_commit,
            '-m', message,
            index_tree)
        if status != 0:
            stash_error('commit-tree', status, out, err)
            return
        worktree_commit = out.strip()

        # Record the stash entry
        status, out, err = git.update_ref(
            '-m', message, 'refs/stash', worktree_commit, create_reflog=True)
        if status != 0:
            stash_error('update-ref', status, out, err)
            return

        # Sync the worktree with the post-stash state.  We've created the
        # stash ref, so now we have to remove the staged changes from the
        # worktree.  We do this by applying a reverse diff of the staged
        # changes.  The diff from stash->HEAD is a reverse diff of the stash.
        patch = utils.tmp_filename('stash')
        with core.xopen(patch, mode='wb') as patch_fd:
            status, out, err = git.diff_tree('refs/stash', 'HEAD', '--',
                binary=True, _stdout=patch_fd)
            if status != 0:
                stash_error('diff-tree', status, out, err)
                return

        # Apply the patch
        status, out, err = git.apply(patch)
        core.unlink(patch)
        ok = status == 0
        if ok:
            # Finally, clear the index we just stashed
            git.reset()
        else:
            stash_error('apply', status, out, err)


def stash_error(cmd, status, out, err):
    title = N_('Error creating stash')
    Interaction.command_error(title, cmd, status, out, err)
