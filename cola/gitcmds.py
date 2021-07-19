"""Git commands and queries for Git"""
from __future__ import absolute_import, division, print_function, unicode_literals
import json
import os
import re
from io import StringIO

from . import core
from . import utils
from . import version
from .git import STDOUT
from .git import EMPTY_TREE_OID
from .git import OID_LENGTH
from .i18n import N_
from .interaction import Interaction


class InvalidRepositoryError(Exception):
    pass


def add(context, items, u=False):
    """Run "git add" while preventing argument overflow"""
    fn = context.git.add
    return utils.slice_fn(
        items, lambda paths: fn('--', force=True, verbose=True, u=u, *paths)
    )


def apply_diff(context, filename):
    git = context.git
    return git.apply(filename, index=True, cached=True)


def apply_diff_to_worktree(context, filename):
    git = context.git
    return git.apply(filename)


def get_branch(context, branch):
    if branch is None:
        branch = current_branch(context)
    return branch


def upstream_remote(context, branch=None):
    """Return the remote associated with the specified branch"""
    config = context.cfg
    branch = get_branch(context, branch)
    return config.get('branch.%s.remote' % branch)


def remote_url(context, remote, push=False):
    """Return the URL for the specified remote"""
    config = context.cfg
    url = config.get('remote.%s.url' % remote, '')
    if push:
        url = config.get('remote.%s.pushurl' % remote, url)
    return url


def diff_index_filenames(context, ref):
    """
    Return a diff of filenames that have been modified relative to the index
    """
    git = context.git
    out = git.diff_index(ref, name_only=True, z=True)[STDOUT]
    return _parse_diff_filenames(out)


def diff_filenames(context, *args):
    """Return a list of filenames that have been modified"""
    git = context.git
    out = git.diff_tree(
        name_only=True, no_commit_id=True, r=True, z=True, _readonly=True, *args
    )[STDOUT]
    return _parse_diff_filenames(out)


def listdir(context, dirname, ref='HEAD'):
    """Get the contents of a directory according to Git

    Query Git for the content of a directory, taking ignored
    files into account.

    """
    dirs = []
    files = []

    # first, parse git ls-tree to get the tracked files
    # in a list of (type, path) tuples
    entries = ls_tree(context, dirname, ref=ref)
    for entry in entries:
        if entry[0][0] == 't':  # tree
            dirs.append(entry[1])
        else:
            files.append(entry[1])

    # gather untracked files
    untracked = untracked_files(context, paths=[dirname], directory=True)
    for path in untracked:
        if path.endswith('/'):
            dirs.append(path[:-1])
        else:
            files.append(path)

    dirs.sort()
    files.sort()

    return (dirs, files)


def diff(context, args):
    """Return a list of filenames for the given diff arguments

    :param args: list of arguments to pass to "git diff --name-only"

    """
    git = context.git
    out = git.diff(name_only=True, z=True, *args)[STDOUT]
    return _parse_diff_filenames(out)


def _parse_diff_filenames(out):
    if out:
        return out[:-1].split('\0')
    return []


def tracked_files(context, *args):
    """Return the names of all files in the repository"""
    git = context.git
    out = git.ls_files('--', *args, z=True)[STDOUT]
    if out:
        return sorted(out[:-1].split('\0'))
    return []


def all_files(context, *args):
    """Returns a sorted list of all files, including untracked files."""
    git = context.git
    ls_files = git.ls_files(
        '--', *args, z=True, cached=True, others=True, exclude_standard=True
    )[STDOUT]
    return sorted([f for f in ls_files.split('\0') if f])


class _current_branch(object):
    """Cache for current_branch()"""

    key = None
    value = None


def reset():
    _current_branch.key = None


def current_branch(context):
    """Return the current branch"""
    git = context.git
    head = git.git_path('HEAD')
    try:
        key = core.stat(head).st_mtime
        if _current_branch.key == key:
            return _current_branch.value
    except OSError:
        # OSError means we can't use the stat cache
        key = 0

    status, data, _ = git.rev_parse('HEAD', symbolic_full_name=True)
    if status != 0:
        # git init -- read .git/HEAD.  We could do this unconditionally...
        data = _read_git_head(context, head)

    for refs_prefix in ('refs/heads/', 'refs/remotes/', 'refs/tags/'):
        if data.startswith(refs_prefix):
            value = data[len(refs_prefix) :]
            _current_branch.key = key
            _current_branch.value = value
            return value
    # Detached head
    return data


