"""Provides commands and queries for Git."""
from __future__ import division, absolute_import, unicode_literals

import re
from io import StringIO

from cola import core
from cola import gitcfg
from cola import utils
from cola import version
from cola.git import git
from cola.git import STDOUT
from cola.i18n import N_


EMPTY_TREE_SHA1 = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'


class InvalidRepositoryError(Exception):
    pass


def default_remote(config=None):
    """Return the remote tracked by the current branch."""
    if config is None:
        config = gitcfg.current()
    return config.get('branch.%s.remote' % current_branch())


def diff_index_filenames(ref):
    """Return a of filenames that have been modified relative to the index"""
    out = git.diff_index(ref, name_only=True, z=True)[STDOUT]
    return _parse_diff_filenames(out)


def diff_filenames(*args):
    """Return a list of filenames that have been modified"""
    out = git.diff_tree(name_only=True, no_commit_id=True, r=True, z=True,
                        *args)[STDOUT]
    return _parse_diff_filenames(out)


def diff(args):
    """Return a list of filenames for the given diff arguments

    :param args: list of arguments to pass to "git diff --name-only"

    """
    out = git.diff(name_only=True, z=True, *args)[STDOUT]
    return _parse_diff_filenames(out)


def _parse_diff_filenames(out):
    if out:
        return out[:-1].split('\0')
    else:
        return []


def tracked_files(*args):
    """Return the names of all files in the repository"""
    out = git.ls_files('--', *args, z=True)[STDOUT]
    if out:
        return sorted(out[:-1].split('\0'))
    else:
        return []


def all_files(*args):
    """Returns a sorted list of all files, including untracked files."""
    ls_files = git.ls_files('--', *args,
                            z=True,
                            cached=True,
                            others=True,
                            exclude_standard=True)[STDOUT]
    return sorted([f for f in ls_files.split('\0') if f])


class _current_branch:
    """Cache for current_branch()"""
    key = None
    value = None


def reset():
    _current_branch.key = None


def current_branch():
    """Return the current branch"""
    head = git.git_path('HEAD')
    try:
        key = core.stat(head).st_mtime
        if _current_branch.key == key:
            return _current_branch.value
    except OSError:
        # OSError means we can't use the stat cache
        key = 0

    status, data, err = git.rev_parse('HEAD', symbolic_full_name=True)
    if status != 0:
        # git init -- read .git/HEAD.  We could do this unconditionally...
        data = _read_git_head(head)

    for refs_prefix in ('refs/heads/', 'refs/remotes/', 'refs/tags/'):
        if data.startswith(refs_prefix):
            value = data[len(refs_prefix):]
            _current_branch.key = key
            _current_branch.value = value
            return value
    # Detached head
    return data


def _read_git_head(head, default='master', git=git):
    """Pure-python .git/HEAD reader"""
    # Legacy .git/HEAD symlinks
    if core.islink(head):
        refs_heads = core.realpath(git.git_path('refs', 'heads'))
        path = core.abspath(head).replace('\\', '/')
        if path.startswith(refs_heads + '/'):
            return path[len(refs_heads)+1:]

    # Common .git/HEAD "ref: refs/heads/master" file
    elif core.isfile(head):
        data = core.read(head).rstrip()
        ref_prefix = 'ref: '
        if data.startswith(ref_prefix):
            return data[len(ref_prefix):]
        # Detached head
        return data

    return default


def branch_list(remote=False):
    """
    Return a list of local or remote branches

    This explicitly removes HEAD from the list of remote branches.

    """
    if remote:
        return for_each_ref_basename('refs/remotes')
    else:
        return for_each_ref_basename('refs/heads')


def for_each_ref_basename(refs, git=git):
    """Return refs starting with 'refs'."""
    out = git.for_each_ref(refs, format='%(refname)')[STDOUT]
    output = out.splitlines()
    non_heads = filter(lambda x: not x.endswith('/HEAD'), output)
    return list(map(lambda x: x[len(refs) + 1:], non_heads))


def all_refs(split=False, git=git):
    """Return a tuple of (local branches, remote branches, tags)."""
    local_branches = []
    remote_branches = []
    tags = []
    triple = lambda x, y: (x, len(x) + 1, y)
    query = (triple('refs/tags', tags),
             triple('refs/heads', local_branches),
             triple('refs/remotes', remote_branches))
    out = git.for_each_ref(format='%(refname)')[STDOUT]
    for ref in out.splitlines():
        for prefix, prefix_len, dst in query:
            if ref.startswith(prefix) and not ref.endswith('/HEAD'):
                dst.append(ref[prefix_len:])
                continue
    if split:
        return local_branches, remote_branches, tags
    else:
        return local_branches + remote_branches + tags


