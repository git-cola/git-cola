"""Provides commands and queries for Git."""

import cola


def default_remote():
    model = cola.model()
    branch = model.currentbranch
    branchconfig = 'branch.%s.remote' % branch
    return model.local_config(branchconfig, 'origin')

def corresponding_remote_ref():
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
