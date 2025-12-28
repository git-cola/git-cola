"""The central cola model"""
import os

from qtpy import QtCore
from qtpy.QtCore import Signal

from .. import core
from .. import git
from .. import gitcmds
from .. import gitcfg
from .. import version
from ..git import STDOUT, transform_kwargs
from ..interaction import Interaction
from ..i18n import N_
from . import prefs


FETCH = 'fetch'
FETCH_HEAD = 'FETCH_HEAD'
PUSH = 'push'
PULL = 'pull'


def create(context):
    """Create the repository status model"""
    return MainModel(context)


class MainModel(QtCore.QObject):
    """Repository status model"""

    # Refactor: split this class apart into separate DiffModel, CommitMessageModel,
    # StatusModel, and a DiffEditorState.

    # Signals
    about_to_update = Signal()
    previous_contents = Signal(list, list, list, list)
    commit_message_changed = Signal(object)
    diff_text_changed = Signal()
    diff_text_updated = Signal(str)
    # "diff_type" {text,image} represents the diff viewer mode.
    diff_type_changed = Signal(object)
    # "file_type" {text,image} represents the selected file type.
    file_type_changed = Signal(object)
    images_changed = Signal(object)
    mode_changed = Signal(str)
    submodules_changed = Signal()
    refs_updated = Signal()
    updated = Signal()
    worktree_changed = Signal()

    # States
    mode_none = 'none'  # Default: nothing's happened, do nothing
    mode_worktree = 'worktree'  # Comparing index to worktree
    mode_diffstat = 'diffstat'  # Showing a diffstat
    mode_display = 'display'  # Displaying arbitrary information
    mode_untracked = 'untracked'  # Dealing with an untracked file
    mode_untracked_diff = 'untracked-diff'  # Diffing an untracked file
    mode_index = 'index'  # Comparing index to last commit
    mode_amend = 'amend'  # Amending a commit
    mode_diff = 'diff'  # Diffing against an arbitrary commit

    # Modes where we can checkout files from the $head
    modes_undoable = {mode_amend, mode_diff, mode_index, mode_worktree}

    # Modes where we can partially stage files
    modes_partially_stageable = {
        mode_amend,
        mode_diff,
        mode_worktree,
        mode_untracked_diff,
    }

    # Modes where we can partially unstage files
    modes_unstageable = {mode_amend, mode_diff, mode_index}

    unstaged = property(lambda self: self.modified + self.unmerged + self.untracked)
    """An aggregate of the modified, unmerged, and untracked file lists."""

    def __init__(self, context, cwd=None):
        """Interface to the main repository status"""
        super().__init__()

        self.context = context
        self.git = context.git
        self.cfg = context.cfg
        self.selection = context.selection

        self.initialized = False
        self.annex = False
        self.lfs = False
        self.head = 'HEAD'
        self.diff_text = ''
        self.diff_type = Types.TEXT
        self.file_type = Types.TEXT
        self.mode = self.mode_none
        self.filename = None
        self.is_cherry_picking = False
        self.is_merging = False
        self.is_rebasing = False
        self.is_applying_patch = False
        self.commit_author = None
        self.currentbranch = ''
        self.directory = ''
        self.project = ''
        self.remotes = []
        self.filter_paths = None
        self.images = []

        self.commitmsg = ''  # current commit message
        self._auto_commitmsg = ''  # e.g. .git/MERGE_MSG
        self._prev_commitmsg = ''  # saved here when clobbered by .git/MERGE_MSG
        self.object_format = 'sha1'  # repository object format variables.
        self.oid_len = git.OID_LENGTH_SHA1
        self.empty_tree_oid = git.EMPTY_TREE_SHA1
        self.missing_blob_oid = git.MISSING_BLOB_SHA1

        self.modified = []  # modified, staged, untracked, unmerged paths
        self.staged = []
        self.untracked = []
        self.unmerged = []
        self.upstream_changed = []  # paths that've changed upstream
        self.staged_deleted = set()
        self.unstaged_deleted = set()
        self.submodules = set()
        self.submodules_list = None  # lazy loaded

        self.error = None  # The last error message.
        self.ref_sort = 0  # (0: version, 1:reverse-chrono)
        self.local_branches = []
        self.remote_branches = []
        self.tags = []
        if cwd:
            self.set_worktree(cwd)

    def is_diff_mode(self):
        """Are we in diff mode?"""
        return self.mode == self.mode_diff

    def is_unstageable(self):
        """Are we in a mode that supports "unstage" actions?"""
        return self.mode in self.modes_unstageable

    def is_amend_mode(self):
        """Are we amending a commit?"""
        return self.mode == self.mode_amend

    def is_undoable(self):
        """Can we checkout from the current branch or head ref?"""
        return self.mode in self.modes_undoable

    def is_partially_stageable(self):
        """Whether partial staging should be allowed."""
        return self.mode in self.modes_partially_stageable

    def is_stageable(self):
        """Whether staging should be allowed."""
        return self.is_partially_stageable() or self.mode == self.mode_untracked

    def all_branches(self):
        return self.local_branches + self.remote_branches

    def set_worktree(self, worktree):
        last_worktree = self.git.paths.worktree
        self.git.set_worktree(worktree)

        is_valid = self.git.is_valid()
        if is_valid:
            reset = last_worktree is None or last_worktree != worktree
            cwd = self.git.getcwd()
            self.project = os.path.basename(cwd)
            self.set_directory(cwd)
            core.chdir(cwd)
            self.update_config(reset=reset)

            # Detect the "git init" scenario by checking for branches.
            # If no branches exist then we cannot use "git rev-parse" yet.
            err = None
            refs = self.git.git_path('refs', 'heads')
            if core.exists(refs) and core.listdir(refs):
                # "git rev-parse" exits with a non-zero exit status when the
                # safe.directory protection is active.
                status, _, err = self.git.rev_parse('HEAD')
                is_valid = status == 0
            if is_valid:
                self.error = None
                self.worktree_changed.emit()
            else:
                self.error = err

        return is_valid

    def is_git_lfs_enabled(self):
        """Return True if `git lfs install` has been run

        We check for the existence of the "lfs" object-storea, and one of the
        "git lfs install"-provided hooks.  This allows us to detect when
        "git lfs uninstall" has been run.

        """
        lfs_filter = self.cfg.get('filter.lfs.clean', default=False)
        lfs_dir = lfs_filter and self.git.git_path('lfs')
        lfs_hook = lfs_filter and self.cfg.hooks_path('post-merge')
        return (
            lfs_filter
            and lfs_dir
            and core.exists(lfs_dir)
            and lfs_hook
            and core.exists(lfs_hook)
        )

    def set_commitmsg(self, msg, notify=True):
        self.commitmsg = msg
        self._auto_commitmsg = ''
        if notify:
            self.commit_message_changed.emit(msg)

    def set_commit_author(self, author):
        """Set the author that will be used when creating commits"""
        self.commit_author = author

    def save_commitmsg(self, msg=None):
        if msg is None:
            msg = self.commitmsg
        path = self.git.git_path('GIT_COLA_MSG')
        try:
            if not msg.endswith('\n'):
                msg += '\n'
            core.write(path, msg)
        except OSError:
            pass
        return path

    def set_diff_text(self, txt):
        """Update the text displayed in the diff editor"""
        changed = txt != self.diff_text
        self.diff_text = txt
        self.diff_text_updated.emit(txt)
        if changed:
            self.diff_text_changed.emit()

    def set_diff_type(self, diff_type):  # text, image
        """Set the diff type to either text or image"""
        changed = diff_type != self.diff_type
        self.diff_type = diff_type
        if changed:
            self.diff_type_changed.emit(diff_type)

    def set_file_type(self, file_type):  # text, image
        """Set the file type to either text or image"""
        changed = file_type != self.file_type
        self.file_type = file_type
        if changed:
            self.file_type_changed.emit(file_type)

    def set_images(self, images):
        """Update the images shown in the preview pane"""
        self.images = images
        self.images_changed.emit(images)

    def set_directory(self, path):
        self.directory = path

    def set_mode(self, mode, head=None):
        """Set the current editing mode (worktree, index, amending, ...)"""
        # Do not allow going into index or worktree mode when amending.
        if self.is_amend_mode() and mode != self.mode_none:
            return
        # We cannot amend in the middle of git cherry-pick, git am or git merge.
        if (
            self.is_cherry_picking or self.is_merging or self.is_applying_patch
        ) and mode == self.mode_amend:
            mode = self.mode

        # Stay in diff mode until explicitly reset.
        if self.mode == self.mode_diff and mode != self.mode_none:
            mode = self.mode_diff
            head = head or self.head
        else:
            # If we are amending then we'll use "HEAD^", otherwise use the specified
            # head or "HEAD" if head has not been specified.
            if mode == self.mode_amend:
                head = 'HEAD^'
            elif not head:
                head = 'HEAD'

        self.head = head
        self.mode = mode
        self.mode_changed.emit(mode)

    def update_path_filter(self, filter_paths):
        self.filter_paths = filter_paths
        self.update_file_status()

    def emit_about_to_update(self):
        self.previous_contents.emit(
            self.staged, self.unmerged, self.modified, self.untracked
        )
        self.about_to_update.emit()

    def emit_updated(self):
        self.updated.emit()

    def update_file_status(self, update_index=False):
        """Update modified/staged files status"""
        self.emit_about_to_update()
        self.update_files(update_index=update_index, emit=True)

    def update_file_merge_status(self):
        """Update modified/staged files and Merge/Rebase/Cherry-pick status"""
        self.emit_about_to_update()
        self._update_merge_rebase_status()
        self.update_file_status()

    def update_status(self, update_index=False, reset=False):
        # Give observers a chance to respond
        self.emit_about_to_update()
        self.initialized = True
        self._update_merge_rebase_status()
        self._update_files(update_index=update_index)
        self._update_remotes()
        self._update_branches_and_tags()
        self._update_commitmsg()
        self.update_config()
        if reset:
            self.update_submodules_list()
        self.emit_updated()

    def update_config(self, emit=False, reset=False):
        if reset:
            self.cfg.reset()
        self.annex = self.cfg.is_annex()
        self.lfs = self.is_git_lfs_enabled()
        # Update sha256 / sha1 repository state.
        self.object_format = self.cfg.get_object_format()
        if self.object_format == 'sha256':
            self.oid_len = git.OID_LENGTH_SHA256
            self.empty_tree_oid = git.EMPTY_TREE_SHA256
            self.missing_blob_oid = git.MISSING_BLOB_SHA256
        else:
            self.oid_len = git.OID_LENGTH_SHA1
            self.empty_tree_oid = git.EMPTY_TREE_SHA1
            self.missing_blob_oid = git.MISSING_BLOB_SHA1
        if emit:
            self.emit_updated()

    def update_files(self, update_index=False, emit=False):
        self._update_files(update_index=update_index)
        if emit:
            self.emit_updated()

    def _update_files(self, update_index=False):
        context = self.context
        display_untracked = prefs.display_untracked(context)
        state = gitcmds.worktree_state(
            context,
            head=self.head,
            update_index=update_index,
            display_untracked=display_untracked,
            paths=self.filter_paths,
        )
        self.staged = state.get('staged', [])
        self.modified = state.get('modified', [])
        self.unmerged = state.get('unmerged', [])
        self.untracked = state.get('untracked', [])
        self.upstream_changed = state.get('upstream_changed', [])
        self.staged_deleted = state.get('staged_deleted', set())
        self.unstaged_deleted = state.get('unstaged_deleted', set())
        self.submodules = state.get('submodules', set())

        selection = self.selection
        if self.is_empty():
            selection.reset()
        else:
            selection.update(self)
        if selection.is_empty():
            self.set_diff_text('')

    def is_empty(self):
        return not (
            bool(self.staged or self.modified or self.unmerged or self.untracked)
        )

    def is_empty_repository(self):
        return not self.local_branches

    def _update_remotes(self):
        self.remotes = sorted(gitcfg.get_remotes(self.cfg))

    def _update_branches_and_tags(self):
        context = self.context
        sort_types = (
            'version:refname',
            '-committerdate',
        )
        sort_key = sort_types[self.ref_sort]
        local_branches, remote_branches, tags = gitcmds.all_refs(
            context, split=True, sort_key=sort_key
        )
        self.local_branches = local_branches
        self.remote_branches = remote_branches
        self.tags = tags
        # Set these early since they are used to calculate 'upstream_changed'.
        self.currentbranch = gitcmds.current_branch(self.context)
        self.refs_updated.emit()

    def _update_merge_rebase_status(self):
        cherry_pick_head = self.git.git_path('CHERRY_PICK_HEAD')
        merge_head = self.git.git_path('MERGE_HEAD')
        rebase_merge = self.git.git_path('rebase-merge')
        rebase_apply = self.git.git_path('rebase-apply', 'applying')
        self.is_cherry_picking = cherry_pick_head and core.exists(cherry_pick_head)
        self.is_merging = merge_head and core.exists(merge_head)
        self.is_rebasing = rebase_merge and core.exists(rebase_merge)
        self.is_applying_patch = rebase_apply and core.exists(rebase_apply)
        if self.mode == self.mode_amend and (
            self.is_merging or self.is_cherry_picking or self.is_applying_patch
        ):
            self.set_mode(self.mode_none)

    def _update_commitmsg(self):
        """Check for merge message files and update the commit message

        The message is cleared when the merge completes.
        """
        if self.is_amend_mode():
            return
        # Check if there's a message file in .git/
        context = self.context
        merge_msg_path = gitcmds.merge_message_path(context)
        if merge_msg_path:
            msg = gitcmds.read_merge_commit_message(context, merge_msg_path)
            if msg != self._auto_commitmsg:
                self._auto_commitmsg = msg
                self._prev_commitmsg = self.commitmsg
                self.set_commitmsg(msg)

        elif self._auto_commitmsg and self._auto_commitmsg == self.commitmsg:
            self._auto_commitmsg = ''
            self.set_commitmsg(self._prev_commitmsg)

    def update_submodules_list(self):
        self.submodules_list = gitcmds.list_submodule(self.context)
        self.submodules_changed.emit()

    def update_remotes(self):
        self._update_remotes()
        self.update_refs()

    def update_refs(self):
        """Update tag and branch names"""
        self.emit_about_to_update()
        self._update_branches_and_tags()
        self.emit_updated()

    def delete_branch(self, branch):
        status, out, err = self.git.branch(branch, D=True)
        self.update_refs()
        return status, out, err

    def rename_branch(self, branch, new_branch):
        status, out, err = self.git.branch(branch, new_branch, M=True)
        self.update_refs()
        return status, out, err

    def remote_url(self, name, action):
        push = action == 'PUSH'
        return gitcmds.remote_url(self.context, name, push=push)

    def fetch(self, remote, **opts):
        result = run_remote_action(self.context, self.git.fetch, remote, FETCH, **opts)
        self.update_refs()
        return result

    def push(self, remote, **opts):
        result = run_remote_action(self.context, self.git.push, remote, PUSH, **opts)
        self.update_refs()
        return result

    def pull(self, remote, **opts):
        result = run_remote_action(self.context, self.git.pull, remote, PULL, **opts)
        # Pull can result in merge conflicts
        self.update_refs()
        self.update_files(update_index=False, emit=True)
        return result

    def create_branch(self, name, base, track=False, force=False):
        """Create a branch named 'name' from revision 'base'

        Pass track=True to create a local tracking branch.
        """
        return self.git.branch(name, base, track=track, force=force)

    def is_commit_published(self):
        """Return True if the latest commit exists in any remote branch"""
        return bool(self.git.branch(r=True, contains='HEAD')[STDOUT])

    def untrack_paths(self, paths):
        context = self.context
        status, out, err = gitcmds.untrack_paths(context, paths)
        self.update_file_status()
        return status, out, err

    def getcwd(self):
        """If we've chosen a directory then use it, otherwise use current"""
        if self.directory:
            return self.directory
        return core.getcwd()

    def cycle_ref_sort(self):
        """Choose the next ref sort type (version, reverse-chronological)"""
        self.set_ref_sort(self.ref_sort + 1)

    def set_ref_sort(self, raw_value):
        value = raw_value % 2  # Currently two sort types
        if value == self.ref_sort:
            return
        self.ref_sort = value
        self.update_refs()