def _read_git_head(context, head, default='main'):
    """Pure-python .git/HEAD reader"""
    # Common .git/HEAD "ref: refs/heads/main" files
    git = context.git
    islink = core.islink(head)
    if core.isfile(head) and not islink:
        data = core.read(head).rstrip()
        ref_prefix = 'ref: '
        if data.startswith(ref_prefix):
            return data[len(ref_prefix) :]
        # Detached head
        return data
    # Legacy .git/HEAD symlinks
    elif islink:
        refs_heads = core.realpath(git.git_path('refs', 'heads'))
        path = core.abspath(head).replace('\\', '/')
        if path.startswith(refs_heads + '/'):
            return path[len(refs_heads) + 1 :]

    return default


def branch_list(context, remote=False):
    """
    Return a list of local or remote branches

    This explicitly removes HEAD from the list of remote branches.

    """
    if remote:
        return for_each_ref_basename(context, 'refs/remotes')
    return for_each_ref_basename(context, 'refs/heads')


def _version_sort(context, key='version:refname'):
    if version.check_git(context, 'version-sort'):
        sort = key
    else:
        sort = False
    return sort


def for_each_ref_basename(context, refs):
    """Return refs starting with 'refs'."""
    git = context.git
    sort = _version_sort(context)
    _, out, _ = git.for_each_ref(refs, format='%(refname)', sort=sort, _readonly=True)
    output = out.splitlines()
    non_heads = [x for x in output if not x.endswith('/HEAD')]
    offset = len(refs) + 1
    return [x[offset:] for x in non_heads]


def _triple(x, y):
    return (x, len(x) + 1, y)


def all_refs(context, split=False, sort_key='version:refname'):
    """Return a tuple of (local branches, remote branches, tags)."""
    git = context.git
    local_branches = []
    remote_branches = []
    tags = []
    triple = _triple
    query = (
        triple('refs/tags', tags),
        triple('refs/heads', local_branches),
        triple('refs/remotes', remote_branches),
    )
    sort = _version_sort(context, key=sort_key)
    _, out, _ = git.for_each_ref(format='%(refname)', sort=sort, _readonly=True)
    for ref in out.splitlines():
        for prefix, prefix_len, dst in query:
            if ref.startswith(prefix) and not ref.endswith('/HEAD'):
                dst.append(ref[prefix_len:])
                continue
    tags.reverse()
    if split:
        return local_branches, remote_branches, tags
    return local_branches + remote_branches + tags


def tracked_branch(context, branch=None):
    """Return the remote branch associated with 'branch'."""
    if branch is None:
        branch = current_branch(context)
    if branch is None:
        return None
    config = context.cfg
    remote = config.get('branch.%s.remote' % branch)
    if not remote:
        return None
    merge_ref = config.get('branch.%s.merge' % branch)
    if not merge_ref:
        return None
    refs_heads = 'refs/heads/'
    if merge_ref.startswith(refs_heads):
        return remote + '/' + merge_ref[len(refs_heads) :]
    return None


def parse_remote_branch(branch):
    """Split a remote branch apart into (remote, name) components"""
    rgx = re.compile(r'^(?P<remote>[^/]+)/(?P<branch>.+)$')
    match = rgx.match(branch)
    remote = ''
    branch = ''
    if match:
        remote = match.group('remote')
        branch = match.group('branch')
    return (remote, branch)


def untracked_files(context, paths=None, **kwargs):
    """Returns a sorted list of untracked files."""
    git = context.git
    if paths is None:
        paths = []
    args = ['--'] + paths
    out = git.ls_files(z=True, others=True, exclude_standard=True, *args, **kwargs)[
        STDOUT
    ]
    if out:
        return out[:-1].split('\0')
    return []


def tag_list(context):
    """Return a list of tags."""
    result = for_each_ref_basename(context, 'refs/tags')
    result.reverse()
    return result


def log(git, *args, **kwargs):
    return git.log(
        no_color=True,
        no_abbrev_commit=True,
        no_ext_diff=True,
        _readonly=True,
        *args,
        **kwargs
    )[STDOUT]


def commit_diff(context, oid):
    git = context.git
    return log(git, '-1', oid, '--') + '\n\n' + oid_diff(context, oid)


_diff_overrides = {}


def update_diff_overrides(space_at_eol, space_change, all_space, function_context):
    _diff_overrides['ignore_space_at_eol'] = space_at_eol
    _diff_overrides['ignore_space_change'] = space_change
    _diff_overrides['ignore_all_space'] = all_space
    _diff_overrides['function_context'] = function_context


