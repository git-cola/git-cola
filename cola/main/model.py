# Copyright (c) 2008 David Aguilar
"""This module provides the central cola model.
"""

import os
import copy

from cola import core
from cola import git
from cola import gitcfg
from cola import gitcmds
from cola import utils
from cola.compat import set
from cola.observable import Observable
from cola.decorators import memoize
from cola.models.selection import selection_model


# Static GitConfig instance
_config = gitcfg.instance()


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
    message_head_changed = 'head_changed'
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
        self.git = git.instance()

        self.head = 'HEAD'
        self.diff_text = ''
        self.mode = self.mode_none
        self.filename = None
        self.currentbranch = ''
        self.directory = ''
        self.project = ''
        self.remotes = []

        self.commitmsg = ''
        self.modified = []
        self.staged = []
        self.untracked = []
        self.unmerged = []
        self.upstream_changed = []
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

    def editor(self):
        app = _config.get('gui.editor', 'gvim')
        return {'vim': 'gvim'}.get(app, app)

    def history_browser(self):
        return _config.get('gui.historybrowser', 'gitk')

    def all_branches(self):
        return (self.local_branches + self.remote_branches)

    def set_worktree(self, worktree):
        self.git.set_worktree(worktree)
        is_valid = self.git.is_valid()
        if is_valid:
            basename = os.path.basename(self.git.worktree())
            self.project = core.decode(basename)
        return is_valid

    def set_commitmsg(self, msg):
        self.commitmsg = msg
        self.notify_observers(self.message_commit_message_changed, msg)

    def save_commitmsg(self, msg):
        path = git.git.git_path('GIT_COLA_MSG')
        utils.write(path, msg)

    def set_diff_text(self, txt):
        self.diff_text = txt
        self.notify_observers(self.message_diff_text_changed, txt)

    def set_directory(self, path):
        self.directory = path
        self.notify_observers(self.message_directory_changed, path)

    def set_filename(self, filename):
        self.filename = filename
        self.notify_observers(self.message_filename_changed, filename)

    def set_head(self, head):
        self.head = head
        self.notify_observers(self.message_head_changed, head)

    def set_mode(self, mode):
        self.notify_observers(self.message_mode_about_to_change, mode)
        if self.amending():
            if mode != self.mode_none:
                return
        self.mode = mode
        self.notify_observers(self.message_mode_changed, mode)

    def apply_diff(self, filename):
        return self.git.apply(filename, index=True, cached=True,
                              with_stderr=True, with_status=True)

    def apply_diff_to_worktree(self, filename):
        return self.git.apply(filename,
                              with_stderr=True, with_status=True)

    def prev_commitmsg(self, *args):
        """Queries git for the latest commit message."""
        log = self.git.log('-1', no_color=True, pretty='format:%s%n%n%b', *args)
        return core.decode(log)

    def update_file_status(self, update_index=False):
        self.notify_observers(self.message_about_to_update)
        self._update_files(update_index=update_index)
        self.notify_observers(self.message_updated)

    def update_status(self, update_index=False):
        # Give observers a chance to respond
        self.notify_observers(self.message_about_to_update)
        self._update_files(update_index=update_index)
        self._update_refs()
        self._update_branches_and_tags()
        self._update_branch_heads()
        self.notify_observers(self.message_updated)

    def _update_files(self, update_index=False):
        state = gitcmds.worktree_state_dict(head=self.head,
                                            update_index=update_index)
        self.staged = state.get('staged', [])
        self.modified = state.get('modified', [])
        self.unmerged = state.get('unmerged', [])
        self.untracked = state.get('untracked', [])
        self.submodules = state.get('submodules', set())
        self.upstream_changed = state.get('upstream_changed', [])
        if self.is_empty() or selection_model().is_empty():
            self.set_diff_text('')

    def is_empty(self):
        return not(bool(self.staged or self.modified or
                        self.unmerged or self.untracked))

    def _update_refs(self):
        self.remotes = self.git.remote().splitlines()

    def _update_branch_heads(self):
        # Set these early since they are used to calculate 'upstream_changed'.
        self.currentbranch = gitcmds.current_branch()

    def _update_branches_and_tags(self):
        local_branches, remote_branches, tags = gitcmds.all_refs(split=True)
        self.local_branches = local_branches
        self.remote_branches = remote_branches
        self.tags = tags

    def delete_branch(self, branch):
        return self.git.branch(branch,
                               D=True,
                               with_stderr=True,
                               with_status=True)

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
        size = max_arg_len / avg_filename_len

        full_status = 0
        full_output = []

        items = copy.copy(input_items)
        while items:
            status, output = map_fn(items[:size])
            full_status = full_status or status
            full_output.append(output)
            items = items[size:]

        return (full_status, '\n'.join(full_output))

    def _sliced_add(self, input_items):
        lambda_fn = lambda x: self.git.add('--',
                                           force=True,
                                           verbose=True,
                                           with_stderr=True,
                                           with_status=True,
                                           *x)
        return self._sliced_op(input_items, lambda_fn)

    def stage_modified(self):
        status, output = self._sliced_add(self.modified)
        self.update_file_status()
        return (status, output)

    def stage_untracked(self):
        status, output = self._sliced_add(self.untracked)
        self.update_file_status()
        return (status, output)

    def reset(self, *items):
        lambda_fn = lambda x: self.git.reset('--',
                                             with_stderr=True,
                                             with_status=True,
                                             *x)
        status, output = self._sliced_op(items, lambda_fn)
        self.update_file_status()
        return (status, output)

    def unstage_all(self):
        """Unstage all files, even while amending"""
        status, output = self.git.reset(self.head, '--', '.',
                                        with_stderr=True,
                                        with_status=True)
        self.update_file_status()
        return (status, output)

    def stage_all(self):
        status, output = self.git.add(v=True,
                                      u=True,
                                      with_stderr=True,
                                      with_status=True)
        self.update_file_status()
        return (status, output)

    def config_set(self, key, value, local=True):
        # git config category.key value
        strval = unicode(value)
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
        config_lines = self.git.config(**kwargs).splitlines()
        newdict = {}
        for line in config_lines:
            try:
                k, v = line.split('=', 1)
            except:
                # value-less entry in .gitconfig
                continue
            v = core.decode(v)
            k = k.replace('.','_') # git -> model
            if v == 'true' or v == 'false':
                v = bool(eval(v.title()))
            try:
                v = int(eval(v))
            except:
                pass
            newdict[k]=v
        return newdict

    def commit_with_msg(self, msg, tmpfile, amend=False):
        """Creates a git commit."""

        if not msg.endswith('\n'):
            msg += '\n'

        # Create the commit message file
        fh = open(tmpfile, 'w')
        core.write(fh, msg)
        fh.close()

        # Run 'git commit'
        status, out = self.git.commit(F=tmpfile, v=True, amend=amend,
                                      with_status=True,
                                      with_stderr=True)
        os.unlink(tmpfile)
        return (status, core.decode(out))

    def remote_url(self, name, action):
        if action == 'push':
            url = self.git.config('remote.%s.pushurl' % name, get=True)
            if url:
                return url
        return self.git.config('remote.%s.url' % name, get=True)

    def remote_args(self, remote,
                    local_branch='',
                    remote_branch='',
                    ffwd=True,
                    tags=False,
                    rebase=False,
                    push=False):
        # Swap the branches in push mode (reverse of fetch)
        if push:
            tmp = local_branch
            local_branch = remote_branch
            remote_branch = tmp
        if ffwd:
            branch_arg = '%s:%s' % (remote_branch, local_branch)
        else:
            branch_arg = '+%s:%s' % (remote_branch, local_branch)
        args = [remote]
        if local_branch and remote_branch:
            args.append(branch_arg)
        elif local_branch:
            args.append(local_branch)
        elif remote_branch:
            args.append(remote_branch)
        kwargs = {
            'verbose': True,
            'tags': tags,
            'rebase': rebase,
            'with_stderr': True,
            'with_status': True,
        }
        return (args, kwargs)

    def run_remote_action(self, action, remote, push=False, **kwargs):
        args, kwargs = self.remote_args(remote, push=push, **kwargs)
        return action(*args, **kwargs)

    def fetch(self, remote, **opts):
        return self.run_remote_action(self.git.fetch, remote, **opts)

    def push(self, remote, **opts):
        return self.run_remote_action(self.git.push, remote, push=True, **opts)

    def pull(self, remote, **opts):
        return self.run_remote_action(self.git.pull, remote, push=True, **opts)

    def create_branch(self, name, base, track=False, force=False):
        """Create a branch named 'name' from revision 'base'

        Pass track=True to create a local tracking branch.
        """
        return self.git.branch(name, base,
                               track=track, force=force,
                               with_stderr=True,
                               with_status=True)

    def cherry_pick_list(self, revs, **kwargs):
        """Cherry-picks each revision into the current branch.
        Returns a list of command output strings (1 per cherry pick)"""
        if not revs:
            return []
        cherries = []
        status = 0
        for rev in revs:
            newstatus, out = self.git.cherry_pick(rev,
                                                  with_stderr=True,
                                                  with_status=True)
            if status == 0:
                status += newstatus
            cherries.append(out)
        return (status, '\n'.join(cherries))

    def pad(self, pstr, num=22):
        topad = num-len(pstr)
        if topad > 0:
            return pstr + ' '*topad
        else:
            return pstr

    def is_commit_published(self):
        head = self.git.rev_parse('HEAD')
        return bool(self.git.branch(r=True, contains=head))

    def everything(self):
        """Returns a sorted list of all files, including untracked files."""
        ls_files = self.git.ls_files(z=True,
                                     cached=True,
                                     others=True,
                                     exclude_standard=True)
        return sorted(map(core.decode, [f for f in ls_files.split('\0') if f]))

    def stage_paths(self, paths):
        """Stages add/removals to git."""
        if not paths:
            self.stage_all()
            return

        add = []
        remove = []

        for path in set(paths):
            if os.path.exists(core.encode(path)):
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
                self.git.add('--', u=True, with_stderr=True, *remove[:42])
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
        status, out = gitcmds.untrack_paths(paths, head=self.head)
        self.update_file_status()
        return status, out

    def getcwd(self):
        """If we've chosen a directory then use it, otherwise os.getcwd()."""
        if self.directory:
            return self.directory
        return os.getcwd()