class Types:
    """File types (used for image diff modes)"""

    IMAGE = 'image'
    TEXT = 'text'


def remote_args(
    context,
    remote,
    action,
    local_branch='',
    remote_branch='',
    ff_only=False,
    force=False,
    no_ff=False,
    tags=False,
    rebase=False,
    set_upstream=False,
    prune=False,
):
    """Return arguments for git fetch/push/pull"""

    args = [remote]
    what = refspec_arg(local_branch, remote_branch, remote, action)
    if what:
        args.append(what)

    kwargs = {
        'verbose': True,
    }
    if action == PULL:
        if rebase:
            kwargs['rebase'] = True
        elif ff_only:
            kwargs['ff_only'] = True
        elif no_ff:
            kwargs['no_ff'] = True
    elif force:
        if action == PUSH and version.check_git(context, 'force-with-lease'):
            kwargs['force_with_lease'] = True
        else:
            kwargs['force'] = True

    if action == PUSH and set_upstream:
        kwargs['set_upstream'] = True
    if tags:
        kwargs['tags'] = True
    if prune:
        kwargs['prune'] = True

    return (args, kwargs)


def refspec(src, dst, action):
    if action == PUSH and src == dst:
        spec = src
    else:
        spec = f'{src}:{dst}'
    return spec


