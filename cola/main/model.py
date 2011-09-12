# Copyright (c) 2008 David Aguilar
"""This module provides the central cola model.
"""

import os
import time
import copy

from cola import core
from cola import utils
from cola import git
from cola import gitcfg
from cola import gitcmds
from cola import serializer
from cola.compat import set
from cola.obsmodel import ObservableModel, OMSerializer
from cola.decorators import memoize


# Static GitConfig instance
_config = gitcfg.instance()


# Provides access to a global MainModel instance
@memoize
def model():
    """Returns the main model singleton"""
    return MainModel()


class MainSerializer(OMSerializer):
    def post_decode_hook(self):
        OMSerializer.post_decode_hook(self)
        self.obj.generate_remote_helpers()


class MainModel(ObservableModel):
    """Provides a friendly wrapper for doing common git operations."""

    # Observable messages
    message_about_to_update = 'about_to_update'
    message_commit_message_changed = 'commit_message_changed'
    message_diff_text_changed = 'diff_text_changed'
    message_filename_changed = 'filename_changed'
    message_head_changed = 'head_changed'
    message_mode_changed = 'mode_changed'
    message_updated = 'updated'

    # States
    mode_none = 'none' # Default: nothing's happened, do nothing
    mode_worktree = 'worktree' # Comparing index to worktree
    mode_index = 'index' # Comparing index to last commit
    mode_amend = 'amend' # Amending a commit
    mode_grep = 'grep' # We ran Search -> Grep
    mode_branch = 'branch' # Applying changes from a branch
    mode_diff = 'diff' # Diffing against an arbitrary branch
    mode_diff_expr = 'diff_expr' # Diffing using arbitrary expression
    mode_review = 'review' # Reviewing a branch

    # Modes where we don't do anything like staging, etc.
    modes_read_only = (mode_branch, mode_grep,
                       mode_diff, mode_diff_expr, mode_review)
    # Modes where we can checkout files from the $head
    modes_undoable = (mode_none, mode_index, mode_worktree)

    unstaged = property(lambda self: self.modified + self.unmerged + self.untracked)
    """An aggregate of the modified, unmerged, and untracked file lists."""

    def __init__(self, cwd=None):
        """Reads git repository settings and sets several methods
        so that they refer to the git module.  This object
        encapsulates cola's interaction with git."""
        ObservableModel.__init__(self)

        # Initialize the git command object
        self.git = git.instance()

        #####################################################
        self.head = 'HEAD'
        self.diff_text = ''
        self.mode = self.mode_none
        self.filename = None
        self.currentbranch = ''
        self.trackedbranch = ''
        self.directory = ''
        self.git_version = self.git.version()
        self.remotes = []
        self.remotename = ''
        self.local_branch = ''
        self.remote_branch = ''

        #####################################################
        # Status info
        self.commitmsg = ''
        self.modified = []
        self.staged = []
        self.untracked = []
        self.unmerged = []
        self.upstream_changed = []
        self.submodules = set()

        #####################################################
        # Refs
        self.revision = ''
        self.local_branches = []
        self.remote_branches = []
        self.tags = []
        self.revisions = []
        self.summaries = []

        self.fetch_helper = None
        self.push_helper = None
        self.pull_helper = None
        self.generate_remote_helpers()
        if cwd:
            self.use_worktree(cwd)

        #####################################################
        # Dag
        self._commits = []

    def read_only(self):
        return self.mode in self.modes_read_only

    def undoable(self):
        """Whether we can checkout files from the $head."""
        return self.mode in self.modes_undoable

    def enable_staging(self):
        """Whether staging should be allowed."""
        return self.mode == self.mode_worktree

    def generate_remote_helpers(self):
        """Generates helper methods for fetch, push and pull"""
        self.push_helper = self.gen_remote_helper(self.git.push, push=True)
        self.fetch_helper = self.gen_remote_helper(self.git.fetch)
        self.pull_helper = self.gen_remote_helper(self.git.pull)

    def use_worktree(self, worktree):
        self.git.load_worktree(worktree)
        is_valid = self.git.is_valid()
        if is_valid:
            basename = os.path.basename(self.git.worktree())
            self.set_project(core.decode(basename))
        return is_valid

    def editor(self):
        app = _config.get('gui.editor', 'gvim')
        return {'vim': 'gvim'}.get(app, app)

    def history_browser(self):
        return _config.get('gui.historybrowser', 'gitk')

    def remember_gui_settings(self):
        return _config.get('cola.savewindowsettings', True)

    def all_branches(self):
        return (self.local_branches + self.remote_branches)

    def set_commitmsg(self, msg):
        self.commitmsg = msg
        self.notify_message_observers(self.message_commit_message_changed, msg)

    def set_diff_text(self, txt):
        self.diff_text = txt
        self.notify_message_observers(self.message_diff_text_changed, txt)

    def set_filename(self, filename):
        self.filename = filename
        self.notify_message_observers(self.message_filename_changed, filename)

    def set_head(self, head):
        self.head = head
        self.notify_message_observers(self.message_head_changed, head)

    def set_mode(self, mode):
        self.mode = mode
        self.notify_message_observers(self.message_mode_changed, mode)

    def set_remote(self, remote):
        if not remote:
            return
        self.set_param('remote', remote)
        branches = utils.grep('%s/\S+$' % remote,
                              gitcmds.branch_list(remote=True),
                              squash=False)
        self.set_remote_branches(branches)

    def apply_diff(self, filename):
        return self.git.apply(filename, index=True, cached=True,
                              with_stderr=True, with_status=True)

    def apply_diff_to_worktree(self, filename):
        return self.git.apply(filename,
                              with_stderr=True, with_status=True)

    def prev_commitmsg(self):
        """Queries git for the latest commit message."""
        return core.decode(self.git.log('-1', no_color=True, pretty='format:%s%n%n%b'))

    def update_file_status(self, update_index=False):
        self.notify_message_observers(self.message_about_to_update)
        self.notification_enabled = False
        self._update_files(update_index=update_index)
        self.notification_enabled = True
        self.notify_observers('staged', 'unstaged')
        self.broadcast_updated()

    def update_status(self, update_index=False):
        # Give observers a chance to respond
        self.notify_message_observers(self.message_about_to_update)
        # This allows us to defer notification until the
        # we finish processing data
        self.notification_enabled = False

        self._update_files(update_index=update_index)
        self._update_refs()
        self._update_branches_and_tags()
        self._update_branch_heads()

        # Re-enable notifications and emit changes
        self.notification_enabled = True
        self.notify_observers('staged', 'unstaged')
        self.broadcast_updated()

    def update_status_of_files(self, files):
        self.notify_message_observers(self.message_about_to_update)
        self.notification_enabled = False

        states = gitcmds.partial_worktree_state_dict(files, self.head)
        for status, path in states:
            if status == 'unmodified':
                if path in self.modified:
                    self.modified.remove(path)
                if path in self.untracked:
                    self.untracked.remove(path)
            elif status == 'modified':
                if path in self.untracked:
                    self.untracked.remove(path)
                if path not in self.modified:
                    self.modified.append(path)
            elif status == 'untracked':
                if path in self.modified:
                    self.modified.remove(path)
                if path not in self.untracked:
                    self.untracked.append(path)

        self.modified.sort()
        self.untracked.sort()

        self.notification_enabled = True
        self.notify_observers('staged', 'unstaged')
        self.broadcast_updated()

    def broadcast_updated(self):
        self.notify_message_observers(self.message_updated)

    def _update_files(self, worktree_only=False, update_index=False):
        staged_only = self.read_only()
        state = gitcmds.worktree_state_dict(head=self.head,
                                            update_index=update_index,
                                            staged_only=staged_only)
        self.staged = state.get('staged', [])
        self.modified = state.get('modified', [])
        self.unmerged = state.get('unmerged', [])
        self.untracked = state.get('untracked', [])
        self.submodules = state.get('submodules', set())
        self.upstream_changed = state.get('upstream_changed', [])

    def _update_refs(self):
        self.set_remotes(self.git.remote().splitlines())
        self.set_revision('')
        self.set_local_branch('')
        self.set_remote_branch('')


    def _update_branch_heads(self):
        # Set these early since they are used to calculate 'upstream_changed'.
        self.set_trackedbranch(gitcmds.tracked_branch())
        self.set_currentbranch(gitcmds.current_branch())

    def _update_branches_and_tags(self):
        local_branches, remote_branches, tags = gitcmds.all_refs(split=True)
        self.set_local_branches(local_branches)
        self.set_remote_branches(remote_branches)
        self.set_tags(tags)

    def delete_branch(self, branch):
        return self.git.branch(branch,
                               D=True,
                               with_stderr=True,
                               with_status=True)

    def revision_sha1(self, idx):
        return self.revisions[idx]

    def _sliced_op(self, input_items, map_fn, size=42):
        items = copy.copy(input_items)
        full_status = 0
        full_output = []
        while len(items) > 0:
            status, output = map_fn(items[:size])
            full_status = full_status or status
            full_output.append(output)
            items = items[size:]
        return (full_status, '\n'.join(full_output))

    def _sliced_add(self, input_items, size=42):
        lambda_fn = lambda x: self.git.add('--',
                                           v=True,
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

    def commit_with_msg(self, msg, amend=False):
        """Creates a git commit."""

        if not msg.endswith('\n'):
            msg += '\n'
        # Sure, this is a potential "security risk," but if someone
        # is trying to intercept/re-write commit messages on your system,
        # then you probably have bigger problems to worry about.
        tmpfile = self.tmp_filename()

        # Create the commit message file
        fh = open(tmpfile, 'w')
        core.write_nointr(fh, msg)
        fh.close()

        # Run 'git commit'
        status, out = self.git.commit(F=tmpfile, v=True, amend=amend,
                                      with_status=True,
                                      with_stderr=True)
        os.unlink(tmpfile)
        return (status, out)

    def tmp_dir(self):
        # Allow TMPDIR/TMP with a fallback to /tmp
        return os.environ.get('TMP', os.environ.get('TMPDIR', '/tmp'))

    def tmp_file_pattern(self):
        return os.path.join(self.tmp_dir(), '*.git-cola.%s.*' % os.getpid())

    def tmp_filename(self, prefix=''):
        basename = ((prefix+'.git-cola.%s.%s'
                    % (os.getpid(), time.time())))
        basename = basename.replace('/', '-')
        basename = basename.replace('\\', '-')
        tmpdir = self.tmp_dir()
        return os.path.join(tmpdir, basename)

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
            branch_arg = '%s:%s' % ( remote_branch, local_branch )
        else:
            branch_arg = '+%s:%s' % ( remote_branch, local_branch )
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

    def gen_remote_helper(self, gitaction, push=False):
        """Generates a closure that calls git fetch, push or pull
        """
        def remote_helper(remote, **kwargs):
            args, kwargs = self.remote_args(remote, push=push, **kwargs)
            return gitaction(*args, **kwargs)
        return remote_helper

    def create_branch(self, name, base, track=False):
        """Create a branch named 'name' from revision 'base'

        Pass track=True to create a local tracking branch.
        """
        return self.git.branch(name, base, track=track,
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

    def parse_stash_list(self, revids=False, names=False):
        """Parses "git stash list" and returns a list of stashes."""
        stashes = self.git.stash("list").splitlines()
        if revids:
            return [s[:s.index(':')] for s in stashes]
        elif names:
            return [s.split(': ', 2)[-1] for s in stashes]
        else:
            return stashes

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

        self.notify_message_observers(self.message_about_to_update)

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
        self.notify_message_observers(self.message_updated)

    def unstage_paths(self, paths):
        if not paths:
            self.unstage_all()
            return
        gitcmds.unstage_paths(paths, head=self.head)
        self.update_file_status()

    def getcwd(self):
        """If we've chosen a directory then use it, otherwise os.getcwd()."""
        if self.directory:
            return self.directory
        return os.getcwd()

serializer.handlers[MainModel] = MainSerializer
