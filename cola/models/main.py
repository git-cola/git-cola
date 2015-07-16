# Copyright (c) 2008 David Aguilar
"""This module provides the central cola model.
"""
from __future__ import division, absolute_import, unicode_literals

import copy
import os

from cola import core
from cola import git
from cola import gitcmds
from cola.git import STDOUT
from cola.observable import Observable
from cola.decorators import memoize
from cola.models.selection import selection_model
from cola.models import prefs
from cola.compat import ustr


@memoize
def model():
    """Returns the main model singleton"""
    return MainModel()


class MainModel(Observable):
    """Provides a friendly wrapper for doing common git operations."""

    # Observable messages
    message_about_to_update = 'about_to_update'
    message_commit_message_changed = 'commit_message_changed'
    message_diff_text_changed = 'diff_text_changed'
    message_directory_changed = 'directory_changed'
    message_filename_changed = 'filename_changed'
    message_mode_about_to_change = 'mode_about_to_change'
    message_mode_changed = 'mode_changed'
    message_updated = 'updated'

    # States
    mode_none = 'none' # Default: nothing's happened, do nothing
    mode_worktree = 'worktree' # Comparing index to worktree
    mode_untracked = 'untracked' # Dealing with an untracked file
    mode_index = 'index' # Comparing index to last commit
    mode_amend = 'amend' # Amending a commit

    # Modes where we can checkout files from the $head
    modes_undoable = set((mode_amend, mode_index, mode_worktree))

    # Modes where we can partially stage files
    modes_stageable = set((mode_amend, mode_worktree, mode_untracked))

    # Modes where we can partially unstage files
    modes_unstageable = set((mode_amend, mode_index))

    unstaged = property(lambda self: self.modified + self.unmerged + self.untracked)
    """An aggregate of the modified, unmerged, and untracked file lists."""

    def __init__(self, cwd=None):
        """Reads git repository settings and sets several methods
        so that they refer to the git module.  This object
        encapsulates cola's interaction with git."""
        Observable.__init__(self)

        # Initialize the git command object
        self.git = git.current()

        self.head = 'HEAD'
        self.diff_text = ''
        self.mode = self.mode_none
        self.filename = None
        self.is_merging = False
        self.is_rebasing = False
        self.currentbranch = ''
        self.directory = ''
        self.project = ''
        self.remotes = []
        self.filter_paths = None

        self.commitmsg = ''  # current commit message
        self._auto_commitmsg = ''  # e.g. .git/MERGE_MSG
        self._prev_commitmsg = '' # saved here when clobbered by .git/MERGE_MSG

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
            self.project = os.path.basename(self.git.worktree())
        return is_valid

    def set_commitmsg(self, msg, notify=True):
        self.commitmsg = msg
        if notify:
            self.notify_observers(self.message_commit_message_changed, msg)

    def save_commitmsg(self, msg):
        path = self.git.git_path('GIT_COLA_MSG')
        try:
            core.write(path, msg)
        except:
            pass

    def set_diff_text(self, txt):
        self.diff_text = txt
        self.notify_observers(self.message_diff_text_changed, txt)

    def set_directory(self, path):
        self.directory = path
        self.notify_observers(self.message_directory_changed, path)

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

    def update_file_status(self, update_index=False):
        self.notify_observers(self.message_about_to_update)
        self._update_files(update_index=update_index)
        self.notify_observers(self.message_updated)

    def update_status(self, update_index=False):
        # Give observers a chance to respond
        self.notify_observers(self.message_about_to_update)
        self._update_merge_rebase_status()
        self._update_files(update_index=update_index)
        self._update_remotes()
        self._update_branches_and_tags()
        self._update_branch_heads()
        self._update_commitmsg()
        self.notify_observers(self.message_updated)

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

        sel = selection_model()
        if self.is_empty():
            sel.reset()
        else:
            sel.update(self)
        if selection_model().is_empty():
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
        self.is_merging = core.exists(self.git.git_path('MERGE_HEAD'))
        self.is_rebasing = core.exists(self.git.git_path('rebase-merge'))
        if self.is_merging and self.mode == self.mode_amend:
            self.set_mode(self.mode_none)

    def _update_commitmsg(self):
        """Check for git merge message files, or clear it when the merge completes"""
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
        self.notify_observers(self.message_about_to_update)
        self._update_branches_and_tags()
        self._update_branch_heads()
        self.notify_observers(self.message_updated)
        return status, out, err

    def _sliced_op(self, input_items, map_fn):
        """Slice input_items and call map_fn over every slice

        This exists because of "errno: Argument list too long"

        """
        # This comment appeared near the top of include/linux/binfmts.h
        # in the Linux source tree:
        #
        # /*
        #  * MAX_ARG_PAGES defines the number of pages allocated for arguments
        #  * and envelope for the new program. 32 should suffice, this gives
        #  * a maximum env+arg of 128kB w/4KB pages!
        #  */
        # #define MAX_ARG_PAGES 32
        #
        # 'size' is a heuristic to keep things highly performant by minimizing
        # the number of slices.  If we wanted it to run as few commands as
        # possible we could call "getconf ARG_MAX" and make a better guess,
        # but it's probably not worth the complexity (and the extra call to
        # getconf that we can't do on Windows anyways).
        #
        # In my testing, getconf ARG_MAX on Mac OS X Mountain Lion reported
        # 262144 and Debian/Linux-x86_64 reported 2097152.
        #
        # The hard-coded max_arg_len value is safely below both of these
        # real-world values.

        max_arg_len = 32 * 4 * 1024
        avg_filename_len = 300
        size = max_arg_len // avg_filename_len

        status = 0
        outs = []
        errs = []

        items = copy.copy(input_items)
        while items:
            stat, out, err = map_fn(items[:size])
            status = max(stat, status)
            outs.append(out)
            errs.append(err)
            items = items[size:]

        return (status, '\n'.join(outs), '\n'.join(errs))

    def _sliced_add(self, input_items):
        lambda_fn = lambda x: self.git.add('--', force=True, verbose=True, *x)
        return self._sliced_op(input_items, lambda_fn)

    def stage_modified(self):
        status, out, err = self._sliced_add(self.modified)
        self.update_file_status()
        return (status, out, err)

    def stage_untracked(self):
        status, out, err = self._sliced_add(self.untracked)
        self.update_file_status()
        return (status, out, err)

    def reset(self, *items):
        lambda_fn = lambda x: self.git.reset('--', *x)
        status, out, err = self._sliced_op(items, lambda_fn)
        self.update_file_status()
        return (status, out, err)

    def unstage_all(self):
        """Unstage all files, even while amending"""
        status, out, err = self.git.reset(self.head, '--', '.')
        self.update_file_status()
        return (status, out, err)

    def stage_all(self):
        status, out, err = self.git.add(v=True, u=True)
        self.update_file_status()
        return (status, out, err)

    def config_set(self, key, value, local=True):
        # git config category.key value
        strval = ustr(value)
        if type(value) is bool:
            # git uses "true" and "false"
            strval = strval.lower()
        if local:
            argv = [key, strval]
        else:
            argv = ['--global', key, strval]
        return self.git.config(*argv)

    def config_dict(self, local=True):
        """parses the lines from git config --list into a dictionary"""

        kwargs = {
            'list': True,
            'global': not local, # global is a python keyword
        }
        config_lines = self.git.config(**kwargs)[STDOUT].splitlines()
        newdict = {}
        for line in config_lines:
            try:
                k, v = line.split('=', 1)
            except:
                # value-less entry in .gitconfig
                continue
            k = k.replace('.','_') # git -> model
            if v == 'true' or v == 'false':
                v = bool(eval(v.title()))
            try:
                v = int(eval(v))
            except:
                pass
            newdict[k]=v
        return newdict

    def remote_url(self, name, action):
        if action == 'push':
            url = self.git.config('remote.%s.pushurl' % name,
                                  get=True)[STDOUT]
            if url:
                return url
        return self.git.config('remote.%s.url' % name, get=True)[STDOUT]

    def fetch(self, remote, **opts):
        return run_remote_action(self.git.fetch, remote, **opts)

    def push(self, remote, remote_branch='', local_branch='', **opts):
        # Swap the branches in push mode (reverse of fetch)
        opts.update(dict(local_branch=remote_branch, remote_branch=local_branch))
        return run_remote_action(self.git.push, remote, **opts)

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
        head = self.git.rev_parse('HEAD')[STDOUT]
        return bool(self.git.branch(r=True, contains=head)[STDOUT])

    def stage_paths(self, paths):
        """Stages add/removals to git."""
        if not paths:
            self.stage_all()
            return

        add = []
        remove = []

        for path in set(paths):
            if core.exists(path):
                add.append(path)
            else:
                remove.append(path)

        self.notify_observers(self.message_about_to_update)

        # `git add -u` doesn't work on untracked files
        if add:
            self._sliced_add(add)

        # If a path doesn't exist then that means it should be removed
        # from the index.   We use `git add -u` for that.
        if remove:
            while remove:
                self.git.add('--', u=True, *remove[:42])
                remove = remove[42:]

        self._update_files()
        self.notify_observers(self.message_updated)

    def unstage_paths(self, paths):
        if not paths:
            self.unstage_all()
            return
        gitcmds.unstage_paths(paths, head=self.head)
        self.update_file_status()

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
                ffwd=True,
                tags=False,
                rebase=False,
                pull=False):
    """Return arguments for git fetch/push/pull"""

    args = [remote]
    what = refspec_arg(local_branch, remote_branch, ffwd, pull)
    if what:
        args.append(what)
    kwargs = {
        'verbose': True,
        'tags': tags,
        'rebase': rebase,
    }
    return (args, kwargs)


def refspec(src, dst, ffwd):
    spec = '%s:%s' % (src, dst)
    if not ffwd:
        spec = '+' + spec
    return spec


def refspec_arg(local_branch, remote_branch, ffwd, pull):
    """Return the refspec for a fetch or pull command"""
    if not pull and local_branch and remote_branch:
        what = refspec(remote_branch, local_branch, ffwd)
    else:
        what = local_branch or remote_branch or None
    return what


def run_remote_action(action, remote, **kwargs):
    args, kwargs = remote_args(remote, **kwargs)
    return action(*args, **kwargs)