def tracked_branch(branch=None, config=None):
    """Return the remote branch associated with 'branch'."""
    if config is None:
        config = gitcfg.current()
    if branch is None:
        branch = current_branch()
    if branch is None:
        return None
    remote = config.get('branch.%s.remote' % branch)
    if not remote:
        return None
    merge_ref = config.get('branch.%s.merge' % branch)
    if not merge_ref:
        return None
    refs_heads = 'refs/heads/'
    if merge_ref.startswith(refs_heads):
        return remote + '/' + merge_ref[len(refs_heads):]
    return None


def untracked_files(git=git, paths=None):
    """Returns a sorted list of untracked files."""

    if paths is None:
        paths = []
    args = ['--'] + paths
    out = git.ls_files(z=True, others=True, exclude_standard=True,
                       *args)[STDOUT]
    if out:
        return out[:-1].split('\0')
    return []


def tag_list():
    """Return a list of tags."""
    return list(reversed(for_each_ref_basename('refs/tags')))


def log(git, *args, **kwargs):
    return git.log(no_color=True, no_abbrev_commit=True,
                   no_ext_diff=True, *args, **kwargs)[STDOUT]


def commit_diff(sha1, git=git):
    return log(git, '-1', sha1, '--') + '\n\n' + sha1_diff(git, sha1)


_diff_overrides = {}
def update_diff_overrides(space_at_eol, space_change,
                          all_space, function_context):
    _diff_overrides['ignore_space_at_eol'] = space_at_eol
    _diff_overrides['ignore_space_change'] = space_change
    _diff_overrides['ignore_all_space'] = all_space
    _diff_overrides['function_context'] = function_context


def common_diff_opts(config=None):
    if config is None:
        config = gitcfg.current()
    submodule = version.check('diff-submodule', version.git_version())
    opts = {
        'patience': True,
        'submodule': submodule,
        'no_color': True,
        'no_ext_diff': True,
        'unified': config.get('gui.diffcontext', 3),
        '_raw': True,
    }
    opts.update(_diff_overrides)
    return opts


def _add_filename(args, filename):
    if filename:
        args.extend(['--', filename])


def sha1_diff(git, sha1, filename=None):
    """Return the diff for a sha1"""
    # Naively "$sha1^!" is what we'd like to use but that doesn't
    # give the correct result for merges--the diff is reversed.
    # Be explicit and compare sha1 against its first parent.
    args = [sha1 + '~', sha1]
    opts = common_diff_opts()
    _add_filename(args, filename)
    status, out, err = git.diff(*args, **opts)
    if status != 0:
        # We probably don't have "$sha1~" because this is the root commit.
        # "git show" is clever enough to handle the root commit.
        args = [sha1 + '^!']
        _add_filename(args, filename)
        status, out, err = git.show(pretty='format:', *args, **opts)
        out = out.lstrip()
    return out


def diff_info(sha1, git=git, filename=None):
    decoded = log(git, '-1', sha1, '--', pretty='format:%b').strip()
    if decoded:
        decoded += '\n\n'
    return decoded + sha1_diff(git, sha1, filename=filename)


def diff_helper(commit=None,
                ref=None,
                endref=None,
                filename=None,
                cached=True,
                deleted=False,
                head=None,
                amending=False,
                with_diff_header=False,
                suppress_header=True,
                reverse=False,
                git=git):
    "Invokes git diff on a filepath."
    if commit:
        ref, endref = commit+'^', commit
    argv = []
    if ref and endref:
        argv.append('%s..%s' % (ref, endref))
    elif ref:
        for r in utils.shell_split(ref.strip()):
            argv.append(r)
    elif head and amending and cached:
        argv.append(head)

    encoding = None
    if filename:
        argv.append('--')
        if type(filename) is list:
            argv.extend(filename)
        else:
            argv.append(filename)
            cfg = gitcfg.current()
            encoding = cfg.file_encoding(filename)

    status, out, err = git.diff(R=reverse, M=True, cached=cached,
                                _encoding=encoding,
                                *argv,
                                **common_diff_opts())
    if status != 0:
        # git init
        if with_diff_header:
            return ('', '')
        else:
            return ''

    return extract_diff_header(status, deleted,
                               with_diff_header, suppress_header, out)


