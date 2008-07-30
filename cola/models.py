import os
import sys
import re
import time
import subprocess
from cStringIO import StringIO

from cola import git
from cola import utils
from cola import model

#+-------------------------------------------------------------------------
#+ A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile('([0-9a-f]+)\W(.*)')

#+-------------------------------------------------------------------------
# List of functions available directly through model.command_name()
GIT_COMMANDS = """
    am annotate apply archive archive_recursive
    bisect blame branch bundle
    checkout checkout_index cherry cherry_pick citool
    clean commit config count_objects
    describe diff
    fast_export fetch filter_branch format_patch fsck
    gc get_tar_commit_id grep gui
    hard_repack imap_send init instaweb
    log lost_found ls_files ls_remote ls_tree
    merge mergetool mv name_rev pull push
    read_tree rebase relink remote repack
    request_pull reset revert rev_list rm
    send_email shortlog show show_branch
    show_ref stash status submodule svn
    tag var verify_pack whatchanged
""".split()

class GitCola(git.Git):
    """GitPython throws exceptions by default.
    We suppress exceptions in favor of return values.
    """
    def __init__(self):
        self._git_dir = None
        self._work_tree = None
        self._has_worktree = True
        git_dir = self.get_git_dir()
        work_tree = self.get_work_tree()
        if work_tree:
            os.chdir(work_tree)
        git.Git.__init__(self, work_tree)
    def execute(*args, **kwargs):
        kwargs['with_exceptions'] = False
        return git.Git.execute(*args, **kwargs)
    def get_work_tree(self):
        if self._work_tree or not self._has_worktree:
            return self._work_tree
        if not self._git_dir:
            self._git_dir = self.get_git_dir()
        # Handle bare repositories
        if (len(os.path.basename(self._git_dir)) > 4
                and self._git_dir.endswith('.git')):
            self._has_worktree = False
            return self._work_tree
        self._work_tree = os.getenv('GIT_WORK_TREE')
        if not self._work_tree or not os.path.isdir(self._work_tree):
            self._work_tree = os.path.abspath(
                    os.path.join(os.path.abspath(self._git_dir), '..'))
        return self._work_tree
    def get_git_dir(self):
        if self._git_dir:
            return self._git_dir
        self._git_dir = os.getenv('GIT_DIR')
        if self._git_dir and self._is_git_dir(self._git_dir):
            return self._git_dir
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
        if not self._git_dir:
            sys.stderr.write("oops, %s is not a git project.\n"
                            % os.getcwd() )
            sys.exit(-1)
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