def refspec_arg(local_branch, remote_branch, remote, action):
    """Return the refspec for a fetch or pull command"""
    ref = None
    if action == PUSH and local_branch and remote_branch:  # Push with local and remote.
        ref = refspec(local_branch, remote_branch, action)
    elif action == FETCH:
        if local_branch and remote_branch:  # Fetch with local and remote.
            if local_branch == FETCH_HEAD:
                ref = remote_branch
            else:
                ref = refspec(remote_branch, local_branch, action)
        elif remote_branch:
            # If we are fetching and only a remote branch was specified then setup
            # a refspec that will fetch into the remote tracking branch only.
            ref = refspec(
                remote_branch,
                f'refs/remotes/{remote}/{remote_branch}',
                action,
            )
    if not ref and local_branch != FETCH_HEAD:
        ref = local_branch or remote_branch or None
    return ref


def run_remote_action(context, fn, remote, action, **kwargs):
    """Run fetch, push or pull"""
    kwargs.pop('_add_env', None)
    args, kwargs = remote_args(context, remote, action, **kwargs)

    if prefs.verbose_simple_commands(context):
        cmd_args = ['git']
        if action == FETCH:
            cmd_args.append('fetch')
        elif action == PUSH:
            cmd_args.append('push')
        elif action == PULL:
            cmd_args.append('pull')
        cmd_args.extend(transform_kwargs(**kwargs))
        cmd_args.extend(args)
        context.notifier.git_cmd(core.list2cmdline(cmd_args))

    autodetect_proxy(context, kwargs)
    no_color(kwargs)
    return fn(*args, **kwargs)


