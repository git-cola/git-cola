# Copyright (c) 2008 David Aguilar
"""This module provides the central cola model.
"""

import os
import sys
import re
import time
import subprocess
from cStringIO import StringIO

from cola import core
from cola import utils
from cola import gitcmd
from cola import gitcmds
from cola.models.observable import ObservableModel


# Provides access to a global MainModel instance
_instance = None
def model():
    """Returns the main model singleton"""
    global _instance
    if _instance:
        return _instance
    _instance = MainModel()
    return _instance


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

    def __init__(self, cwd=None):
        """Reads git repository settings and sets several methods
        so that they refer to the git module.  This object
        encapsulates cola's interaction with git."""
        ObservableModel.__init__(self)

        # Initialize the git command object
        self.git = gitcmd.instance()

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
        self.unstaged = []
        self.untracked = []
        self.unmerged = []
        self.upstream_changed = []

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
            self.set_project(os.path.basename(self.git.worktree()))
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
            'cola_savewindowsettings': False,
            'cola_showoutput': 'errors',
            'cola_tabwidth': 8,
            'merge_keepbackup': True,
            'diff_tool': os.getenv('GIT_DIFF_TOOL', 'xxdiff'),
            'merge_tool': os.getenv('GIT_MERGE_TOOL', 'xxdiff'),
            'gui_editor': os.getenv('EDITOR', 'gvim'),
            'gui_historybrowser': 'gitk',
        }

        local_dict = self.config_dict(local=True)
        global_dict = self.config_dict(local=False)

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
        self.diff_context = self.local_config('gui.diffcontext', 3)

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
        return self.gui_config('editor')

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

    def load_commitmsg(self, path):
        fh = open(path, 'r')
        contents = core.decode(core.read_nointr(fh))
        fh.close()
        self.set_commitmsg(contents)

    def prev_commitmsg(self):
        """Queries git for the latest commit message."""
        return core.decode(self.git.log('-1', pretty='format:%s%n%n%b'))

    def load_commitmsg_template(self):
        template = self.global_config('commit.template')
        if template:
            self.load_commitmsg(template)

    def update_status(self):
        # Give observers a chance to respond
        self.notify_message_observers(self.message_about_to_update)
        # This allows us to defer notification until the
        # we finish processing data
        staged_only = self.read_only()
        head = self.head
        notify_enabled = self.notification_enabled
        self.notification_enabled = False

        # Set these early since they are used to calculate 'upstream_changed'.
        self.set_trackedbranch(gitcmds.tracked_branch())
        self.set_currentbranch(gitcmds.current_branch())

        (self.staged,
         self.modified,
         self.unmerged,
         self.untracked,
         self.upstream_changed) = gitcmds.worktree_state(head=head,
                                                staged_only=staged_only)
        # NOTE: the model's unstaged list holds an aggregate of the
        # the modified, unmerged, and untracked file lists.
        self.set_unstaged(self.modified + self.unmerged + self.untracked)
        self.set_remotes(self.git.remote().splitlines())
        self.set_tags(gitcmds.tag_list())
        self.set_remote_branches(gitcmds.branch_list(remote=True))
        self.set_local_branches(gitcmds.branch_list(remote=False))
        self.set_revision('')
        self.set_local_branch('')
        self.set_remote_branch('')
        # Re-enable notifications and emit changes
        self.notification_enabled = notify_enabled

        self.read_font_sizes()
        self.notify_observers('staged', 'unstaged')
        self.notify_message_observers(self.message_updated)

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

    def filename(self, idx, staged=True):
        try:
            if staged:
                return self.staged[idx]
            else:
                return self.unstaged[idx]
        except IndexError:
            return None

    def stage_modified(self):
        status, output = self.git.add(v=True,
                                      with_stderr=True,
                                      with_status=True,
                                      *self.modified)
        self.update_status()
        return (status, output)

    def stage_untracked(self):
        status, output = self.git.add(v=True,
                                      with_stderr=True,
                                      with_status=True,
                                      *self.untracked)
        self.update_status()
        return (status, output)

    def reset(self, *items):
        status, output = self.git.reset('--',
                                        with_stderr=True,
                                        with_status=True,
                                        *items)
        self.update_status()
        return (status, output)

    def unstage_all(self):
        status, output = self.git.reset(with_stderr=True,
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
                # the user has an invalid entry in their git config
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

    def git_repo_path(self, *subpaths):
        paths = [self.git.git_dir()]
        paths.extend(subpaths)
        return os.path.realpath(os.path.join(*paths))

    def merge_message_path(self):
        for basename in ('MERGE_MSG', 'SQUASH_MSG'):
            path = self.git_repo_path(basename)
            if os.path.exists(path):
                return path
        return None

    def merge_message(self):
        return self.git.fmt_merge_msg('--file',
                                      self.git_repo_path('FETCH_HEAD'))

    def abort_merge(self):
        # Reset the worktree
        output = self.git.read_tree('HEAD', reset=True, u=True, v=True)
        # remove MERGE_HEAD
        merge_head = self.git_repo_path('MERGE_HEAD')
        if os.path.exists(merge_head):
            os.unlink(merge_head)
        # remove MERGE_MESSAGE, etc.
        merge_msg_path = self.merge_message_path()
        while merge_msg_path:
            os.unlink(merge_msg_path)
            merge_msg_path = self.merge_message_path()

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

    def parse_stash_list(self, revids=False):
        """Parses "git stash list" and returns a list of stashes."""
        stashes = self.git.stash("list").splitlines()
        if revids:
            return [ s[:s.index(':')] for s in stashes ]
        else:
            return [ s[s.index(':')+1:] for s in stashes ]

    def pad(self, pstr, num=22):
        topad = num-len(pstr)
        if topad > 0:
            return pstr + ' '*topad
        else:
            return pstr

    def describe(self, revid, descr):
        version = self.git.describe(revid, tags=True, always=True,
                                    abbrev=4)
        return version + ' - ' + descr

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
        add = []
        remove = []
        for path in set(paths):
            if os.path.exists(core.encode(path)):
                add.append(path)
            else:
                remove.append(path)
        # `git add -u` doesn't work on untracked files
        if add:
            self.git.add('--', *add)
        # If a path doesn't exist then that means it should be removed
        # from the index.   We use `git add -u` for that.
        if remove:
            self.git.add('--', u=True, *remove)
        self.update_status()

    def getcwd(self):
        """If we've chosen a directory then use it, otherwise os.getcwd()."""
        if self.directory:
            return self.directory
        return os.getcwd()