def common_diff_opts(context):
    config = context.cfg
    # Default to --patience when diff.algorithm is unset
    patience = not config.get('diff.algorithm', default='')
    submodule = version.check_git(context, 'diff-submodule')
    opts = {
        'patience': patience,
        'submodule': submodule,
        'no_color': True,
        'no_ext_diff': True,
        'unified': config.get('gui.diffcontext', default=3),
        '_raw': True,
    }
    opts.update(_diff_overrides)
    return opts


def _add_filename(args, filename):
    if filename:
        args.extend(['--', filename])


def oid_diff(context, oid, filename=None):
    """Return the diff for an oid"""
    # Naively "$oid^!" is what we'd like to use but that doesn't
    # give the correct result for merges--the diff is reversed.
    # Be explicit and compare oid against its first parent.
    git = context.git
    args = [oid + '~', oid]
    opts = common_diff_opts(context)
    _add_filename(args, filename)
    status, out, _ = git.diff(*args, **opts)
    if status != 0:
        # We probably don't have "$oid~" because this is the root commit.
        # "git show" is clever enough to handle the root commit.
        args = [oid + '^!']
        _add_filename(args, filename)
        _, out, _ = git.show(pretty='format:', _readonly=True, *args, **opts)
        out = out.lstrip()
    return out


def diff_info(context, oid, filename=None):
    git = context.git
    decoded = log(git, '-1', oid, '--', pretty='format:%b').strip()
    if decoded:
        decoded += '\n\n'
    return decoded + oid_diff(context, oid, filename=filename)


# pylint: disable=too-many-arguments
def diff_helper(
    context,
    commit=None,
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
    untracked=False,
):
    "Invokes git diff on a filepath."
    git = context.git
    cfg = context.cfg
    if commit:
        ref, endref = commit + '^', commit
    argv = []
    if ref and endref:
        argv.append('%s..%s' % (ref, endref))
    elif ref:
        argv.extend(utils.shell_split(ref.strip()))
    elif head and amending and cached:
        argv.append(head)

    encoding = None
    if untracked:
        argv.append('--no-index')
        argv.append(os.devnull)
        argv.append(filename)
    elif filename:
        argv.append('--')
        if isinstance(filename, (list, tuple)):
            argv.extend(filename)
        else:
            argv.append(filename)
            encoding = cfg.file_encoding(filename)

    status, out, _ = git.diff(
        R=reverse,
        M=True,
        cached=cached,
        _encoding=encoding,
        *argv,
        **common_diff_opts(context)
    )

    success = status == 0

    # Diff will return 1 when comparing untracked file and it has change,
    # therefore we will check for diff header from output to differentiate
    # from actual error such as file not found.
    if untracked and status == 1:
        try:
            _, second, _ = out.split('\n', 2)
        except ValueError:
            second = ''
        success = second.startswith('new file mode ')

    if not success:
        # git init
        if with_diff_header:
            return ('', '')
        return ''

    result = extract_diff_header(deleted, with_diff_header, suppress_header, out)
    return core.UStr(result, out.encoding)


def extract_diff_header(deleted, with_diff_header, suppress_header, diffoutput):
    """Split a diff into a header section and payload section"""

    if diffoutput.startswith('Submodule'):
        if with_diff_header:
            return ('', diffoutput)
        return diffoutput

    start = False
    del_tag = 'deleted file mode '

    output = StringIO()
    headers = StringIO()

    for line in diffoutput.split('\n'):
        if not start and line[:2] == '@@' and '@@' in line[2:]:
            start = True
        if start or (deleted and del_tag in line):
            output.write(line + '\n')
        else:
            if with_diff_header:
                headers.write(line + '\n')
            elif not suppress_header:
                output.write(line + '\n')

    output_text = output.getvalue()
    output.close()

    headers_text = headers.getvalue()
    headers.close()

    if with_diff_header:
        return (headers_text, output_text)
    return output_text