def no_color(kwargs):
    """Augment kwargs with an _add_env environment dict that disables colors"""
    try:
        env = kwargs['_add_env']
    except KeyError:
        env = kwargs['_add_env'] = {}
    else:
        if env is None:
            env = kwargs['_add_env'] = {}
    env['NO_COLOR'] = '1'
    env['TERM'] = 'dumb'


def autodetect_proxy(context, kwargs):
    """Detect proxy settings when running on Gnome and KDE"""
    # kwargs can refer to persistent global state so we purge it.
    # Callers should not expect their _add_env to persist.
    kwargs.pop('_add_env', None)
    enabled = prefs.autodetect_proxy(context)
    if not enabled:
        return
    # If "git config http.proxy" is configured then there's nothing to do.
    http_proxy = prefs.http_proxy(context)
    if http_proxy:
        Interaction.log(
            N_('http proxy configured by "git config http.proxy %(url)s"')
            % dict(url=http_proxy)
        )
        return
    # This function has the side-effect of updating the kwargs dict.
    # The "_add_env" parameter gets forwarded to the __getattr__ git function's
    # _add_env option which forwards to core.run_command()'s add_env option.
    add_env = autodetect_proxy_environ()
    if add_env:
        kwargs['_add_env'] = add_env


def autodetect_proxy_environ():
    """Return the environment variables used for configuring proxies"""
    add_env = {}
    xdg_current_desktop = core.getenv('XDG_CURRENT_DESKTOP', default='')
    if not xdg_current_desktop:
        return add_env

    http_proxy = None
    https_proxy = None
    if xdg_current_desktop == 'KDE' or xdg_current_desktop.endswith(':KDE'):
        kreadconfig = core.find_executable('kreadconfig5')
        if kreadconfig:
            http_proxy = autodetect_proxy_kde(kreadconfig, 'http')
            https_proxy = autodetect_proxy_kde(kreadconfig, 'https')
    elif xdg_current_desktop:
        # If we're not on KDE then we'll fallback to GNOME / gsettings.
        gsettings = core.find_executable('gsettings')
        if gsettings and autodetect_proxy_gnome_is_enabled(gsettings):
            http_proxy = autodetect_proxy_gnome(gsettings, 'http')
            https_proxy = autodetect_proxy_gnome(gsettings, 'https')

    if os.environ.get('http_proxy'):
        Interaction.log(
            N_('http proxy configured by the "http_proxy" environment variable')
        )
    elif http_proxy:
        Interaction.log(
            N_('%(scheme)s proxy configured from %(desktop)s settings: %(url)s')
            % dict(scheme='http', desktop=xdg_current_desktop, url=http_proxy)
        )
        add_env['http_proxy'] = http_proxy

    if os.environ.get('https_proxy', None):
        Interaction.log(
            N_('https proxy configured by the "https_proxy" environment variable')
        )
    elif https_proxy:
        Interaction.log(
            N_('%(scheme)s proxy configured from %(desktop)s settings: %(url)s')
            % dict(scheme='https', desktop=xdg_current_desktop, url=https_proxy)
        )
        add_env['https_proxy'] = https_proxy

    return add_env


