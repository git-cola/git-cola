"""Provides commands and queries for Git."""
import os

import cola
from cola import gitcmd
from cola import core
from cola import utils

git = gitcmd.instance()


def default_remote():
    """Return the remote tracked by the current branch."""
    branch = current_branch()
    branchconfig = 'branch.%s.remote' % branch
    model = cola.model()
    return model.local_config(branchconfig, 'origin')


def corresponding_remote_ref():
    """Return the remote branch tracked by the current branch."""
    remote = default_remote()
    branch = current_branch()
    best_match = '%s/%s' % (remote, branch)
    remote_branches = branch_list(remote=True)
    if not remote_branches:
        return remote
    for rb in remote_branches:
        if rb == best_match:
            return rb
    if remote_branches:
        return remote_branches[0]
    return remote


def diff_filenames(arg):
    """Return a list of filenames that have been modified"""
    diff_zstr = git.diff(arg, name_only=True, z=True).rstrip('\0')
    return [core.decode(f) for f in diff_zstr.split('\0') if f]


def all_files():
    """Return the names of all files in the repository"""
    return [core.decode(f)
            for f in git.ls_files(z=True)
                        .strip('\0').split('\0') if f]


class _current_branch:
    """Stat cache for current_branch()."""
    st_mtime = 0
    value = None


def current_branch():
    """Find the current branch."""
    model = cola.model()
    head = os.path.abspath(model.git_repo_path('HEAD'))

    try:
        st = os.stat(head)
        if _current_branch.st_mtime == st.st_mtime:
            return _current_branch.value
    except OSError, e:
        pass

    # Handle legacy .git/HEAD symlinks
    if os.path.islink(head):
        refs_heads = os.path.realpath(model.git_repo_path('refs', 'heads'))
        path = os.path.abspath(head).replace('\\', '/')
        if path.startswith(refs_heads + '/'):
            value = path[len(refs_heads)+1:]
            _current_branch.value = value
            _current_branch.st_mtime = st.st_mtime
            return value
        return ''

    # Handle the common .git/HEAD "ref: refs/heads/master" file
    if os.path.isfile(head):
        value = utils.slurp(head).strip()
        ref_prefix = 'ref: refs/heads/'
        if value.startswith(ref_prefix):
            value = value[len(ref_prefix):]

        _current_branch.st_mtime = st.st_mtime
        _current_branch.value = value
        return value

    # This shouldn't happen
    return ''


def branch_list(remote=False):
    """
    Return a list of local or remote branches

    This explicitly removes HEAD from the list of remote branches.

    """
    if remote:
        return for_each_ref_basename('refs/remotes/')
    else:
        return for_each_ref_basename('refs/heads/')


def for_each_ref_basename(refs):
    """Return refs starting with 'refs'."""
    output = git.for_each_ref(refs, format='%(refname)').splitlines()
    non_heads = filter(lambda x: not x.endswith('/HEAD'), output)
    return map(lambda x: x[len(refs):], non_heads)


def tracked_branch(branch=None):
    """Return the remote branch associated with 'branch'."""
    if branch is None:
        branch = current_branch()
    model = cola.model()
    branch_remote = 'local_branch_%s_remote' % branch
    if not model.has_param(branch_remote):
        return ''
    remote = model.param(branch_remote)
    if not remote:
        return ''
    branch_merge = 'local_branch_%s_merge' % branch
    if not model.has_param(branch_merge):
        return ''
    ref = model.param(branch_merge)
    refs_heads = 'refs/heads/'
    if ref.startswith(refs_heads):
        return remote + '/' + ref[len(refs_heads):]
    return ''


def untracked_files():
    """Returns a sorted list of all files, including untracked files."""
    ls_files = git.ls_files(z=True,
                            others=True,
                            exclude_standard=True)
    return [core.decode(f) for f in ls_files.split('\0') if f]


def tag_list():
    """Return a list of tags."""
    tags = for_each_ref_basename('refs/tags/')
    tags.reverse()
    return tags
