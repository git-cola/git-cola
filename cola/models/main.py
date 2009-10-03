# Copyright (c) 2008 David Aguilar
"""This module provides the central cola model.
"""

import os
import sys
import re
import time
import subprocess
from cStringIO import StringIO

from cola import gitcola
from cola import core
from cola import utils
from cola import errors
from cola.models.observable import ObservableModel

#+-------------------------------------------------------------------------
#+ A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile('([0-9a-f]+)\W(.*)')

# Provides access to a global MainModel instance
_instance = None
def model():
    """Returns the main model singleton"""
    global _instance
    if _instance:
        return _instance
    _instance = MainModel()
    return _instance


def eval_path(path):
    """handles quoted paths."""
    if path.startswith('"') and path.endswith('"'):
        return core.decode(eval(path))
    else:
        return path


class MainModel(ObservableModel):
    """Provides a friendly wrapper for doing common git operations."""

    # Observable messages
    message_updated = 'updated'
    message_about_to_update = 'about_to_update'
    message_paths_staged   = 'paths_staged'
    message_paths_unstaged = 'paths_unstaged'
    message_paths_reverted = 'paths_reverted'

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
        self.git = gitcola.GitCola()

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

        # These are parallel lists
        # ref^{tree}
        self.types = []
        self.sha1s = []
        self.names = []

        self.directories = []
        self.directory_entries = {}

        # parallel lists
        self.subtree_types = []
        self.subtree_sha1s = []
        self.subtree_names = []

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

    def all_files(self):
        """Returns the names of all files in the repository"""
        return [core.decode(f)
                for f in self.git.ls_files(z=True)
                                 .strip('\0').split('\0') if f]

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
        self.__global_defaults = {
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

        global_defaults = self.__global_defaults
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

    def branch_list(self, remote=False):
        """Returns a list of local or remote branches

        This explicitly removes HEAD from the list of remote branches.
        """
        branches = map(lambda x: x.lstrip('* '),
                self.git.branch(r=remote).splitlines())
        if remote:
            return [b for b in branches if b.find('/HEAD') == -1]
        return branches

    def config_params(self):
        params = []
        params.extend(map(lambda x: 'local_' + x,
                          self._local_and_global_defaults.keys()))
        params.extend(map(lambda x: 'global_' + x,
                          self._local_and_global_defaults.keys()))
        params.extend(map(lambda x: 'global_' + x,
                          self.__global_defaults.keys()))
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

    def init_browser_data(self):
        """This scans over self.(names, sha1s, types) to generate
        directories, directory_entries, and subtree_*"""

        # Collect data for the model
        if not self.currentbranch:
            return

        self.subtree_types = []
        self.subtree_sha1s = []
        self.subtree_names = []
        self.directories = []
        self.directory_entries = {}

        # Lookup the tree info
        tree_info = self.parse_ls_tree(self.currentbranch)

        self.set_types(map(lambda(x): x[1], tree_info ))
        self.set_sha1s(map(lambda(x): x[2], tree_info ))
        self.set_names(map(lambda(x): x[3], tree_info ))

        if self.directory: self.directories.append('..')

        dir_entries = self.directory_entries
        dir_regex = re.compile('([^/]+)/')
        dirs_seen = {}
        subdirs_seen = {}

        for idx, name in enumerate(self.names):
            if not name.startswith(self.directory):
                continue
            name = name[ len(self.directory): ]
            if name.count('/'):
                # This is a directory...
                match = dir_regex.match(name)
                if not match:
                    continue
                dirent = match.group(1) + '/'
                if dirent not in self.directory_entries:
                    self.directory_entries[dirent] = []

                if dirent not in dirs_seen:
                    dirs_seen[dirent] = True
                    self.directories.append(dirent)

                entry = name.replace(dirent, '')
                entry_match = dir_regex.match(entry)
                if entry_match:
                    subdir = entry_match.group(1) + '/'
                    if subdir in subdirs_seen:
                        continue
                    subdirs_seen[subdir] = True
                    dir_entries[dirent].append(subdir)
                else:
                    dir_entries[dirent].append(entry)
            else:
                self.subtree_types.append(self.types[idx])
                self.subtree_sha1s.append(self.sha1s[idx])
                self.subtree_names.append(name)

    def add_or_remove(self, to_process):
        """Invokes 'git add' to index the filenames in to_process that exist
        and 'git rm' for those that do not exist."""

        if not to_process:
            return 'No files to add or remove.'

        to_add = []
        to_remove = []

        for filename in to_process:
            encfilename = core.encode(filename)
            if os.path.exists(encfilename):
                to_add.append(filename)

        status = 0
        if to_add:
            newstatus, output = self.git.add(v=True,
                                             with_stderr=True,
                                             with_status=True,
                                             *to_add)
            status += newstatus
        else:
            output = ''

        if len(to_add) == len(to_process):
            # to_process only contained unremoved files --
            # short-circuit the removal checks
            return (status, output)

        # Process files to remote
        for filename in to_process:
            if not os.path.exists(filename):
                to_remove.append(filename)
        newstatus, out = self.git.rm(with_stderr=True,
                                     with_status=True,
                                     *to_remove)
        if status == 0:
            status += newstatus
        output + '\n\n' + out
        return (status, output)

    def editor(self):
        return self.gui_config('editor')

    def history_browser(self):
        return self.gui_config('historybrowser')

    def remember_gui_settings(self):
        return self.cola_config('savewindowsettings')

    def subtree_node(self, idx):
        return (self.subtree_types[idx],
                self.subtree_sha1s[idx],
                self.subtree_names[idx])

    def all_branches(self):
        return (self.local_branches + self.remote_branches)

    def set_remote(self, remote):
        if not remote:
            return
        self.set_param('remote', remote)
        branches = utils.grep('%s/\S+$' % remote,
                              self.branch_list(remote=True),
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
        self.set_currentbranch(self.current_branch())
        self.set_trackedbranch(self.tracked_branch())

        (self.staged,
         self.modified,
         self.unmerged,
         self.untracked,
         self.upstream_changed) = self.worktree_state(head=head,
                                                      staged_only=staged_only)
        # NOTE: the model's unstaged list holds an aggregate of the
        # the modified, unmerged, and untracked file lists.
        self.set_unstaged(self.modified + self.unmerged + self.untracked)
        self.set_remotes(self.git.remote().splitlines())
        self.set_remote_branches(self.branch_list(remote=True))
        self.set_local_branches(self.branch_list(remote=False))
        self.set_tags(self.git.tag().splitlines())
        self.set_revision('')
        self.set_local_branch('')
        self.set_remote_branch('')
        # Re-enable notifications and emit changes
        self.notification_enabled = notify_enabled

        self.read_font_sizes()
        self.notify_observers('staged','unstaged')
        self.notify_message_observers(self.message_updated)

    def read_font_sizes(self):
        """Read font sizes from the configuration."""
        value = self.cola_config('fontdiff')
        if not value:
            return
        items = value.split(',')
        if len(items) < 2:
            return
        self.global_cola_fontdiff_size = int(items[1])

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

    def commit_diff(self, sha1):
        commit = self.git.show(sha1)
        first_newline = commit.index('\n')
        if commit[first_newline+1:].startswith('Merge:'):
            return (core.decode(commit) + '\n\n' +
                    core.decode(self.diff_helper(commit=sha1,
                                                 cached=False,
                                                 suppress_header=False)))
        else:
            return core.decode(commit)

    def filename(self, idx, staged=True):
        try:
            if staged:
                return self.staged[idx]
            else:
                return self.unstaged[idx]
        except IndexError:
            return None

    def diff_details(self, idx, ref, staged=True):
        """
        Return a "diff" for an entry by index relative to ref.

        `staged` indicates whether we should consider this as a
        staged or unstaged entry.

        """
        filename = self.filename(idx, staged=staged)
        if not filename:
            return (None, None)
        encfilename = core.encode(filename)
        if staged:
            diff = self.diff_helper(filename=filename,
                                    ref=ref,
                                    cached=True)
        else:
            if os.path.isdir(encfilename):
                diff = '\n'.join(os.listdir(filename))

            elif filename in self.unmerged:
                diff = ('@@@ Unmerged @@@\n'
                        '- %s is unmerged.\n+ ' % filename +
                        'Right-click the file to launch "git mergetool".\n'
                        '@@@ Unmerged @@@\n\n')
                diff += self.diff_helper(filename=filename,
                                        cached=False)
            elif filename in self.modified:
                diff = self.diff_helper(filename=filename,
                                        cached=False)
            else:
                diff = 'SHA1: ' + self.git.hash_object(filename)
        return (diff, filename)

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

    def log_helper(self, all=False, extra_args=None):
        """
        Returns a pair of parallel arrays listing the revision sha1's
        and commit summaries.
        """
        revs = []
        summaries = []
        regex = REV_LIST_REGEX
        args = []
        if extra_args:
            args = extra_args
        output = self.git.log(pretty='oneline', all=all, *args)
        for line in map(core.decode, output.splitlines()):
            match = regex.match(line)
            if match:
                revs.append(match.group(1))
                summaries.append(match.group(2))
        return (revs, summaries)

    def parse_rev_list(self, raw_revs):
        revs = []
        for line in map(core.decode, raw_revs.splitlines()):
            match = REV_LIST_REGEX.match(line)
            if match:
                rev_id = match.group(1)
                summary = match.group(2)
                revs.append((rev_id, summary,))
        return revs

    def rev_list_range(self, start, end):
        range = '%s..%s' % (start, end)
        raw_revs = self.git.rev_list(range, pretty='oneline')
        return self.parse_rev_list(raw_revs)

    def diff_helper(self,
                    commit=None,
                    branch=None,
                    ref=None,
                    endref=None,
                    filename=None,
                    cached=True,
                    with_diff_header=False,
                    suppress_header=True,
                    reverse=False):
        "Invokes git diff on a filepath."
        if commit:
            ref, endref = commit+'^', commit
        argv = []
        if ref and endref:
            argv.append('%s..%s' % (ref, endref))
        elif ref:
            for r in ref.strip().split():
                argv.append(r)
        elif branch:
            argv.append(branch)

        if filename:
            argv.append('--')
            if type(filename) is list:
                argv.extend(filename)
            else:
                argv.append(filename)

        start = False
        del_tag = 'deleted file mode '

        headers = []
        deleted = cached and not os.path.exists(core.encode(filename))

        diffoutput = self.git.diff(R=reverse,
                                   M=True,
                                   no_color=True,
                                   cached=cached,
                                   unified=self.diff_context,
                                   with_raw_output=True,
                                   with_stderr=True,
                                   *argv)

        # Handle 'git init'
        if diffoutput.startswith('fatal:'):
            if with_diff_header:
                return ('', '')
            else:
                return ''

        output = StringIO()

        diff = diffoutput.split('\n')
        for line in map(core.decode, diff):
            if not start and '@@' == line[:2] and '@@' in line[2:]:
                start = True
            if start or (deleted and del_tag in line):
                output.write(core.encode(line) + '\n')
            else:
                if with_diff_header:
                    headers.append(core.encode(line))
                elif not suppress_header:
                    output.write(core.encode(line) + '\n')

        result = core.decode(output.getvalue())
        output.close()

        if with_diff_header:
            return('\n'.join(headers), result)
        else:
            return result

    def git_repo_path(self, *subpaths):
        paths = [self.git.git_dir()]
        paths.extend(subpaths)
        return os.path.realpath(os.path.join(*paths))

    def merge_message_path(self):
        for file in ('MERGE_MSG', 'SQUASH_MSG'):
            path = self.git_repo_path(file)
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

    def _is_modified(self, name):
        status, out = self.git.diff('--', name,
                                    name_only=True,
                                    exit_code=True,
                                    with_status=True)
        return status != 0


    def _branch_status(self, branch):
        """
        Returns a tuple of staged, unstaged, untracked, and unmerged files

        This shows only the changes that were introduced in branch

        """
        status, output = self.git.diff(name_only=True,
                                       M=True, z=True,
                                       with_stderr=True,
                                       with_status=True,
                                       *branch.strip().split())
        if status != 0:
            return ([], [], [], [], [])
        staged = []
        for name in output.strip('\0').split('\0'):
            if not name:
                continue
            staged.append(core.decode(name))

        return (staged, [], [], [], staged)

    def worktree_state(self, head='HEAD', staged_only=False):
        """Return a tuple of files in various states of being

        Can be staged, unstaged, untracked, unmerged, or changed
        upstream.

        """
        self.git.update_index(refresh=True)
        if staged_only:
            return self._branch_status(head)

        staged_set = set()
        modified_set = set()
        upstream_changed_set = set()

        (staged, modified, unmerged, untracked, upstream_changed) = (
                [], [], [], [], [])
        try:
            output = self.git.diff_index(head,
                                         cached=True,
                                         with_stderr=True)
            if output.startswith('fatal:'):
                raise errors.GitInitError('git init')
            for line in output.splitlines():
                rest, name = line.split('\t', 1)
                status = rest[-1]
                name = eval_path(name)
                if status  == 'M':
                    staged.append(name)
                    staged_set.add(name)
                    # This file will also show up as 'M' without --cached
                    # so by default don't consider it modified unless
                    # it's truly modified
                    modified_set.add(name)
                    if not staged_only and self._is_modified(name):
                        modified.append(name)
                elif status == 'A':
                    staged.append(name)
                    staged_set.add(name)
                elif status == 'D':
                    staged.append(name)
                    staged_set.add(name)
                    modified_set.add(name)
                elif status == 'U':
                    unmerged.append(name)
                    modified_set.add(name)

        except errors.GitInitError:
            # handle git init
            staged.extend(self.all_files())

        try:
            output = self.git.diff_index(head, with_stderr=True)
            if output.startswith('fatal:'):
                raise errors.GitInitError('git init')
            for line in output.splitlines():
                info, name = line.split('\t', 1)
                status = info.split()[-1]
                if status == 'M' or status == 'D':
                    name = eval_path(name)
                    if name not in modified_set:
                        modified.append(name)
                elif status == 'A':
                    name = eval_path(name)
                    # newly-added yet modified
                    if (name not in modified_set and not staged_only and
                            self._is_modified(name)):
                        modified.append(name)

        except errors.GitInitError:
            # handle git init
            for name in (self.git.ls_files(modified=True, z=True)
                                 .split('\0')):
                if name:
                    modified.append(core.decode(name))

        for name in self.git.ls_files(others=True, exclude_standard=True,
                                      z=True).split('\0'):
            if name:
                untracked.append(core.decode(name))

        # Look for upstream modified files if this is a tracking branch
        if self.trackedbranch:
            try:
                diff_expr = self.merge_base_to(self.trackedbranch)
                output = self.git.diff(diff_expr,
                                       name_only=True, z=True)
                if output.startswith('fatal:'):
                    raise errors.GitInitError('git init')
                for name in output.split('\0'):
                    if not name:
                        continue
                    name = core.decode(name)
                    upstream_changed.append(name)
                    upstream_changed_set.add(name)

            except errors.GitInitError:
                # handle git init
                pass

        # Keep stuff sorted
        staged.sort()
        modified.sort()
        unmerged.sort()
        untracked.sort()
        upstream_changed.sort()

        return (staged, modified, unmerged, untracked, upstream_changed)

    def reset_helper(self, args):
        """Removes files from the index

        This handles the git init case, which is why it's not
        just 'git reset name'.  For the git init case this falls
        back to 'git rm --cached'.

        """
        # fake the status because 'git reset' returns 1
        # regardless of success/failure
        status = 0
        output = self.git.reset('--', with_stderr=True, *args)
        # handle git init: we have to use 'git rm --cached'
        # detect this condition by checking if the file is still staged
        state = self.worktree_state()
        staged = state[0]
        rmargs = [a for a in args if a in staged]
        if not rmargs:
            return (status, output)
        output += self.git.rm('--', cached=True, with_stderr=True, *rmargs)
        return (status, output)

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

    def parse_ls_tree(self, rev):
        """Returns a list of(mode, type, sha1, path) tuples."""
        lines = self.git.ls_tree(rev, r=True).splitlines()
        output = []
        regex = re.compile('^(\d+)\W(\w+)\W(\w+)[ \t]+(.*)$')
        for line in lines:
            match = regex.match(line)
            if match:
                mode = match.group(1)
                objtype = match.group(2)
                sha1 = match.group(3)
                filename = match.group(4)
                output.append((mode, objtype, sha1, filename,) )
        return output

    def format_patch_helper(self, to_export, revs, output='patches'):
        """writes patches named by to_export to the output directory."""

        outlines = []

        cur_rev = to_export[0]
        cur_master_idx = revs.index(cur_rev)

        patches_to_export = [ [cur_rev] ]
        patchset_idx = 0

        # Group the patches into continuous sets
        for idx, rev in enumerate(to_export[1:]):
            # Limit the search to the current neighborhood for efficiency
            master_idx = revs[ cur_master_idx: ].index(rev)
            master_idx += cur_master_idx
            if master_idx == cur_master_idx + 1:
                patches_to_export[ patchset_idx ].append(rev)
                cur_master_idx += 1
                continue
            else:
                patches_to_export.append([ rev ])
                cur_master_idx = master_idx
                patchset_idx += 1

        # Export each patchsets
        status = 0
        for patchset in patches_to_export:
            newstatus, out = self.export_patchset(patchset[0],
                                                  patchset[-1],
                                                  output='patches',
                                                  n=len(patchset) > 1,
                                                  thread=True,
                                                  patch_with_stat=True)
            outlines.append(out)
            if status == 0:
                status += newstatus
        return (status, '\n'.join(outlines))

    def export_patchset(self, start, end, output="patches", **kwargs):
        revarg = '%s^..%s' % (start, end)
        return self.git.format_patch('-o', output, revarg,
                                     with_stderr=True,
                                     with_status=True,
                                     **kwargs)

    def current_branch(self):
        """Parses 'git symbolic-ref' to find the current branch."""
        headref = self.git.symbolic_ref('HEAD', with_stderr=True)
        if headref.startswith('refs/heads/'):
            return headref[11:]
        elif headref.startswith('fatal:'):
            return ''
        return headref

    def tracked_branch(self):
        """The name of the branch that current branch is tracking"""
        remote = self.git.config('branch.'+self.currentbranch+'.remote',
                                 get=True, with_stderr=True)
        if not remote:
            return ''
        headref = self.git.config('branch.'+self.currentbranch+'.merge',
                                  get=True, with_stderr=True)
        if headref.startswith('refs/heads/'):
            tracked_branch = headref[11:]
            return remote + '/' + tracked_branch
        return ''

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

    def update_revision_lists(self, filename=None, show_versions=False):
        num_results = self.num_results
        if filename:
            rev_list = self.git.log('--', filename,
                                    max_count=num_results,
                                    pretty='oneline')
        else:
            rev_list = self.git.log(max_count=num_results,
                                    pretty='oneline', all=True)

        commit_list = self.parse_rev_list(rev_list)
        commit_list.reverse()
        commits = map(lambda x: x[0], commit_list)
        descriptions = map(lambda x: core.decode(x[1]), commit_list)
        if show_versions:
            fancy_descr_list = map(lambda x: self.describe(*x), commit_list)
            self.set_descriptions_start(fancy_descr_list)
            self.set_descriptions_end(fancy_descr_list)
        else:
            self.set_descriptions_start(descriptions)
            self.set_descriptions_end(descriptions)

        self.set_revisions_start(commits)
        self.set_revisions_end(commits)

        return commits

    def changed_files(self, start, end):
        zfiles_str = self.git.diff('%s..%s' % (start, end),
                                   name_only=True, z=True).strip('\0')
        return [core.decode(enc) for enc in zfiles_str.split('\0') if enc]

    def renamed_files(self, start, end):
        difflines = self.git.diff('%s..%s' % (start, end),
                                  no_color=True,
                                  M=True).splitlines()
        return [ eval_path(r[12:].rstrip())
                    for r in difflines if r.startswith('rename from ') ]

    def is_commit_published(self):
        head = self.git.rev_parse('HEAD')
        return bool(self.git.branch(r=True, contains=head))

    def merge_base_to(self, ref):
        """Given `ref`, return $(git merge-base ref HEAD)..ref."""
        base = self.git.merge_base('HEAD', ref)
        return '%s..%s' % (base, ref)

    def everything(self):
        """Returns a sorted list of all files, including untracked files."""
        files = self.all_files() + self.untracked
        files.sort()
        return files

    def stage_paths(self, paths):
        """Adds paths to git and notifies observers."""

        # Grab the old lists of untracked + modified files
        self.update_status()
        old_modified = set(self.modified)
        old_untracked = set(self.untracked)

        # Add paths and scan for changes
        paths = set(paths)
        for path in paths:
            # If a path doesn't exist then that means it should be removed
            # from the index.   We use `git add -u` for that.
            # GITBUG: `git add -u` doesn't on untracked files.
            if os.path.exists(core.encode(path)):
                self.git.add('--', path)
            else:
                self.git.add('--', path, u=True)
        self.update_status()

        # Grab the new lists of untracked + modified files
        new_modified = set(self.modified)
        new_untracked = set(self.untracked)

        # Handle 'git add' on a directory
        newly_not_modified = utils.add_parents(old_modified - new_modified)
        newly_not_untracked = utils.add_parents(old_untracked - new_untracked)
        for path in newly_not_modified.union(newly_not_untracked):
            paths.add(path)

        self.notify_message_observers(self.message_paths_staged, paths=paths)

    def unstage_paths(self, paths):
        """Unstages paths from the staging area and notifies observers."""
        paths = set(paths)

        # Grab the old list of staged files
        self.update_status()
        old_staged = set(self.staged)

        # Reset and scan for new changes
        self.reset_helper(paths)
        self.update_status()

        # Grab the new list of staged file
        new_staged = set(self.staged)

        # Handle 'git reset' on a directory
        newly_unstaged = utils.add_parents(old_staged - new_staged)
        for path in newly_unstaged:
            paths.add(path)

        self.notify_message_observers(self.message_paths_unstaged, paths=paths)

    def revert_paths(self, paths):
        """Revert paths to the content from HEAD."""
        paths = set(paths)

        # Grab the old set of changed files
        self.update_status()
        old_modified = set(self.modified)
        old_staged = set(self.staged)
        old_changed = old_modified.union(old_staged)

        # Checkout and scan for changes
        self.git.checkout('HEAD', '--', *paths)
        self.update_status()

        # Grab the new set of changed files
        new_modified = set(self.modified)
        new_staged = set(self.staged)
        new_changed = new_modified.union(new_staged)

        # Handle 'git checkout' on a directory
        newly_reverted = utils.add_parents(old_changed - new_changed)

        for path in newly_reverted:
            paths.add(path)

        self.notify_message_observers(self.message_paths_reverted, paths=paths)

    def getcwd(self):
        """If we've chosen a directory then use it, otherwise os.getcwd()."""
        if self.directory:
            return self.directory
        return os.getcwd()
