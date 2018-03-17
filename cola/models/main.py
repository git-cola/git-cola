# Copyright (C) 2007-2018 David Aguilar
"""This module provides the central cola model.
"""
from __future__ import division, absolute_import, unicode_literals

import os

from .. import core
from .. import git
from .. import gitcmds
from .. import gitcfg
from ..compat import ustr
from ..decorators import memoize
from ..git import STDOUT
from ..interaction import Interaction
from ..i18n import N_
from ..models import prefs
from ..models.selection import selection_model
from ..observable import Observable


@memoize
def model():
    """Returns the main model singleton"""
    return MainModel()


class MainModel(Observable):
    """Repository status model"""
    # TODO this class can probably be split apart into a DiffModel,
    # CommitMessageModel, StatusModel, and an AppStatusStateMachine.

    # Observable messages
    message_about_to_update = 'about_to_update'
    message_commit_message_changed = 'commit_message_changed'
    message_diff_text_changed = 'diff_text_changed'
    message_diff_type_changed = 'diff_type_changed'
    message_filename_changed = 'filename_changed'
    message_images_changed = 'images_changed'
    message_mode_about_to_change = 'mode_about_to_change'
    message_mode_changed = 'mode_changed'
    message_updated = 'updated'

    # States
    mode_none = 'none'  # Default: nothing's happened, do nothing
    mode_worktree = 'worktree'  # Comparing index to worktree
    mode_diffstat = 'diffstat'  # Showing a diffstat
    mode_untracked = 'untracked'  # Dealing with an untracked file
    mode_index = 'index'  # Comparing index to last commit
    mode_amend = 'amend'  # Amending a commit

    # Modes where we can checkout files from the $head
    modes_undoable = set((mode_amend, mode_index, mode_worktree))

    # Modes where we can partially stage files
    modes_stageable = set((mode_amend, mode_worktree, mode_untracked))

    # Modes where we can partially unstage files
    modes_unstageable = set((mode_amend, mode_index))

    unstaged = property(
            lambda self: self.modified + self.unmerged + self.untracked)
    """An aggregate of the modified, unmerged, and untracked file lists."""

    def __init__(self, cwd=None):
        """Reads git repository settings and sets several methods
        so that they refer to the git module.  This object
        encapsulates cola's interaction with git."""
        Observable.__init__(self)

        # Initialize the git command object
        self.git = git.current()
        self.cfg = gitcfg.current()

        self.initialized = False
        self.annex = False
        self.lfs = False
        self.head = 'HEAD'
        self.diff_text = ''
        self.diff_type = 'text'  # text, image
        self.mode = self.mode_none
        self.filename = None
        self.is_merging = False
        self.is_rebasing = False
        self.currentbranch = ''
        self.directory = ''
        self.project = ''
        self.remotes = []
        self.filter_paths = None
        self.images = []

        self.commitmsg = ''  # current commit message
        self._auto_commitmsg = ''  # e.g. .git/MERGE_MSG
        self._prev_commitmsg = ''  # saved here when clobbered by .git/MERGE_MSG

        self.modified = []  # modified, staged, untracked, unmerged paths
        self.staged = []
        self.untracked = []
        self.unmerged = []
        self.upstream_changed = []  # paths that've changed upstream
        self.staged_deleted = set()
        self.unstaged_deleted = set()
        self.submodules = set()

        self.local_branches = []
        self.remote_branches = []
        self.tags = []
        if cwd:
            self.set_worktree(cwd)

    def unstageable(self):
        return self.mode in self.modes_unstageable

    def amending(self):
        return self.mode == self.mode_amend

    def undoable(self):
        """Whether we can checkout files from the $head."""
        return self.mode in self.modes_undoable

    def stageable(self):
        """Whether staging should be allowed."""
        return self.mode in self.modes_stageable

    def all_branches(self):
        return (self.local_branches + self.remote_branches)

    def set_worktree(self, worktree):
        self.git.set_worktree(worktree)
        is_valid = self.git.is_valid()
        if is_valid:
            cwd = self.git.getcwd()
            self.project = os.path.basename(cwd)
            self.set_directory(cwd)
            core.chdir(cwd)
            self.cfg.reset()
            self.annex = self.cfg.is_annex()
            lfs = self.git.git_path('lfs')
            self.lfs = bool(lfs and core.exists(lfs))
        return is_valid

    def set_commitmsg(self, msg, notify=True):
        self.commitmsg = msg
        if notify:
            self.notify_observers(self.message_commit_message_changed, msg)

    def save_commitmsg(self, msg=None):
        if msg is None:
            msg = self.commitmsg
        path = self.git.git_path('GIT_COLA_MSG')
        try:
            if not msg.endswith('\n'):
                msg += '\n'
            core.write(path, msg)
        except:
            pass
        return path

    def set_diff_text(self, txt):
        """Update the text displayed in the diff editor"""
        self.diff_text = txt
        self.notify_observers(self.message_diff_text_changed, txt)

    def set_diff_type(self, diff_type):  # text, image
        """Set the diff type to either text or image"""
        self.diff_type = diff_type
        self.notify_observers(self.message_diff_type_changed, diff_type)

    def set_images(self, images):
        """Update the images shown in the preview pane"""
        self.images = images
        self.notify_observers(self.message_images_changed, images)

    def set_directory(self, path):
        self.directory = path

    def set_filename(self, filename):
        self.filename = filename
        self.notify_observers(self.message_filename_changed, filename)

    def set_mode(self, mode):
        if self.amending():
            if mode != self.mode_none:
                return
        if self.is_merging and mode == self.mode_amend:
            mode = self.mode
        if mode == self.mode_amend:
            head = 'HEAD^'
        else:
            head = 'HEAD'
        self.notify_observers(self.message_mode_about_to_change, mode)
        self.head = head
        self.mode = mode
        self.notify_observers(self.message_mode_changed, mode)

    def apply_diff(self, filename):
        return self.git.apply(filename, index=True, cached=True)

    def apply_diff_to_worktree(self, filename):
        return self.git.apply(filename)

    def prev_commitmsg(self, *args):
        """Queries git for the latest commit message."""
        return self.git.log('-1', no_color=True, pretty='format:%s%n%n%b',
                            *args)[STDOUT]

    def update_path_filter(self, filter_paths):
        self.filter_paths = filter_paths
        self.update_file_status()

    def emit_about_to_update(self):
        self.notify_observers(self.message_about_to_update)

    def emit_updated(self):
        self.notify_observers(self.message_updated)

    def update_file_status(self, update_index=False):
        self.emit_about_to_update()
        self.update_files(update_index=update_index, emit=True)

    def update_status(self, update_index=False):
        # Give observers a chance to respond
        self.emit_about_to_update()
        self.initialized = True
        self._update_merge_rebase_status()
        self._update_files(update_index=update_index)
        self._update_remotes()
        self._update_branches_and_tags()
        self._update_branch_heads()
        self._update_commitmsg()
        self.emit_updated()

    def update_files(self, update_index=False, emit=False):
        self._update_files(update_index=update_index)
        if emit:
            self.emit_updated()

    def _update_files(self, update_index=False):
        display_untracked = prefs.display_untracked()
        state = gitcmds.worktree_state(head=self.head,
                                       update_index=update_index,
                                       display_untracked=display_untracked,
                                       paths=self.filter_paths)
        self.staged = state.get('staged', [])
        self.modified = state.get('modified', [])
        self.unmerged = state.get('unmerged', [])
        self.untracked = state.get('untracked', [])
        self.upstream_changed = state.get('upstream_changed', [])
        self.staged_deleted = state.get('staged_deleted', set())
        self.unstaged_deleted = state.get('unstaged_deleted', set())
        self.submodules = state.get('submodules', set())

        selection = selection_model()
        if self.is_empty():
            selection.reset()
        else:
            selection.update(self)
        if selection.is_empty():
            self.set_diff_text('')

    def is_empty(self):
        return not(bool(self.staged or self.modified or
                        self.unmerged or self.untracked))

    def is_empty_repository(self):
        return not self.local_branches

    def _update_remotes(self):
        self.remotes = self.git.remote()[STDOUT].splitlines()

    def _update_branch_heads(self):
        # Set these early since they are used to calculate 'upstream_changed'.
        self.currentbranch = gitcmds.current_branch()

    def _update_branches_and_tags(self):
        local_branches, remote_branches, tags = gitcmds.all_refs(split=True)
        self.local_branches = local_branches
        self.remote_branches = remote_branches
        self.tags = tags

    def _update_merge_rebase_status(self):
        merge_head = self.git.git_path('MERGE_HEAD')
        rebase_merge = self.git.git_path('rebase-merge')
        self.is_merging = merge_head and core.exists(merge_head)
        self.is_rebasing = rebase_merge and core.exists(rebase_merge)
        if self.is_merging and self.mode == self.mode_amend:
            self.set_mode(self.mode_none)

    def _update_commitmsg(self):
        """Check for merge message files and update the commit message

        The message is cleared when the merge completes

        """
        if self.amending():
            return
        # Check if there's a message file in .git/
        merge_msg_path = gitcmds.merge_message_path()
        if merge_msg_path:
            msg = core.read(merge_msg_path)
            if msg != self._auto_commitmsg:
                self._auto_commitmsg = msg
                self._prev_commitmsg = self.commitmsg
                self.set_commitmsg(msg)

        elif self._auto_commitmsg and self._auto_commitmsg == self.commitmsg:
            self._auto_commitmsg = ''
            self.set_commitmsg(self._prev_commitmsg)

    def update_remotes(self):
        self._update_remotes()
        self._update_branches_and_tags()

    def delete_branch(self, branch):
        status, out, err = self.git.branch(branch, D=True)
        self._update_branches_and_tags()
        return status, out, err

    def rename_branch(self, branch, new_branch):
        status, out, err = self.git.branch(branch, new_branch, M=True)
        self.emit_about_to_update()
        self._update_branches_and_tags()
        self._update_branch_heads()
        self.emit_updated()
        return status, out, err

    def remote_url(self, name, action):
        if action == 'push':
            url = self.cfg.get('remote.%s.pushurl' % name)
            if url:
                return url
        return self.cfg.get('remote.%s.url' % name)

    def fetch(self, remote, **opts):
        return run_remote_action(self.git.fetch, remote, **opts)

    def push(self, remote, remote_branch='', local_branch='', **opts):
        # Swap the branches in push mode (reverse of fetch)
        opts.update(dict(local_branch=remote_branch,
                         remote_branch=local_branch))
        return run_remote_action(self.git.push, remote, push=True, **opts)

    def pull(self, remote, **opts):
        return run_remote_action(self.git.pull, remote, pull=True, **opts)

    def create_branch(self, name, base, track=False, force=False):
        """Create a branch named 'name' from revision 'base'

        Pass track=True to create a local tracking branch.
        """
        return self.git.branch(name, base, track=track, force=force)

    def cherry_pick_list(self, revs, **kwargs):
        """Cherry-picks each revision into the current branch.
        Returns a list of command output strings (1 per cherry pick)"""
        if not revs:
            return []
        outs = []
        errs = []
        status = 0
        for rev in revs:
            stat, out, err = self.git.cherry_pick(rev)
            status = max(stat, status)
            outs.append(out)
            errs.append(err)
        return (status, '\n'.join(outs), '\n'.join(errs))

    def pad(self, pstr, num=22):
        topad = num-len(pstr)
        if topad > 0:
            return pstr + ' '*topad
        else:
            return pstr

    def is_commit_published(self):
        """Return True if the latest commit exists in any remote branch"""
        return bool(self.git.branch(r=True, contains='HEAD')[STDOUT])

    def untrack_paths(self, paths):
        status, out, err = gitcmds.untrack_paths(paths, head=self.head)
        self.update_file_status()
        return status, out, err

    def getcwd(self):
        """If we've chosen a directory then use it, otherwise use current"""
        if self.directory:
            return self.directory
        return core.getcwd()