def extract_diff_header(status, deleted,
                        with_diff_header, suppress_header, diffoutput):
    headers = []

    if diffoutput.startswith('Submodule'):
        if with_diff_header:
            return ('', diffoutput)
        else:
            return diffoutput

    start = False
    del_tag = 'deleted file mode '
    output = StringIO()

    diff = diffoutput.split('\n')
    for line in diff:
        if not start and '@@' == line[:2] and '@@' in line[2:]:
            start = True
        if start or (deleted and del_tag in line):
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


def format_patchsets(to_export, revs, output='patches'):
    """
    Group contiguous revision selection into patchsets

    Exists to handle multi-selection.
    Multiple disparate ranges in the revision selection
    are grouped into continuous lists.

    """

    outs = []
    errs = []

    cur_rev = to_export[0]
    cur_master_idx = revs.index(cur_rev)

    patches_to_export = [[cur_rev]]
    patchset_idx = 0

    # Group the patches into continuous sets
    for idx, rev in enumerate(to_export[1:]):
        # Limit the search to the current neighborhood for efficiency
        master_idx = revs[cur_master_idx:].index(rev)
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
        stat, out, err = export_patchset(patchset[0],
                                         patchset[-1],
                                         output='patches',
                                         n=len(patchset) > 1,
                                         thread=True,
                                         patch_with_stat=True)
        outs.append(out)
        if err:
            errs.append(err)
        status = max(stat, status)
    return (status, '\n'.join(outs), '\n'.join(errs))


def export_patchset(start, end, output='patches', **kwargs):
    """Export patches from start^ to end."""
    return git.format_patch('-o', output, start + '^..' + end, **kwargs)


def unstage_paths(args, head='HEAD'):
    status, out, err = git.reset(head, '--', *set(args))
    if status == 128:
        # handle git init: we have to use 'git rm --cached'
        # detect this condition by checking if the file is still staged
        return untrack_paths(args, head=head)
    else:
        return (status, out, err)


def untrack_paths(args, head='HEAD'):
    if not args:
        return (-1, N_('Nothing to do'), '')
    return git.update_index('--', force_remove=True, *set(args))


def worktree_state(head='HEAD',
                   update_index=False,
                   display_untracked=True,
                   paths=None):
    """Return a dict of files in various states of being

    :rtype: dict, keys are staged, unstaged, untracked, unmerged,
            changed_upstream, and submodule.

    """
    if update_index:
        git.update_index(refresh=True)

    staged, unmerged, staged_deleted, staged_submods = diff_index(head,
                                                                  paths=paths)
    modified, unstaged_deleted, modified_submods = diff_worktree(paths)
    untracked = display_untracked and untracked_files(paths=paths) or []

    # Remove unmerged paths from the modified list
    if unmerged:
        unmerged_set = set(unmerged)
        modified = [path for path in modified if path not in unmerged_set]

    # Look for upstream modified files if this is a tracking branch
    upstream_changed = diff_upstream(head)

    # Keep stuff sorted
    staged.sort()
    modified.sort()
    unmerged.sort()
    untracked.sort()
    upstream_changed.sort()

    return {'staged': staged,
            'modified': modified,
            'unmerged': unmerged,
            'untracked': untracked,
            'upstream_changed': upstream_changed,
            'staged_deleted': staged_deleted,
            'unstaged_deleted': unstaged_deleted,
            'submodules': staged_submods | modified_submods}


def _parse_raw_diff(out):
    while out:
        info, path, out = out.split('\0', 2)
        status = info[-1]
        is_submodule = ('160000' in info[1:14])
        yield (path, status, is_submodule)


def diff_index(head, cached=True, paths=None):
    staged = []
    unmerged = []
    deleted = set()
    submodules = set()

    if paths is None:
        paths = []
    args = [head, '--'] + paths
    status, out, err = git.diff_index(cached=cached, z=True, *args)
    if status != 0:
        # handle git init
        args[0] = EMPTY_TREE_SHA1
        status, out, err = git.diff_index(cached=cached, z=True, *args)

    for path, status, is_submodule in _parse_raw_diff(out):
        if is_submodule:
            submodules.add(path)
        if status in 'DAMT':
            staged.append(path)
            if status == 'D':
                deleted.add(path)
        elif status == 'U':
            unmerged.append(path)

    return staged, unmerged, deleted, submodules


