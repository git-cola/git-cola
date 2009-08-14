# Copyright (c) 2008 David Aguilar
"""This module provides the cola model class.
"""

import os
import sys
import re
import time
import subprocess
from cStringIO import StringIO

from cola import git
from cola import core
from cola import utils
from cola import errors
from cola.models.observable import ObservableModel

#+-------------------------------------------------------------------------
#+ A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile('([0-9a-f]+)\W(.*)')

class GitInitError(errors.ColaError):
    pass

class GitCola(git.Git):
    """GitPython throws exceptions by default.
    We suppress exceptions in favor of return values.
    """
    def __init__(self):
        git.Git.__init__(self)
        self.load_worktree(os.getcwd())

    def load_worktree(self, path):
        self._git_dir = path
        self._work_tree = None
        self.get_work_tree()

    def get_work_tree(self):
        if self._work_tree:
            return self._work_tree
        self.get_git_dir()
        if self._git_dir:
            curdir = self._git_dir
        else:
            curdir = os.getcwd()

        if self._is_git_dir(os.path.join(curdir, '.git')):
            return curdir

        # Handle bare repositories
        if (len(os.path.basename(curdir)) > 4
                and curdir.endswith('.git')):
            return curdir
        if 'GIT_WORK_TREE' in os.environ:
            self._work_tree = os.getenv('GIT_WORK_TREE')
        if not self._work_tree or not os.path.isdir(self._work_tree):
            if self._git_dir:
                gitparent = os.path.join(os.path.abspath(self._git_dir), '..')
                self._work_tree = os.path.abspath(gitparent)
                self.set_cwd(self._work_tree)
        return self._work_tree

    def is_valid(self):
        return self._git_dir and self._is_git_dir(self._git_dir)

    def get_git_dir(self):
        if self.is_valid():
            return self._git_dir
        if 'GIT_DIR' in os.environ:
            self._git_dir = os.getenv('GIT_DIR')
        if self._git_dir:
            curpath = os.path.abspath(self._git_dir)
        else:
            curpath = os.path.abspath(os.getcwd())
        # Search for a .git directory
        while curpath:
            if self._is_git_dir(curpath):
                self._git_dir = curpath
                break
            gitpath = os.path.join(curpath, '.git')
            if self._is_git_dir(gitpath):
                self._git_dir = gitpath
                break
            curpath, dummy = os.path.split(curpath)
            if not dummy:
                break
        return self._git_dir

    def _is_git_dir(self, d):
        """ This is taken from the git setup.c:is_git_directory
            function."""
        if (os.path.isdir(d)
                and os.path.isdir(os.path.join(d, 'objects'))
                and os.path.isdir(os.path.join(d, 'refs'))):
            headref = os.path.join(d, 'HEAD')
            return (os.path.isfile(headref)
                    or (os.path.islink(headref)
                    and os.readlink(headref).startswith('refs')))
        return False

def eval_path(path):
    """handles quoted paths."""
    if path.startswith('"') and path.endswith('"'):
        return core.decode(eval(path))
    else:
        return path