class Model(model.Model):
    """Provides a friendly wrapper for doing commit git operations."""

    def init(self):
        """Reads git repository settings and sets several methods
        so that they refer to the git module.  This object
        encapsulates cola's interaction with git."""

        # chdir to the root of the git tree.
        # This keeps paths relative.
        self.git = GitCola()

        # Read git config
        self.__init_config_data()

        # Import all git commands from git.py
        for cmd in GIT_COMMANDS:
            setattr(self, cmd, getattr(self.git, cmd))

        self.create(
            #####################################################
            # Used in various places
            currentbranch = '',
            remotes = [],
            remotename = '',
            local_branch = '',
            remote_branch = '',
            search_text = '',
            git_version = self.git.version(),

            #####################################################
            # Used primarily by the main UI
            project = os.path.basename(os.getcwd()),
            commitmsg = '',
            modified = [],
            staged = [],
            unstaged = [],
            untracked = [],
            unmerged = [],
            window_geom = utils.parse_geom(self.get_global_cola_geometry()),

            #####################################################
            # Used by the create branch dialog
            revision = '',
            local_branches = [],
            remote_branches = [],
            tags = [],

            #####################################################
            # Used by the commit/repo browser
            directory = '',
            revisions = [],
            summaries = [],

            # These are parallel lists
            types = [],
            sha1s = [],
            names = [],

            # All items below here are re-calculated in
            # init_browser_data()
            directories = [],
            directory_entries = {},

            # These are also parallel lists
            subtree_types = [],
            subtree_sha1s = [],
            subtree_names = [],
            )

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
            'cola_geometry':'',
            'cola_fontui': '',
            'cola_fontuisize': 12,
            'cola_fontdiff': '',
            'cola_fontdiffsize': 12,
            'cola_savewindowsettings': False,
            'cola_editdiffreverse': False,
            'cola_saveatexit': False,
            'gui_editor': 'gvim',
            'gui_diffeditor': 'xxdiff',
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
                    self.set_param(param+'size', size)
                    param = param[len('global_'):]
                    global_dict[param] = font
                    global_dict[param+'size'] = size

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

        # Allow EDITOR/DIFF_EDITOR environment variable overrides
        self.global_gui_editor = os.getenv('COLA_EDITOR',
                                           self.global_gui_editor)
        self.global_gui_diffeditor = os.getenv('COLA_DIFFEDITOR',
                                               self.global_gui_diffeditor)
        # Load the diff context
        self.diff_context = self.local_gui_diffcontext

    def get_cola_config(self, key):
        return getattr(self, 'global_cola_'+key)

    def get_gui_config(self, key):
        return getattr(self, 'global_gui_'+key)

    def branch_list(self, remote=False):
        branches = map(lambda x: x.lstrip('* '),
                self.git.branch(r=remote).splitlines())
        if remote:
            remotes = []
            for branch in branches:
                if branch.endswith('/HEAD'):
                    continue
                remotes.append(branch)
            return remotes
        return branches

    def get_config_params(self):
        params = []
        params.extend(map(lambda x: 'local_' + x,
                          self.__local_and_global_defaults.keys()))
        params.extend(map(lambda x: 'global_' + x,
                          self.__local_and_global_defaults.keys()))
        params.extend(map(lambda x: 'global_' + x,
                          self.__global_defaults.keys()))
        return [ p for p in params if not p.endswith('size') ]

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
        if not self.get_currentbranch(): return

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

    def add_or_remove(self, *to_process):
        """Invokes 'git add' to index the filenames in to_process that exist
        and 'git rm' for those that do not exist."""

        if not to_process:
            return 'No files to add or remove.'

        to_add = []
        to_remove = []

        for filename in to_process:
            if os.path.exists(filename):
                to_add.append(filename)

        output = self.git.add(v=True, *to_add)

        if len(to_add) == len(to_process):
            # to_process only contained unremoved files --
            # short-circuit the removal checks
            return output

        # Process files to remote
        for filename in to_process:
            if not os.path.exists(filename):
                to_remove.append(filename)
        output + '\n\n' + self.git.rm(*to_remove)

    def get_editor(self):
        return self.get_gui_config('editor')

    def get_diffeditor(self):
        return self.get_gui_config('diffeditor')

    def get_history_browser(self):
        return self.get_gui_config('historybrowser')

    def remember_gui_settings(self):
        return self.get_cola_config('savewindowsettings')

    def save_at_exit(self):
        return self.get_cola_config('saveatexit')

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
        if not remote: return
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
        file = open(path, 'r')
        contents = file.read()
        file.close()
        self.set_commitmsg(contents)

    def get_prev_commitmsg(self,*rest):
        """Queries git for the latest commit message and sets it in
        self.commitmsg."""
        commit_msg = []
        commit_lines = self.git.show('HEAD').split('\n')
        for idx, msg in enumerate(commit_lines):
            if idx < 4: continue
            msg = msg.lstrip()
            if msg.startswith('diff --git'):
                commit_msg.pop()
                break
            commit_msg.append(msg)
        self.set_commitmsg('\n'.join(commit_msg).rstrip())

    def update_status(self):
        # This allows us to defer notification until the
        # we finish processing data
        notify_enabled = self.get_notify()
        self.set_notify(False)

        # Reset the staged and unstaged model lists
        # NOTE: the model's unstaged list is used to
        # hold both modified and untracked files.
        self.staged = []
        self.modified = []
        self.untracked = []

        # Read git status items
        (staged_items,
         modified_items,
         untracked_items,
         unmerged_items) = self.parse_status()

        # Gather items to be committed
        for staged in staged_items:
            if staged not in self.get_staged():
                self.add_staged(staged)

        # Gather unindexed items
        for modified in modified_items:
            if modified not in self.get_modified():
                self.add_modified(modified)

        # Gather untracked items
        for untracked in untracked_items:
            if untracked not in self.get_untracked():
                self.add_untracked(untracked)

        # Gather unmerged items
        for unmerged in unmerged_items:
            if unmerged not in self.get_unmerged():
                self.add_unmerged(unmerged)

        self.set_currentbranch(self.current_branch())
        self.set_unstaged(self.get_modified() + self.get_untracked() + self.get_unmerged())
        self.set_remotes(self.git.remote().splitlines())
        self.set_remote_branches(self.branch_list(remote=True))
        self.set_local_branches(self.branch_list(remote=False))
        self.set_tags(self.git.tag().splitlines())
        self.set_revision('')
        self.set_local_branch('')
        self.set_remote_branch('')
        # Re-enable notifications and emit changes
        self.set_notify(notify_enabled)
        self.notify_observers('staged','unstaged')

    def delete_branch(self, branch):
        return self.git.branch(branch, D=True)

    def get_revision_sha1(self, idx):
        return self.get_revisions()[idx]

    def apply_font_size(self, param, default):
        old_font = self.get_param(param)
        if not old_font:
            old_font = default
        size = self.get_param(param+'size')
        props = old_font.split(',')
        props[1] = str(size)
        new_font = ','.join(props)

        self.set_param(param, new_font)

    def get_commit_diff(self, sha1):
        commit = self.git.show(sha1)
        first_newline = commit.index('\n')
        if commit[first_newline+1:].startswith('Merge:'):
            return (commit + '\n\n'
                    + self.diff_helper(commit=sha1,
                                       cached=False,
                                       suppress_header=False))
        else:
            return commit

    def get_diff_details(self, idx, staged=True):
        if staged:
            filename = self.get_staged()[idx]
            if os.path.exists(filename):
                status = 'Staged for commit'
            else:
                status = 'Staged for removal'
            diff = self.diff_helper(filename=filename,
                                    cached=True)
        else:
            filename = self.get_unstaged()[idx]
            if os.path.isdir(filename):
                status = 'Untracked directory'
                diff = '\n'.join(os.listdir(filename))
            elif filename in self.get_modified():
                status = 'Modified, not staged'
                diff = self.diff_helper(filename=filename,
                                        cached=False)
            else:
                status = 'Untracked, not staged'

                file_type = utils.run_cmd('file', '-b', filename)
                if 'binary' in file_type or 'data' in file_type:
                    diff = utils.run_cmd('hexdump', '-C', filename)
                else:
                    if os.path.exists(filename):
                        file = open(filename, 'r')
                        diff = file.read()
                        file.close()
                    else:
                        diff = ''
        return diff, status, filename

    def stage_modified(self):
        output = self.git.add(self.get_modified())
        self.update_status()
        return output

    def stage_untracked(self):
        output = self.git.add(self.get_untracked())
        self.update_status()
        return output

    def reset(self, *items):
        output = self.git.reset('--', *items)
        self.update_status()
        return output

    def unstage_all(self):
        self.git.reset('--', *self.get_staged())
        self.update_status()

    def save_gui_settings(self):
        self.config_set('cola.geometry', utils.get_geom(), local=False)

    def config_set(self, key=None, value=None, local=True):
        if key and value is not None:
            # git config category.key value
            strval = str(value)
            if type(value) is bool:
                # git uses "true" and "false"
                strval = strval.lower()
            if local:
                argv = [ key, strval ]
            else:
                argv = [ '--global', key, strval ]
            return self.git.config(*argv)
        else:
            msg = "oops in config_set(key=%s,value=%s,local=%s"
            raise Exception(msg % (key, value, local))

    def config_dict(self, local=True):
        """parses the lines from git config --list into a dictionary"""

        kwargs = {
            'list': True,
            'global': not local,
        }
        config_lines = self.git.config(**kwargs).splitlines()
        newdict = {}
        for line in config_lines:
            k, v = line.split('=', 1)
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
        file = open(tmpfile, 'w')
        file.write(msg)
        file.close()

        # Run 'git commit'
        output = self.git.commit(F=tmpfile, amend=amend)
        os.unlink(tmpfile)

        return ('git commit -F %s --amend %s\n\n%s'
                % ( tmpfile, amend, output ))


    def diffindex(self):
        return self.git.diff(unified=self.diff_context,
                             stat=True,
                             cached=True)

    def get_tmp_dir(self):
        return os.environ.get('TMP', os.environ.get('TMPDIR', '/tmp'))

    def get_tmp_file_pattern(self):
        return os.path.join(self.get_tmp_dir(), '*.git.%s.*' % os.getpid())

    def get_tmp_filename(self, prefix=''):
        # Allow TMPDIR/TMP with a fallback to /tmp
        basename = (prefix+'.git.%s.%s'
                    % (os.getpid(), time.time())).replace(os.sep, '-')
        return os.path.join(self.get_tmp_dir(), basename)

    def log_helper(self, all=False):
        """
        Returns a pair of parallel arrays listing the revision sha1's
        and commit summaries.
        """
        revs = []
        summaries = []
        regex = REV_LIST_REGEX
        output = self.git.log(pretty='oneline', all=all)
        for line in output.splitlines():
            match = regex.match(line)
            if match:
                revs.append(match.group(1))
                summaries.append(match.group(2))
        return (revs, summaries)

    def parse_rev_list(self, raw_revs):
        revs = []
        for line in raw_revs.splitlines():
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
                    filename=None,
                    color=False,
                    cached=True,
                    with_diff_header=False,
                    suppress_header=True,
                    reverse=False):
        "Invokes git diff on a filepath."

        argv = []
        if commit:
            argv.append('%s^..%s' % (commit, commit))
        elif branch:
            argv.append(branch)

        if filename:
            argv.append('--')
            if type(filename) is list:
                argv.extend(filename)
            else:
                argv.append(filename)

        diffoutput = self.git.diff(R=reverse,
                                   color=color,
                                   cached=cached,
                                   patch_with_raw=True,
                                   unified=self.diff_context,
                                   with_raw_output=True,
                                   *argv)
        diff = diffoutput.splitlines()

        output = StringIO()
        start = False
        del_tag = 'deleted file mode '

        headers = []
        deleted = cached and not os.path.exists(filename)
        for line in diff:
            if not start and '@@ ' in line and ' @@' in line:
                start = True
            if start or(deleted and del_tag in line):
                output.write(line + '\n')
            else:
                if with_diff_header:
                    headers.append(line)
                elif not suppress_header:
                    output.write(line + '\n')
        result = output.getvalue()
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

    def parse_status(self):
        """RETURNS: A tuple of staged, unstaged and untracked file lists.
        """
        def eval_path(path):
            """handles quoted paths."""
            if path.startswith('"') and path.endswith('"'):
                return eval(path)
            else:
                return path

        MODIFIED_TAG = '# Changed but not updated:'
        UNTRACKED_TAG = '# Untracked files:'
        RGX_RENAMED = re.compile('(#\trenamed:\s+|#\tcopied:\s+)'
                                 '(.*?)\s->\s(.*)')
        RGX_MODIFIED = re.compile('(#\tmodified:\s+'
                                  '|#\tnew file:\s+'
                                  '|#\tdeleted:\s+)')
        RGX_UNMERGED = re.compile('(#\tunmerged:\s+)')

        staged = []
        unstaged = []
        untracked = []
        unmerged = []

        STAGED_MODE = 0
        UNSTAGED_MODE = 1
        UNTRACKED_MODE = 2

        current_dest = staged
        mode = STAGED_MODE

        for status_line in self.git.status().splitlines():
            if status_line == MODIFIED_TAG:
                mode = UNSTAGED_MODE
                current_dest = unstaged
                continue
            elif status_line == UNTRACKED_TAG:
                mode = UNTRACKED_MODE
                current_dest = untracked
                continue
            # Staged/unstaged modified/renamed/deleted files
            if mode is STAGED_MODE or mode is UNSTAGED_MODE:
                match = RGX_MODIFIED.match(status_line)
                if match:
                    tag = match.group(0)
                    filename = status_line.replace(tag, '')
                    current_dest.append(eval_path(filename))
                    continue
                match = RGX_RENAMED.match(status_line)
                if match:
                    oldname = match.group(2)
                    newname = match.group(3)
                    current_dest.append(eval_path(oldname))
                    current_dest.append(eval_path(newname))
                    continue
                match = RGX_UNMERGED.match(status_line)
                if match:
                    tag = match.group(0)
                    filename = status_line.replace(tag, '')
                    unmerged.append(eval_path(filename))
                    unstaged.append(eval_path(filename))
                    continue
            # Untracked files
            elif mode is UNTRACKED_MODE:
                if status_line.startswith('#\t'):
                    current_dest.append(eval_path(status_line[2:]))

        return(staged, unstaged, untracked, unmerged)

    def reset_helper(self, *args, **kwargs):
        return self.git.reset('--', *args, **kwargs)

    def remote_url(self, name):
        return self.git.config('remote.%s.url' % name, get=True)

    def get_remote_args(self, remote,
            local_branch='', remote_branch='',
            ffwd=True, tags=False):
        if ffwd:
            branch_arg = '%s:%s' % ( remote_branch, local_branch )
        else:
            branch_arg = '+%s:%s' % ( remote_branch, local_branch )
        args = [remote]
        if local_branch and remote_branch:
            args.append(branch_arg)
        kwargs = {
            "with_extended_output": True,
            "tags": tags
        }
        return (args, kwargs)

    def fetch_helper(self, *args, **kwargs):
        """
        Fetches remote_branch to local_branch only if
        remote_branch and local_branch are both supplied.
        If either is ommitted, "git fetch <remote>" is performed instead.
        Returns (status,output)
        """
        args, kwargs = self.get_remote_args(*args, **kwargs)
        (status, stdout, stderr) = self.git.fetch(v=True, *args, **kwargs)
        return (status, stdout + stderr)

    def push_helper(self, *args, **kwargs):
        """
        Pushes local_branch to remote's remote_branch only if
        remote_branch and local_branch both are supplied.
        If either is ommitted, "git push <remote>" is performed instead.
        Returns (status,output)
        """
        args, kwargs = self.get_remote_args(*args, **kwargs)
        (status, stdout, stderr) = self.git.push(*args, **kwargs)
        return (status, stdout + stderr)

    def pull_helper(self, *args, **kwargs):
        """
        Pushes branches.  If local_branch or remote_branch is ommitted,
        "git pull <remote>" is performed instead of
        "git pull <remote> <remote_branch>:<local_branch>
        Returns (status,output)
        """
        args, kwargs = self.get_remote_args(*args, **kwargs)
        (status, stdout, stderr) = self.git.pull(v=True, *args, **kwargs)
        return (status, stdout + stderr)

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
        for patchset in patches_to_export:
            cmdoutput = self.export_patchset(patchset[0],
                                             patchset[-1],
                                             output="patches",
                                             n=len(patchset) > 1,
                                             thread=True,
                                             patch_with_stat=True)
            outlines.append(cmdoutput)
        return '\n'.join(outlines)

    def export_patchset(self, start, end, output="patches", **kwargs):
        revarg = '%s^..%s' % (start, end)
        return self.git.format_patch("-o", output, revarg, **kwargs)

    def current_branch(self):
        """Parses 'git branch' to find the current branch."""
        branches = self.git.branch().splitlines()
        for branch in branches:
            if branch.startswith('* '):
                return branch.lstrip('* ')
        return 'Detached HEAD'

    def create_branch(self, name, base, track=False):
        """Creates a branch starting from base.  Pass track=True
        to create a remote tracking branch."""
        return self.git.branch(name, base, track=track)

    def cherry_pick_list(self, revs, **kwargs):
        """Cherry-picks each revision into the current branch.
        Returns a list of command output strings (1 per cherry pick)"""
        if not revs:
            return []
        cherries = []
        for rev in revs:
            cherries.append(self.git.cherry_pick(rev, **kwargs))
        return '\n'.join(cherries)

    def parse_stash_list(self, revids=False):
        """Parses "git stash list" and returns a list of stashes."""
        stashes = self.stash("list").splitlines()
        if revids:
            return [ s[:s.index(':')] for s in stashes ]
        else:
            return [ s[s.index(':')+1:] for s in stashes ]
