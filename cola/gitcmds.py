"""Provides commands and queries for Git."""

import cola
from cola import core


def default_remote():
    """Return the remote tracked by the current branch."""
    model = cola.model()
    branch = model.currentbranch
    branchconfig = 'branch.%s.remote' % branch
    return model.local_config(branchconfig, 'origin')


def corresponding_remote_ref():
    """Return the remote branch tracked by the current branch."""
    model = cola.model()
    remote = default_remote()
    branch = model.currentbranch
    best_match = '%s/%s' % (remote, branch)
    remote_branches = model.remote_branches
    if not remote_branches:
        return remote
    for rb in remote_branches:
        if rb == best_match:
            return rb
    return remote_branches[0]


def diff_filenames(arg):
    """Return a list of filenames that have been modified"""
    model = cola.model()
    diff_zstr = model.git.diff(arg, name_only=True, z=True).rstrip('\0')
    return [core.decode(f) for f in diff_zstr.split('\0') if f]
