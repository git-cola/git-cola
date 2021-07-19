from __future__ import absolute_import, division, print_function, unicode_literals

from .. import cmds
from .. import core
from .. import observable
from .. import gitcmds
from .. import utils
from ..i18n import N_
from ..git import STDOUT
from ..interaction import Interaction


class StashModel(observable.Observable):
    def __init__(self, context):
        observable.Observable.__init__(self)
        self.context = context
        self.git = context.git
        self.model = model = context.model
        if not model.initialized:
            model.update_status()

    def stash_list(self, *args):
        return self.git.stash('list', *args)[STDOUT].splitlines()

    def is_staged(self):
        return bool(self.model.staged)

    def is_changed(self):
        model = self.model
        return bool(model.modified or model.staged)

    def stash_info(self, revids=False, names=False):
        """Parses "git stash list" and returns a list of stashes."""
        stashes = self.stash_list(r'--format=%gd/%aD/%s')
        split_stashes = [s.split('/', 3) for s in stashes if s]
        stashes = ['{0}: {1}'.format(s[0], s[2]) for s in split_stashes]
        revids = [s[0] for s in split_stashes]
        author_dates = [s[1] for s in split_stashes]
        names = [s[2] for s in split_stashes]

        return stashes, revids, author_dates, names

    def stash_diff(self, rev):
        git = self.git
        diffstat = git.stash('show', rev)[STDOUT]
        diff = git.stash('show', '-p', '--no-ext-diff', rev)[STDOUT]
        return diffstat + '\n\n' + diff


class ApplyStash(cmds.ContextCommand):
    def __init__(self, context, stash_index, index, pop):
        super(ApplyStash, self).__init__(context)
        self.stash_ref = 'refs/' + stash_index
        self.index = index
        self.pop = pop

    def do(self):
        ref = self.stash_ref
        pop = self.pop
        if pop:
            action = 'pop'
        else:
            action = 'apply'
        if self.index:
            args = [action, '--index', ref]
        else:
            args = [action, ref]
        status, out, err = self.git.stash(*args)
        if status == 0:
            Interaction.log_status(status, out, err)
        else:
            title = N_('Error')
            cmdargs = core.list2cmdline(args)
            Interaction.command_error(title, 'git stash ' + cmdargs, status, out, err)
        self.model.update_status()


class DropStash(cmds.ContextCommand):
    def __init__(self, context, stash_index):
        super(DropStash, self).__init__(context)
        self.stash_ref = 'refs/' + stash_index

    def do(self):
        git = self.git
        status, out, err = git.stash('drop', self.stash_ref)
        if status == 0:
            Interaction.log_status(status, out, err)
        else:
            title = N_('Error')
            Interaction.command_error(
                title, 'git stash drop ' + self.stash_ref, status, out, err
            )


class SaveStash(cmds.ContextCommand):
    def __init__(self, context, stash_name, keep_index):
        super(SaveStash, self).__init__(context)
        self.stash_name = stash_name
        self.keep_index = keep_index

    def do(self):
        if self.keep_index:
            args = ['save', '--keep-index', self.stash_name]
        else:
            args = ['save', self.stash_name]
        status, out, err = self.git.stash(*args)
        if status == 0:
            Interaction.log_status(status, out, err)
        else:
            title = N_('Error')
            cmdargs = core.list2cmdline(args)
            Interaction.command_error(title, 'git stash ' + cmdargs, status, out, err)

        self.model.update_status()


class StashIndex(cmds.ContextCommand):
    """Stash the index away"""

    def __init__(self, context, stash_name):
        super(StashIndex, self).__init__(context)
        self.stash_name = stash_name

    def do(self):
        # Manually create a stash representing the index state
        context = self.context
        git = self.git
        name = self.stash_name
        branch = gitcmds.current_branch(context)
        head = gitcmds.rev_parse(context, 'HEAD')
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
            '-m', 'index on %s: %s' % (branch, head_msg), '-p', head, index_tree
        )
        if status != 0:
            stash_error('commit-tree', status, out, err)
            return
        index_commit = out.strip()

        # Create a commit representing the worktree
        status, out, err = git.commit_tree(
            '-p', head, '-p', index_commit, '-m', message, index_tree
        )
        if status != 0:
            stash_error('commit-tree', status, out, err)
            return
        worktree_commit = out.strip()

        # Record the stash entry
        status, out, err = git.update_ref(
            '-m', message, 'refs/stash', worktree_commit, create_reflog=True
        )
        if status != 0:
            stash_error('update-ref', status, out, err)
            return

        # Sync the worktree with the post-stash state.  We've created the
        # stash ref, so now we have to remove the staged changes from the
        # worktree.  We do this by applying a reverse diff of the staged
        # changes.  The diff from stash->HEAD is a reverse diff of the stash.
        patch = utils.tmp_filename('stash')
        with core.xopen(patch, mode='wb') as patch_fd:
            status, out, err = git.diff_tree(
                'refs/stash', 'HEAD', '--', binary=True, _stdout=patch_fd
            )
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

        self.model.update_status()


def stash_error(cmd, status, out, err):
    title = N_('Error creating stash')
    Interaction.command_error(title, cmd, status, out, err)