def autodetect_proxy_gnome_is_enabled(gsettings):
    """Is the proxy manually configured on Gnome?"""
    status, out, _ = core.run_command(
        [gsettings, 'get', 'org.gnome.system.proxy', 'mode']
    )
    return status == 0 and out.strip().strip("'") == 'manual'


def autodetect_proxy_gnome(gsettings, scheme):
    """Return the configured HTTP proxy for Gnome"""
    status, out, _ = core.run_command(
        [gsettings, 'get', f'org.gnome.system.proxy.{scheme}', 'host']
    )
    if status != 0:
        return None
    host = out.strip().strip("'")
    port = ''
    status, out, _ = core.run_command(
        [gsettings, 'get', f'org.gnome.system.proxy.{scheme}', 'port']
    )
    if status == 0:
        port = ':' + out.strip()
    proxy = host + port
    return proxy


def autodetect_proxy_kde(kreadconfig, scheme):
    """Return the configured HTTP proxy for KDE"""
    cmd = [
        kreadconfig,
        '--file',
        'kioslaverc',
        '--group',
        'Proxy Settings',
        '--key',
        'ProxyType',
    ]
    status, out, err = core.run_command(cmd)
    if status == 0 and out.strip() == '1':
        cmd = [
            kreadconfig,
            '--file',
            'kioslaverc',
            '--group',
            'Proxy Settings',
            '--key',
            f'{scheme}Proxy',
        ]
        status, out, err = core.run_command(cmd)
        if status == 0:
            proxy = out.strip().replace(' ', ':')
            return proxy
        return None
    return None