def format_patchsets(context, to_export, revs, output='patches'):
    """
    Group contiguous revision selection into patchsets

    Exists to handle multi-selection.
    Multiple disparate ranges in the revision selection
    are grouped into continuous lists.

    """

    outs = []
    errs = []

    cur_rev = to_export[0]
    cur_rev_idx = revs.index(cur_rev)

    patches_to_export = [[cur_rev]]
    patchset_idx = 0

    # Group the patches into continuous sets
    for rev in to_export[1:]:
        # Limit the search to the current neighborhood for efficiency
        try:
            rev_idx = revs[cur_rev_idx:].index(rev)
            rev_idx += cur_rev_idx
        except ValueError:
            rev_idx = revs.index(rev)

        if rev_idx == cur_rev_idx + 1:
            patches_to_export[patchset_idx].append(rev)
            cur_rev_idx += 1
        else:
            patches_to_export.append([rev])
            cur_rev_idx = rev_idx
            patchset_idx += 1

    # Export each patchsets
    status = 0
    for patchset in patches_to_export:
        stat, out, err = export_patchset(
            context,
            patchset[0],
            patchset[-1],
            output=output,
            n=len(patchset) > 1,
            thread=True,
            patch_with_stat=True,
        )
        outs.append(out)
        if err:
            errs.append(err)
        status = max(stat, status)
    return (status, '\n'.join(outs), '\n'.join(errs))


def export_patchset(context, start, end, output='patches', **kwargs):
    """Export patches from start^ to end."""
    git = context.git
    return git.format_patch('-o', output, start + '^..' + end, **kwargs)


def reset_paths(context, head, items):
    """Run "git reset" while preventing argument overflow"""
    items = list(set(items))
    fn = context.git.reset
    status, out, err = utils.slice_fn(items, lambda paths: fn(head, '--', *paths))
    return (status, out, err)


def unstage_paths(context, args, head='HEAD'):
    """Unstage paths while accounting for git init"""
    status, out, err = reset_paths(context, head, args)
    if status == 128:
        # handle git init: we have to use 'git rm --cached'
        # detect this condition by checking if the file is still staged
        return untrack_paths(context, args)
    return (status, out, err)


def untrack_paths(context, args):
    if not args:
        return (-1, N_('Nothing to do'), '')
    git = context.git
    return git.update_index('--', force_remove=True, *set(args))


def worktree_state(
    context, head='HEAD', update_index=False, display_untracked=True, paths=None
):
    """Return a dict of files in various states of being

    :rtype: dict, keys are staged, unstaged, untracked, unmerged,
            changed_upstream, and submodule.

    """
    git = context.git
    if update_index:
        git.update_index(refresh=True)

    staged, unmerged, staged_deleted, staged_submods = diff_index(
        context, head, paths=paths
    )
    modified, unstaged_deleted, modified_submods = diff_worktree(context, paths)
    if display_untracked:
        untracked = untracked_files(context, paths=paths)
    else:
        untracked = []

    # Remove unmerged paths from the modified list
    if unmerged:
        unmerged_set = set(unmerged)
        modified = [path for path in modified if path not in unmerged_set]

    # Look for upstream modified files if this is a tracking branch
    upstream_changed = diff_upstream(context, head)

    # Keep stuff sorted
    staged.sort()
    modified.sort()
    unmerged.sort()
    untracked.sort()
    upstream_changed.sort()

    return {
        'staged': staged,
        'modified': modified,
        'unmerged': unmerged,
        'untracked': untracked,
        'upstream_changed': upstream_changed,
        'staged_deleted': staged_deleted,
        'unstaged_deleted': unstaged_deleted,
        'submodules': staged_submods | modified_submods,
    }


def _parse_raw_diff(out):
    while out:
        info, path, out = out.split('\0', 2)
        status = info[-1]
        is_submodule = '160000' in info[1:14]
        yield (path, status, is_submodule)


def diff_index(context, head, cached=True, paths=None):
    git = context.git
    staged = []
    unmerged = []
    deleted = set()
    submodules = set()

    if paths is None:
        paths = []
    args = [head, '--'] + paths
    status, out, _ = git.diff_index(cached=cached, z=True, *args)
    if status != 0:
        # handle git init
        args[0] = EMPTY_TREE_OID
        status, out, _ = git.diff_index(cached=cached, z=True, *args)

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


def diff_worktree(context, paths=None):
    git = context.git
    modified = []
    deleted = set()
    submodules = set()

    if paths is None:
        paths = []
    args = ['--'] + paths
    status, out, _ = git.diff_files(z=True, *args)
    for path, status, is_submodule in _parse_raw_diff(out):
        if is_submodule:
            submodules.add(path)
        if status in 'DAMT':
            modified.append(path)
            if status == 'D':
                deleted.add(path)

    return modified, deleted, submodules


def diff_upstream(context, head):
    """Given `ref`, return $(git merge-base ref HEAD)..ref."""
    tracked = tracked_branch(context)
    if not tracked:
        return []
    base = merge_base(context, head, tracked)
    return diff_filenames(context, base, tracked)