# Helpers
def remote_args(remote,
                local_branch='',
                remote_branch='',
                ff_only=False,
                force=False,
                no_ff=False,
                tags=False,
                rebase=False,
                pull=False,
                push=False,
                set_upstream=False,
                prune=False):
    """Return arguments for git fetch/push/pull"""

    args = [remote]
    what = refspec_arg(local_branch, remote_branch, pull, push)
    if what:
        args.append(what)

    kwargs = {
        'verbose': True,
    }
    if pull:
        if rebase:
            kwargs['rebase'] = True
        elif ff_only:
            kwargs['ff_only'] = True
        elif no_ff:
            kwargs['no_ff'] = True
    elif force:
        kwargs['force'] = True

    if push and set_upstream:
        kwargs['set_upstream'] = True
    if tags:
        kwargs['tags'] = True
    if prune:
        kwargs['prune'] = True

    return (args, kwargs)


def refspec(src, dst, push=False):
    if push and src == dst:
        spec = src
    else:
        spec = '%s:%s' % (src, dst)
    return spec


def refspec_arg(local_branch, remote_branch, pull, push):
    """Return the refspec for a fetch or pull command"""
    if not pull and local_branch and remote_branch:
        what = refspec(remote_branch, local_branch, push=push)
    else:
        what = local_branch or remote_branch or None
    return what


def run_remote_action(action, remote, **kwargs):
    args, kwargs = remote_args(remote, **kwargs)
    return action(*args, **kwargs)