def diff_worktree(paths=None):
    modified = []
    deleted = set()
    submodules = set()

    if paths is None:
        paths = []
    args = ['--'] + paths
    status, out, err = git.diff_files(z=True, *args)
    for path, status, is_submodule in _parse_raw_diff(out):
        if is_submodule:
            submodules.add(path)
        if status in 'DAMT':
            modified.append(path)
            if status == 'D':
                deleted.add(path)

    return modified, deleted, submodules


def diff_upstream(head):
    tracked = tracked_branch()
    if not tracked:
        return []
    base = merge_base(head, tracked)
    return diff_filenames(base, tracked)


def _branch_status(branch):
    """
    Returns a tuple of staged, unstaged, untracked, and unmerged files

    This shows only the changes that were introduced in branch

    """
    staged = diff_filenames(branch)
    return {'staged': staged,
            'upstream_changed': staged}


def merge_base(head, ref):
    """Given `ref`, return $(git merge-base ref HEAD)..ref."""
    return git.merge_base(head, ref)[STDOUT]


def merge_base_parent(branch):
    tracked = tracked_branch(branch=branch)
    if tracked:
        return tracked
    return 'HEAD'


def parse_ls_tree(rev):
    """Return a list of(mode, type, sha1, path) tuples."""
    output = []
    lines = git.ls_tree(rev, r=True)[STDOUT].splitlines()
    regex = re.compile(r'^(\d+)\W(\w+)\W(\w+)[ \t]+(.*)$')
    for line in lines:
        match = regex.match(line)
        if match:
            mode = match.group(1)
            objtype = match.group(2)
            sha1 = match.group(3)
            filename = match.group(4)
            output.append((mode, objtype, sha1, filename,) )
    return output


# A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile(r'^([0-9a-f]{40}) (.*)$')

def parse_rev_list(raw_revs):
    """Parse `git log --pretty=online` output into (SHA-1, summary) pairs."""
    revs = []
    for line in raw_revs.splitlines():
        match = REV_LIST_REGEX.match(line)
        if match:
            rev_id = match.group(1)
            summary = match.group(2)
            revs.append((rev_id, summary,))
    return revs


def log_helper(all=False, extra_args=None):
    """Return parallel arrays containing the SHA-1s and summaries."""
    revs = []
    summaries = []
    args = []
    if extra_args:
        args = extra_args
    output = log(git, pretty='oneline', all=all, *args)
    for line in output.splitlines():
        match = REV_LIST_REGEX.match(line)
        if match:
            revs.append(match.group(1))
            summaries.append(match.group(2))
    return (revs, summaries)


def rev_list_range(start, end):
    """Return a (SHA-1, summary) pairs between start and end."""
    revrange = '%s..%s' % (start, end)
    out = git.rev_list(revrange, pretty='oneline')[STDOUT]
    return parse_rev_list(out)


def commit_message_path():
    """Return the path to .git/GIT_COLA_MSG"""
    path = git.git_path("GIT_COLA_MSG")
    if core.exists(path):
        return path
    return None


def merge_message_path():
    """Return the path to .git/MERGE_MSG or .git/SQUASH_MSG."""
    for basename in ('MERGE_MSG', 'SQUASH_MSG'):
        path = git.git_path(basename)
        if core.exists(path):
            return path
    return None


def abort_merge():
    """Abort a merge by reading the tree at HEAD."""
    # Reset the worktree
    git.read_tree('HEAD', reset=True, u=True, v=True)
    # remove MERGE_HEAD
    merge_head = git.git_path('MERGE_HEAD')
    if core.exists(merge_head):
        core.unlink(merge_head)
    # remove MERGE_MESSAGE, etc.
    merge_msg_path = merge_message_path()
    while merge_msg_path:
        core.unlink(merge_msg_path)
        merge_msg_path = merge_message_path()


def merge_message(revision):
    """Return a merge message for FETCH_HEAD."""
    fetch_head = git.git_path('FETCH_HEAD')
    if core.exists(fetch_head):
        return git.fmt_merge_msg('--file', fetch_head)[STDOUT]
    return "Merge branch '%s'" % revision