def list_submodule(context):
    """Return submodules in the format(state, sha1, path, describe)"""
    git = context.git
    status, data, _ = git.submodule('status')
    ret = []
    if status == 0 and data:
        data = data.splitlines()
        # see git submodule status
        # TODO better separation
        for line in data:
            state = line[0].strip()
            sha1 = line[1 : OID_LENGTH + 1]
            left_bracket = line.find('(', OID_LENGTH + 3)
            if left_bracket == -1:
                left_bracket = len(line) + 1
            path = line[OID_LENGTH + 2 : left_bracket - 1]
            describe = line[left_bracket + 1 : -1]
            ret.append((state, sha1, path, describe))
    return ret


def merge_base(context, head, ref):
    """Return the merge-base of head and ref"""
    git = context.git
    return git.merge_base(head, ref, _readonly=True)[STDOUT]


def merge_base_parent(context, branch):
    tracked = tracked_branch(context, branch=branch)
    if tracked:
        return tracked
    return 'HEAD'


# TODO Unused?
def parse_ls_tree(context, rev):
    """Return a list of (mode, type, oid, path) tuples."""
    output = []
    git = context.git
    lines = git.ls_tree(rev, r=True, _readonly=True)[STDOUT].splitlines()
    regex = re.compile(r'^(\d+)\W(\w+)\W(\w+)[ \t]+(.*)$')
    for line in lines:
        match = regex.match(line)
        if match:
            mode = match.group(1)
            objtype = match.group(2)
            oid = match.group(3)
            filename = match.group(4)
            output.append(
                (
                    mode,
                    objtype,
                    oid,
                    filename,
                )
            )
    return output


# TODO unused?
def ls_tree(context, path, ref='HEAD'):
    """Return a parsed git ls-tree result for a single directory"""
    git = context.git
    result = []
    status, out, _ = git.ls_tree(ref, '--', path, z=True, full_tree=True)
    if status == 0 and out:
        path_offset = 6 + 1 + 4 + 1 + OID_LENGTH + 1
        for line in out[:-1].split('\0'):
            #       1    1                                        1
            # .....6 ...4 ......................................40
            # 040000 tree c127cde9a0c644a3a8fef449a244f47d5272dfa6	relative
            # 100644 blob 139e42bf4acaa4927ec9be1ec55a252b97d3f1e2	relative/path
            # 0..... 7... 12......................................	53
            # path_offset = 6 + 1 + 4 + 1 + OID_LENGTH(40) + 1
            objtype = line[7:11]
            relpath = line[path_offset:]
            result.append((objtype, relpath))

    return result


# A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile(r'^([0-9a-f]{40}) (.*)$')


def parse_rev_list(raw_revs):
    """Parse `git log --pretty=online` output into (oid, summary) pairs."""
    revs = []
    for line in raw_revs.splitlines():
        match = REV_LIST_REGEX.match(line)
        if match:
            rev_id = match.group(1)
            summary = match.group(2)
            revs.append(
                (
                    rev_id,
                    summary,
                )
            )
    return revs


# pylint: disable=redefined-builtin
def log_helper(context, all=False, extra_args=None):
    """Return parallel arrays containing oids and summaries."""
    revs = []
    summaries = []
    args = []
    if extra_args:
        args = extra_args
    git = context.git
    output = log(git, pretty='oneline', all=all, *args)
    for line in output.splitlines():
        match = REV_LIST_REGEX.match(line)
        if match:
            revs.append(match.group(1))
            summaries.append(match.group(2))
    return (revs, summaries)


def rev_list_range(context, start, end):
    """Return (oid, summary) pairs between start and end."""
    git = context.git
    revrange = '%s..%s' % (start, end)
    out = git.rev_list(revrange, pretty='oneline')[STDOUT]
    return parse_rev_list(out)


def commit_message_path(context):
    """Return the path to .git/GIT_COLA_MSG"""
    git = context.git
    path = git.git_path('GIT_COLA_MSG')
    if core.exists(path):
        return path
    return None


def merge_message_path(context):
    """Return the path to .git/MERGE_MSG or .git/SQUASH_MSG."""
    git = context.git
    for basename in ('MERGE_MSG', 'SQUASH_MSG'):
        path = git.git_path(basename)
        if core.exists(path):
            return path
    return None