class MainModel(ObservableModel):
    """Provides a friendly wrapper for doing common git operations."""

    def __init__(self):
        """Reads git repository settings and sets several methods
        so that they refer to the git module.  This object
        encapsulates cola's interaction with git."""
        ObservableModel.__init__(self)

        # Initialize the git command object
        self.git = GitCola()

        #####################################################
        # Used in various places
        self.currentbranch = ''
        self.directory = ''
        self.remotes = []
        self.remotename = ''
        self.local_branch = ''
        self.remote_branch = ''
        self.search_text = ''

        #####################################################
        # Used primarily by the main UI
        self.commitmsg = ''
        self.modified = []
        self.staged = []
        self.unstaged = []
        self.untracked = []
        self.unmerged = []

        #####################################################
        # Used by the create branch dialog
        self.revision = ''
        self.local_branches = []
        self.remote_branches = []
        self.tags = []

        #####################################################
        # Used by the commit/repo browser
        self.revisions = []
        self.summaries = []

        # These are parallel lists
        self.types = []
        self.sha1s = []
        self.names = []

        # All items below here are re-calculated in
        # init_browser_data()
        self.directories = []
        self.directory_entries = {}

        # These are also parallel lists
        self.subtree_types = []
        self.subtree_sha1s = []
        self.subtree_names = []

        self.fetch_helper = None
        self.push_helper = None
        self.pull_helper = None
        self.generate_remote_helpers()

    def all_files(self):
        """Returns the names of all files in the repository"""
        return [core.decode(f)
                for f in self.git.ls_files(z=True)
                                 .strip('\0').split('\0') if f]

    def generate_remote_helpers(self):
        """Generates helper methods for fetch, push and pull"""
        self.fetch_helper = self.gen_remote_helper(self.git.fetch)
        self.push_helper = self.gen_remote_helper(self.git.push)
        self.pull_helper = self.gen_remote_helper(self.git.pull)

    def use_worktree(self, worktree):
        self.git.load_worktree(worktree)
        is_valid = self.git.is_valid()
        if is_valid:
            self.__init_config_data()
        return is_valid

    def __init_config_data(self):
        """Reads git config --list and creates parameters
        for each setting."""
        # These parameters are saved in .gitconfig,
        # so ideally these should be as short as possible.

        # config items that are controllable globally
        # and per-repository
        self.__local_and_global_defaults = {
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
            'cola_fontui': '',
            'cola_fontui_size': 12,
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
        for param in ('global_cola_fontui', 'global_cola_fontdiff'):
            setdefault = True
            if hasattr(self, param):
                font = self.get_param(param)
                if font:
                    setdefault = False
                    size = int(font.split(',')[1])
                    self.set_param(param+'_size', size)
                    param = param[len('global_'):]
                    global_dict[param] = font
                    global_dict[param+'_size'] = size

        # Load defaults for all undefined items
        local_and_global_defaults = self.__local_and_global_defaults
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
        self.diff_context = self.get_local_config('gui.diffcontext', 3)

    def get_global_config(self, key, default=None):
        return self.get_param('global_'+key.replace('.', '_'),
                              default=default)

    def get_local_config(self, key, default=None):
        return self.get_param('local_'+key.replace('.', '_'),
                              default=default)

    def get_cola_config(self, key):
        return getattr(self, 'global_cola_'+key)

    def get_gui_config(self, key):
        return getattr(self, 'global_gui_'+key)

    def get_default_remote(self):
        branch = self.get_currentbranch()
        branchconfig = 'branch.%s.remote' % branch
        return self.get_local_config(branchconfig, 'origin')

    def get_corresponding_remote_ref(self):
        remote = self.get_default_remote()
        branch = self.get_currentbranch()
        best_match = '%s/%s' % (remote, branch)
        remote_branches = self.get_remote_branches()
        if not remote_branches:
            return remote
        for rb in remote_branches:
            if rb == best_match:
                return rb
        return remote_branches[0]

    def get_diff_filenames(self, arg):
        """Returns a list of filenames that have been modified"""
        diff_zstr = self.git.diff(arg, name_only=True, z=True).rstrip('\0')
        return [core.decode(f) for f in diff_zstr.split('\0') if f]

    def branch_list(self, remote=False):
        """Returns a list of local or remote branches
        
        This explicitly removes HEAD from the list of remote branches.
        """
        branches = map(lambda x: x.lstrip('* '),
                self.git.branch(r=remote).splitlines())
        if remote:
            return [b for b in branches if b.find('/HEAD') == -1]
        return branches

    def get_config_params(self):
        params = []
        params.extend(map(lambda x: 'local_' + x,
                          self.__local_and_global_defaults.keys()))
        params.extend(map(lambda x: 'global_' + x,
                          self.__local_and_global_defaults.keys()))
        params.extend(map(lambda x: 'global_' + x,
                          self.__global_defaults.keys()))
        return [ p for p in params if not p.endswith('_size') ]

    def save_config_param(self, param):
        if param not in self.get_config_params():
            return
        value = self.get_param(param)
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
        if not self.get_currentbranch():
            return

        self.subtree_types = []
        self.subtree_sha1s = []
        self.subtree_names = []
        self.directories = []
        self.directory_entries = {}

        # Lookup the tree info
        tree_info = self.parse_ls_tree(self.get_currentbranch())

        self.set_types(map( lambda(x): x[1], tree_info ))
        self.set_sha1s(map( lambda(x): x[2], tree_info ))
        self.set_names(map( lambda(x): x[3], tree_info ))

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
        return self.get_cola_config('savewindowsettings')

    def should_display_log(self, status):
        """Returns whether we should display the log window

        This implements the behavior of the cola.showoutput variable.
            never = never open the log window
            always = open it always
            errors = only open it on error (handled implicitly)

        """
        conf = self.get_cola_config('showoutput')
        if conf == 'never':
            return False
        if conf == 'always':
            return True
        return status != 0

    def get_tree_node(self, idx):
        return (self.get_types()[idx],
                self.get_sha1s()[idx],
                self.get_names()[idx] )

    def get_subtree_node(self, idx):
        return (self.get_subtree_types()[idx],
                self.get_subtree_sha1s()[idx],
                self.get_subtree_names()[idx] )

    def get_all_branches(self):
        return (self.get_local_branches() + self.get_remote_branches())

    def set_remote(self, remote):
        if not remote:
            return
        self.set_param('remote', remote)
        branches = utils.grep('%s/\S+$' % remote,
                              self.branch_list(remote=True),
                              squash=False)
        self.set_remote_branches(branches)

    def add_signoff(self,*rest):
        """Adds a standard Signed-off by: tag to the end
        of the current commit message."""
        msg = self.get_commitmsg()
        signoff =('\n\nSigned-off-by: %s <%s>\n'
                  % (self.get_local_user_name(), self.get_local_user_email()))
        if signoff not in msg:
            self.set_commitmsg(msg + signoff)

    def apply_diff(self, filename):
        return self.git.apply(filename, index=True, cached=True)

    def apply_diff_to_worktree(self, filename):
        return self.git.apply(filename)

    def load_commitmsg(self, path):
        fh = open(path, 'r')
        contents = core.decode(core.read_nointr(fh))
        fh.close()
        self.set_commitmsg(contents)

    def get_prev_commitmsg(self,*rest):
        """Queries git for the latest commit message and sets it in
        self.commitmsg."""
        commit_msg = []
        commit_lines = core.decode(self.git.show('HEAD')).split('\n')
        for idx, msg in enumerate(commit_lines):
            if idx < 4:
                continue
            msg = msg.lstrip()
            if msg.startswith('diff --git'):
                commit_msg.pop()
                break
            commit_msg.append(msg)
        self.set_commitmsg('\n'.join(commit_msg).rstrip())

    def load_commitmsg_template(self):
        template = self.get_global_config('commit.template')
        if template:
            self.load_commitmsg(template)

    def update_status(self, head='HEAD', staged_only=False):
        # This allows us to defer notification until the
        # we finish processing data
        notify_enabled = self.notification_enabled
        self.notification_enabled = False

        (self.staged,
         self.modified,
         self.unmerged,
         self.untracked) = self.get_workdir_state(head=head,
                                                  staged_only=staged_only)
        # NOTE: the model's unstaged list holds an aggregate of the
        # the modified, unmerged, and untracked file lists.
        self.set_unstaged(self.modified + self.unmerged + self.untracked)
        self.set_currentbranch(self.current_branch())
        self.set_remotes(self.git.remote().splitlines())
        self.set_remote_branches(self.branch_list(remote=True))
        self.set_local_branches(self.branch_list(remote=False))
        self.set_tags(self.git.tag().splitlines())
        self.set_revision('')
        self.set_local_branch('')
        self.set_remote_branch('')
        # Re-enable notifications and emit changes
        self.notification_enabled = notify_enabled
        self.notify_observers('staged','unstaged')

    def delete_branch(self, branch):
        return self.git.branch(branch,
                               D=True,
                               with_stderr=True,
                               with_status=True)

    def get_revision_sha1(self, idx):
        return self.get_revisions()[idx]

    def apply_font_size(self, param, default):
        old_font = self.get_param(param)
        if not old_font:
            old_font = default
        size = self.get_param(param+'_size')
        props = old_font.split(',')
        props[1] = str(size)
        new_font = ','.join(props)

        self.set_param(param, new_font)

    def get_commit_diff(self, sha1):
        commit = self.git.show(sha1)
        first_newline = commit.index('\n')
        if commit[first_newline+1:].startswith('Merge:'):
            return (core.decode(commit) + '\n\n' +
                    core.decode(self.diff_helper(commit=sha1,
                                                 cached=False,
                                                 suppress_header=False)))
        else:
            return core.decode(commit)

    def get_filename(self, idx, staged=True):
        try:
            if staged:
                return self.get_staged()[idx]
            else:
                return self.get_unstaged()[idx]
        except IndexError:
            return None

    def get_diff_details(self, idx, ref, staged=True):
        """
        Return a "diff" for an entry by index relative to ref.

        `staged` indicates whether we should consider this as a
        staged or unstaged entry.

        """
        filename = self.get_filename(idx, staged=staged)
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

            elif filename in self.get_unmerged():
                diff = ('@@@ Unmerged @@@\n'
                        '- %s is unmerged.\n+ ' % filename +
                        'Right-click the file to launch "git mergetool".\n'
                        '@@@ Unmerged @@@\n\n')
                diff += self.diff_helper(filename=filename,
                                        cached=False,
                                        patch_with_raw=False)
            elif filename in self.get_modified():
                diff = self.diff_helper(filename=filename,
                                        cached=False)
            else:
                diff = 'SHA1: ' + self.git.hash_object(filename)
        return (diff, filename)

    def get_diff_for_expr(self, idx, expr):
        """
        Return a diff for an arbitrary diff expression.

        `idx` is the index of the entry in the staged files list.

        """
        filename = self.get_filename(idx, staged=True)
        if not filename:
            return (None, None)
        diff = self.diff_helper(filename=filename, ref=expr, cached=False)
        return (diff, filename)

    def stage_modified(self):
        status, output = self.git.add(v=True,
                                      with_stderr=True,
                                      with_status=True,
                                      *self.get_modified())
        self.update_status()
        return (status, output)

    def stage_untracked(self):
        status, output = self.git.add(v=True,
                                      with_stderr=True,
                                      with_status=True,
                                      *self.get_untracked())
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
        tmpfile = self.get_tmp_filename()

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

    def diffindex(self):
        return self.git.diff(unified=self.diff_context,
                             no_color=True,
                             stat=True,
                             cached=True)

    def get_tmp_dir(self):
        # Allow TMPDIR/TMP with a fallback to /tmp
        return os.environ.get('TMP', os.environ.get('TMPDIR', '/tmp'))

    def get_tmp_file_pattern(self):
        return os.path.join(self.get_tmp_dir(), '*.git-cola.%s.*' % os.getpid())

    def get_tmp_filename(self, prefix=''):
        basename = ((prefix+'.git-cola.%s.%s'
                    % (os.getpid(), time.time())))
        basename = basename.replace('/', '-')
        basename = basename.replace('\\', '-')
        tmpdir = self.get_tmp_dir()
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
                    reverse=False,
                    patch_with_raw=True):
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
                                   patch_with_raw=patch_with_raw,
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
        paths = [ self.git.get_git_dir() ]
        paths.extend(subpaths)
        return os.path.realpath(os.path.join(*paths))

    def get_merge_message_path(self):
        for file in ('MERGE_MSG', 'SQUASH_MSG'):
            path = self.git_repo_path(file)
            if os.path.exists(path):
                return path
        return None

    def get_merge_message(self):
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
        merge_msg_path = self.get_merge_message_path()
        while merge_msg_path:
            os.unlink(merge_msg_path)
            merge_msg_path = self.get_merge_message_path()

    def _is_modified(self, name):
        status, out = self.git.diff('--', name,
                                    name_only=True,
                                    exit_code=True,
                                    with_status=True)
        return status != 0


    def _get_branch_status(self, branch):
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
            return ([], [], [], [])
        staged = []
        for name in output.strip('\0').split('\0'):
            if not name:
                continue
            staged.append(core.decode(name))

        return (staged, [], [], [])

    def get_workdir_state(self, head='HEAD', staged_only=False):
        """Returns a tuple of staged, unstaged, untracked, and unmerged files
        """
        self.git.update_index(refresh=True)
        if staged_only:
            return self._get_branch_status(head)

        staged_set = set()
        modified_set = set()

        (staged, modified, unmerged, untracked) = ([], [], [], [])
        try:

            output = self.git.diff_index(head,
                                         M=True,
                                         cached=True,
                                         with_stderr=True)
            if output.startswith('fatal:'):
                raise GitInitError('git init')
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

        except GitInitError:
            # handle git init
            staged.extend(self.all_files())

        try:
            output = self.git.diff_index(head, M=True, with_stderr=True)
            if output.startswith('fatal:'):
                raise GitInitError('git init')
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
                elif status[:1] == 'R':
                    # Rename
                    old, new = name.split('\t')
                    name = eval_path(old)
                    if name not in staged_set:
                        staged.append(name)
                        staged_set.add(name)

        except GitInitError:
            # handle git init
            for name in (self.git.ls_files(modified=True, z=True)
                                 .split('\0')):
                if name:
                    modified.append(core.decode(name))

        for name in self.git.ls_files(others=True, exclude_standard=True,
                                      z=True).split('\0'):
            if name:
                untracked.append(core.decode(name))

        # Keep stuff sorted
        staged.sort()
        modified.sort()
        unmerged.sort()
        untracked.sort()

        return (staged, modified, unmerged, untracked)

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
        state = self.get_workdir_state()
        staged = state[0]
        rmargs = [a for a in args if a in staged]
        if not rmargs:
            return (status, output)
        output += self.git.rm('--', cached=True, with_stderr=True, *rmargs)
        return (status, output)

    def remote_url(self, name):
        return self.git.config('remote.%s.url' % name, get=True)

    def get_remote_args(self, remote,
                        local_branch='',
                        remote_branch='',
                        ffwd=True,
                        tags=False,
                        rebase=False):
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

    def gen_remote_helper(self, gitaction):
        """Generates a closure that calls git fetch, push or pull
        """
        def remote_helper(remote, **kwargs):
            args, kwargs = self.get_remote_args(remote, **kwargs)
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

    def diffstat(self):
        return self.git.diff(
                'HEAD^',
                unified=self.diff_context,
                no_color=True,
                stat=True)

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
        num_results = self.get_num_results()
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

    def get_changed_files(self, start, end):
        zfiles_str = self.git.diff('%s..%s' % (start, end),
                                   name_only=True, z=True).strip('\0')
        return [core.decode(enc) for enc in zfiles_str.split('\0') if enc]

    def get_renamed_files(self, start, end):
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
