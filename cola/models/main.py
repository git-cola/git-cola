# Copyright (c) 2008 David Aguilar
"""This module provides the central cola model.
"""

import os
import sys
import time
import copy
import subprocess
from cStringIO import StringIO

from cola import core
from cola import utils
from cola import git
from cola import gitcfg
from cola import gitcmds
from cola.compat import set
from cola import serializer
from cola.models.observable import ObservableModel, OMSerializer
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
    message_updated = 'updated'
    message_about_to_update = 'about_to_update'

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
        self.mode = self.mode_none
        self.diff_text = ''
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
            self._init_config_data()
            basename = os.path.basename(self.git.worktree())
            self.set_project(core.decode(basename))
        return is_valid

    def _init_config_data(self):
        """Reads git config --list and creates parameters
        for each setting."""
        # These parameters are saved in .gitconfig,
        # so ideally these should be as short as possible.

        # config items that are controllable globally
        # and per-repository
        self._local_and_global_defaults = {
            'user_name': '',
            'user_email': '',
            'merge_summary': False,
            'merge_diffstat': True,
            'merge_verbosity': 2,
            'gui_diffcontext': 3,
            'gui_pruneduringfetch': False,
        }
        # config items that are purely git config --global settings
        self._global_defaults = {
            'cola_geometry': '',
            'cola_fontdiff': '',
            'cola_fontdiff_size': 12,
            'cola_savewindowsettings': True,
            'cola_showoutput': 'errors',
            'cola_tabwidth': 8,
            'merge_keepbackup': True,
            'diff_tool': os.getenv('GIT_DIFF_TOOL', 'xxdiff'),
            'merge_tool': os.getenv('GIT_MERGE_TOOL', 'xxdiff'),
            'gui_editor': os.getenv('VISUAL', os.getenv('EDITOR', 'gvim')),
            'gui_historybrowser': 'gitk',
        }

        def _underscore(dct):
            underscore = {}
            for k, v in dct.iteritems():
                underscore[k.replace('.', '_')] = v
            return underscore

        _config.update()
        local_dict = _underscore(_config.repo())
        global_dict = _underscore(_config.user())

        for k,v in local_dict.iteritems():
            self.set_param('local_'+k, v)
        for k,v in global_dict.iteritems():
            self.set_param('global_'+k, v)
            if k not in local_dict:
                local_dict[k]=v
                self.set_param('local_'+k, v)

        # Bootstrap the internal font*size variables
        for param in ('global_cola_fontdiff'):
            setdefault = True
            if hasattr(self, param):
                font = getattr(self, param)
                if font:
                    setdefault = False
                    size = int(font.split(',')[1])
                    self.set_param(param+'_size', size)
                    param = param[len('global_'):]
                    global_dict[param] = font
                    global_dict[param+'_size'] = size

        # Load defaults for all undefined items
        local_and_global_defaults = self._local_and_global_defaults
        for k,v in local_and_global_defaults.iteritems():
            if k not in local_dict:
                self.set_param('local_'+k, v)
            if k not in global_dict:
                self.set_param('global_'+k, v)

        global_defaults = self._global_defaults
        for k,v in global_defaults.iteritems():
            if k not in global_dict:
                self.set_param('global_'+k, v)

        # Load the diff context
        self.diff_context = _config.get('gui.diffcontext', 3)

    def global_config(self, key, default=None):
        return self.param('global_'+key.replace('.', '_'),
                          default=default)

    def local_config(self, key, default=None):
        return self.param('local_'+key.replace('.', '_'),
                          default=default)

    def cola_config(self, key):
        return getattr(self, 'global_cola_'+key)

    def gui_config(self, key):
        return getattr(self, 'global_gui_'+key)

    def config_params(self):
        params = []
        params.extend(map(lambda x: 'local_' + x,
                          self._local_and_global_defaults.keys()))
        params.extend(map(lambda x: 'global_' + x,
                          self._local_and_global_defaults.keys()))
        params.extend(map(lambda x: 'global_' + x,
                          self._global_defaults.keys()))
        return [ p for p in params if not p.endswith('_size') ]

    def save_config_param(self, param):
        if param not in self.config_params():
            return
        value = getattr(self, param)
        if param == 'local_gui_diffcontext':
            self.diff_context = value
        if param.startswith('local_'):
            param = param[len('local_'):]
            is_local = True
        elif param.startswith('global_'):
            param = param[len('global_'):]
            is_local = False
        else:
            raise Exception("Invalid param '%s' passed to " % param
                           +'save_config_param()')
        param = param.replace('_', '.') # model -> git
        return self.config_set(param, value, local=is_local)

    def editor(self):
        app = self.gui_config('editor')
        return {'vim': 'gvim'}.get(app, app)

    def history_browser(self):
        return self.gui_config('historybrowser')

    def remember_gui_settings(self):
        return self.cola_config('savewindowsettings')

    def all_branches(self):
        return (self.local_branches + self.remote_branches)

    def set_remote(self, remote):
        if not remote:
            return
        self.set_param('remote', remote)
        branches = utils.grep('%s/\S+$' % remote,
                              gitcmds.branch_list(remote=True),
                              squash=False)
        self.set_remote_branches(branches)

    def apply_diff(self, filename):
        return self.git.apply(filename, index=True, cached=True)

    def apply_diff_to_worktree(self, filename):
        return self.git.apply(filename)

    def prev_commitmsg(self):
        """Queries git for the latest commit message."""
        return core.decode(self.git.log('-1', no_color=True, pretty='format:%s%n%n%b'))

    def update_status(self):
        # Give observers a chance to respond
        self.notify_message_observers(self.message_about_to_update)
        # This allows us to defer notification until the
        # we finish processing data
        self.notification_enabled = False

        self._update_files()
        self._update_refs()
        self._update_branches_and_tags()
        self._update_branch_heads()

        # Re-enable notifications and emit changes
        self.notification_enabled = True
        self.notify_observers('staged', 'unstaged')
        self.broadcast_updated()

        self.read_font_sizes()

    def broadcast_updated(self):
        self.notify_message_observers(self.message_updated)

    def _update_files(self, worktree_only=False):
        staged_only = self.read_only()
        state = gitcmds.worktree_state_dict(head=self.head,
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

    def read_font_sizes(self):
        """Read font sizes from the configuration."""
        value = self.cola_config('fontdiff')
        if not value:
            return
        items = value.split(',')
        if len(items) < 2:
            return
        self.global_cola_fontdiff_size = int(float(items[1]))

    def set_diff_font(self, fontstr):
        """Set the diff font string."""
        self.global_cola_fontdiff = fontstr
        self.read_font_sizes()

    def delete_branch(self, branch):
        return self.git.branch(branch,
                               D=True,
                               with_stderr=True,
                               with_status=True)

    def revision_sha1(self, idx):
        return self.revisions[idx]

    def apply_diff_font_size(self, default):
        old_font = self.cola_config('fontdiff')
        if not old_font:
            old_font = default
        size = self.cola_config('fontdiff_size')
        props = old_font.split(',')
        props[1] = str(size)
        new_font = ','.join(props)
        self.global_cola_fontdiff = new_font
        self.notify_observers('global_cola_fontdiff')

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
        self.update_status()
        return (status, output)

    def stage_untracked(self):
        status, output = self._sliced_add(self.untracked)
        self.update_status()
        return (status, output)

    def reset(self, *items):
        lambda_fn = lambda x: self.git.reset('--',
                                             with_stderr=True,
                                             with_status=True,
                                             *x)
        status, output = self._sliced_op(items, lambda_fn)
        self.update_status()
        return (status, output)

    def unstage_all(self):
        status, output = self.git.reset(self.head, '--', '.',
                                        with_stderr=True,
                                        with_status=True)
        self.update_status()
        return (status, output)

    def stage_all(self):
        status, output = self.git.add(v=True,
                                      u=True,
                                      with_stderr=True,
                                      with_status=True)
        self.update_status()
        return (status, output)

    def config_set(self, key=None, value=None, local=True):
        if key and value is not None:
            # git config category.key value
            strval = unicode(value)
            if type(value) is bool:
                # git uses "true" and "false"
                strval = strval.lower()
            if local:
                argv = [ key, strval ]
            else:
                argv = [ '--global', key, strval ]
            return self.git.config(*argv)
        else:
            msg = "oops in config_set(key=%s,value=%s,local=%s)"
            raise Exception(msg % (key, value, local))

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

    def remote_url(self, name):
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
        sset = set(self.staged)
        mset = set(self.modified)
        umset = set(self.unmerged)
        utset = set(self.untracked)
        dirs = bool([p for p in paths if os.path.isdir(core.encode(p))])

        if not dirs:
            self.notify_message_observers(self.message_about_to_update)

        for path in set(paths):
            if not os.path.isdir(core.encode(path)) and path not in sset:
                self.staged.append(path)
            if path in umset:
                self.unmerged.remove(path)
            if path in mset:
                self.modified.remove(path)
            if path in utset:
                self.untracked.remove(path)
            if os.path.exists(core.encode(path)):
                add.append(path)
            else:
                remove.append(path)

        if dirs:
            self.notify_message_observers(self.message_about_to_update)

        elif add or remove:
            self.staged.sort()

        # `git add -u` doesn't work on untracked files
        if add:
            self._sliced_add(add)
        # If a path doesn't exist then that means it should be removed
        # from the index.   We use `git add -u` for that.
        if remove:
            while remove:
                self.git.add('--', u=True, with_stderr=True, *remove[:42])
                remove = remove[42:]

        if dirs:
            self._update_files()

        self.notify_message_observers(self.message_updated)

    def unstage_paths(self, paths):
        if not paths:
            self.unstage_all()
            return
        self.notify_message_observers(self.message_about_to_update)

        staged_set = set(self.staged)
        gitcmds.unstage_paths(paths, head=self.head)
        all_paths_set = set(gitcmds.all_files())
        modified = []
        untracked = []

        cur_modified_set = set(self.modified)
        cur_untracked_set = set(self.untracked)

        for path in paths:
            if path in staged_set:
                self.staged.remove(path)
                if path in all_paths_set:
                    if path not in cur_modified_set:
                        modified.append(path)
                else:
                    if path not in cur_untracked_set:
                        untracked.append(path)

        if modified:
            self.modified.extend(modified)
            self.modified.sort()

        if untracked:
            self.untracked.extend(untracked)
            self.untracked.sort()

        self.notify_message_observers(self.message_updated)

    def getcwd(self):
        """If we've chosen a directory then use it, otherwise os.getcwd()."""
        if self.directory:
            return self.directory
        return os.getcwd()

serializer.handlers[MainModel] = MainSerializer