def prepare_commit_message_hook(context):
    """Run the cola.preparecommitmessagehook to prepare the commit message"""
    config = context.cfg
    default_hook = config.hooks_path('cola-prepare-commit-msg')
    return config.get('cola.preparecommitmessagehook', default=default_hook)


def abort_merge(context):
    """Abort a merge by reading the tree at HEAD."""
    # Reset the worktree
    git = context.git
    status, out, err = git.read_tree('HEAD', reset=True, u=True, v=True)
    # remove MERGE_HEAD
    merge_head = git.git_path('MERGE_HEAD')
    if core.exists(merge_head):
        core.unlink(merge_head)
    # remove MERGE_MESSAGE, etc.
    merge_msg_path = merge_message_path(context)
    while merge_msg_path:
        core.unlink(merge_msg_path)
        merge_msg_path = merge_message_path(context)
    return status, out, err


def strip_remote(remotes, remote_branch):
    for remote in remotes:
        prefix = remote + '/'
        if remote_branch.startswith(prefix):
            return remote_branch[len(prefix) :]
    return remote_branch.split('/', 1)[-1]


def parse_refs(context, argv):
    """Parse command-line arguments into object IDs"""
    git = context.git
    status, out, _ = git.rev_parse(*argv)
    if status == 0:
        oids = [oid for oid in out.splitlines() if oid]
    else:
        oids = argv
    return oids


def prev_commitmsg(context, *args):
    """Queries git for the latest commit message."""
    git = context.git
    return git.log('-1', no_color=True, pretty='format:%s%n%n%b', *args)[STDOUT]


def rev_parse(context, name):
    """Call git rev-parse and return the output"""
    git = context.git
    status, out, _ = git.rev_parse(name)
    if status == 0:
        result = out.strip()
    else:
        result = name
    return result


def write_blob(context, oid, filename):
    """Write a blob to a temporary file and return the path

    Modern versions of Git allow invoking filters.  Older versions
    get the object content as-is.

    """
    if version.check_git(context, 'cat-file-filters-path'):
        return cat_file_to_path(context, filename, oid)
    return cat_file_blob(context, filename, oid)


def cat_file_blob(context, filename, oid):
    return cat_file(context, filename, 'blob', oid)


def cat_file_to_path(context, filename, oid):
    return cat_file(context, filename, oid, path=filename, filters=True)


def cat_file(context, filename, *args, **kwargs):
    """Redirect git cat-file output to a path"""
    result = None
    git = context.git
    # Use the original filename in the suffix so that the generated filename
    # has the correct extension, and so that it resembles the original name.
    basename = os.path.basename(filename)
    suffix = '-' + basename  # ensures the correct filename extension
    path = utils.tmp_filename('blob', suffix=suffix)
    with open(path, 'wb') as fp:
        status, out, err = git.cat_file(
            _raw=True, _readonly=True, _stdout=fp, *args, **kwargs
        )
        Interaction.command(N_('Error'), 'git cat-file', status, out, err)
        if status == 0:
            result = path
    if not result:
        core.unlink(path)
    return result


def write_blob_path(context, head, oid, filename):
    """Use write_blob() when modern git is available"""
    if version.check_git(context, 'cat-file-filters-path'):
        return write_blob(context, oid, filename)
    return cat_file_blob(context, filename, head + ':' + filename)


def annex_path(context, head, filename):
    """Return the git-annex path for a filename at the specified commit"""
    git = context.git
    path = None
    annex_info = {}

    # unfortunately there's no way to filter this down to a single path
    # so we just have to scan all reported paths
    status, out, _ = git.annex('findref', '--json', head)
    if status == 0:
        for line in out.splitlines():
            info = json.loads(line)
            try:
                annex_file = info['file']
            except (ValueError, KeyError):
                continue
            # we only care about this file so we can skip the rest
            if annex_file == filename:
                annex_info = info
                break
    key = annex_info.get('key', '')
    if key:
        status, out, _ = git.annex('contentlocation', key)
        if status == 0 and os.path.exists(out):
            path = out

    return path


def is_binary(context, filename):
    cfg_is_binary = context.cfg.is_binary(filename)
    if cfg_is_binary is not None:
        return cfg_is_binary
    # This is the same heuristic as xdiff-interface.c:buffer_is_binary().
    size = 8000
    try:
        result = core.read(filename, size=size, encoding='bytes')
    except (IOError, OSError):
        result = b''

    return b'\0' in result


def is_valid_ref(context, ref):
    """Is the provided Git ref a valid refname?"""
    status, _, _ = context.git.rev_parse(ref, quiet=True, verify=True)
    return status == 0
