"""Provides commands and queries for Git."""
import os
import re
from cStringIO import StringIO

from cola import core
from cola import gitcfg
from cola import utils
from cola import version
from cola.compat import set
from cola.git import git
from cola.i18n import N_

config = gitcfg.instance()


class InvalidRepositoryError(StandardError):
    pass


def default_remote(config=None):
    """Return the remote tracked by the current branch."""
    if config is None:
        config = gitcfg.instance()
    return config.get('branch.%s.remote' % current_branch())


def diff_index_filenames(ref):
    """Return a of filenames that have been modified relative to the index"""
    diff_zstr = git.diff_index(ref, name_only=True, z=True)
    return _parse_diff_filenames(diff_zstr)


def diff_filenames(*args):
    """Return a list of filenames that have been modified"""
    diff_zstr = git.diff_tree(name_only=True,
                              no_commit_id=True, r=True, z=True, *args)
    return _parse_diff_filenames(diff_zstr)


def diff(args):
    """Return a list of filenames for the given diff arguments

    :param args: list of arguments to pass to "git diff --name-only"

    """
    diff_zstr = git.diff(name_only=True, z=True, *args)
    return _parse_diff_filenames(diff_zstr)


def _parse_diff_filenames(diff_zstr):
    if diff_zstr:
        return core.decode(diff_zstr[:-1]).split('\0')
    else:
        return []


def all_files():
    """Return the names of all files in the repository"""
    ls_files = git.ls_files(z=True)
    if ls_files:
        return core.decode(ls_files[:-1]).split('\0')
    else:
        return []


class _current_branch:
    """Cache for current_branch()"""
    key = None
    value = None


def clear_cache():
    _current_branch.key = None


def current_branch():
    """Return the current branch"""
    decode = core.decode
    head = git.git_path('HEAD')
    try:
        key = os.stat(head).st_mtime
        if _current_branch.key == key:
            return _current_branch.value
    except OSError:
        pass
    status, data = git.rev_parse('HEAD', symbolic_full_name=True, with_status=True)
    if status != 0:
        # git init -- read .git/HEAD.  We could do this unconditionally...
        data = _read_git_head(head)

    for refs_prefix in ('refs/heads/', 'refs/remotes/', 'refs/tags/'):
        if data.startswith(refs_prefix):
            value = decode(data[len(refs_prefix):])
            _current_branch.key = key
            _current_branch.value = value
            return value
    # Detached head
    return data


def _read_git_head(head, default='master', git=git):
    """Pure-python .git/HEAD reader"""
    # Legacy .git/HEAD symlinks
    if os.path.islink(head):
        refs_heads = os.path.realpath(git.git_path('refs', 'heads'))
        path = os.path.abspath(head).replace('\\', '/')
        if path.startswith(refs_heads + '/'):
            return path[len(refs_heads)+1:]

    # Common .git/HEAD "ref: refs/heads/master" file
    elif os.path.isfile(head):
        data = utils.slurp(core.decode(head)).rstrip()
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
    git_output = git.for_each_ref(refs, format='%(refname)')
    output = core.decode(git_output).splitlines()
    non_heads = filter(lambda x: not x.endswith('/HEAD'), output)
    return map(lambda x: x[len(refs) + 1:], non_heads)


def all_refs(split=False, git=git):
    """Return a tuple of (local branches, remote branches, tags)."""
    local_branches = []
    remote_branches = []
    tags = []
    triple = lambda x, y: (x, len(x) + 1, y)
    query = (triple('refs/tags', tags),
             triple('refs/heads', local_branches),
             triple('refs/remotes', remote_branches))
    cmdout = core.decode(git.for_each_ref(format='%(refname)'))
    for ref in cmdout.splitlines():
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
        config = gitcfg.instance()
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


def untracked_files(git=git):
    """Returns a sorted list of untracked files."""
    ls_files = git.ls_files(z=True, others=True, exclude_standard=True)
    if ls_files:
        return core.decode(ls_files[:-1]).split('\0')
    return []


def tag_list():
    """Return a list of tags."""
    tags = for_each_ref_basename('refs/tags')
    tags.reverse()
    return tags


def log(git, *args, **kwargs):
    return core.decode(git.log(no_color=True,
                               no_ext_diff=True,
                               *args, **kwargs))


def commit_diff(sha1, git=git):
    return log(git, '-1', sha1) + '\n\n' + sha1_diff(git, sha1)


_diff_overrides = {}
def update_diff_overrides(space_at_eol, space_change,
                          all_space, function_context):
    _diff_overrides['ignore_space_at_eol'] = space_at_eol
    _diff_overrides['ignore_space_change'] = space_change
    _diff_overrides['ignore_all_space'] = all_space
    _diff_overrides['function_context'] = function_context


def _common_diff_opts(config=config):
    submodule = version.check('diff-submodule', version.git_version())
    opts = {
        'patience': True,
        'submodule': submodule,
        'no_color': True,
        'no_ext_diff': True,
        'with_raw_output': True,
        'with_stderr': True,
        'unified': config.get('gui.diffcontext', 3),
    }
    opts.update(_diff_overrides)
    return opts


def sha1_diff(git, sha1):
    return core.decode(git.diff(sha1+'~', sha1, **_common_diff_opts()))


def diff_info(sha1, git=git):
    decoded = log(git, '-1', sha1, pretty='format:%b').strip()
    if decoded:
        decoded += '\n\n'
    return decoded + sha1_diff(git, sha1)


def diff_helper(commit=None,
                ref=None,
                endref=None,
                filename=None,
                cached=True,
                head=None,
                amending=False,
                with_diff_header=False,
                suppress_header=True,
                reverse=False,
                git=git):
    "Invokes git diff on a filepath."
    encode = core.encode
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
            encoding = config.file_encoding(filename)


    if filename is not None:
        deleted = cached and not os.path.exists(encode(filename))
    else:
        deleted = False

    status, diffoutput = git.diff(R=reverse, M=True, cached=cached,
                                  with_status=True,
                                  *argv, **_common_diff_opts())
    if status != 0:
        # git init
        if with_diff_header:
            return ('', '')
        else:
            return ''

    return extract_diff_header(status, deleted, encoding,
                               with_diff_header, suppress_header, diffoutput)


def extract_diff_header(status, deleted, encoding,
                        with_diff_header, suppress_header, diffoutput):
    encode = core.encode
    headers = []

    if diffoutput.startswith('Submodule'):
        if with_diff_header:
            return ('', diffoutput)
        else:
            return diffoutput

    start = False
    del_tag = 'deleted file mode '
    output = StringIO()

    diff = core.decode(diffoutput, encoding=encoding).split('\n')
    for line in diff:
        if not start and '@@' == line[:2] and '@@' in line[2:]:
            start = True
        if start or (deleted and del_tag in line):
            output.write(encode(line) + '\n')
        else:
            if with_diff_header:
                headers.append(encode(line))
            elif not suppress_header:
                output.write(encode(line) + '\n')

    result = core.decode(output.getvalue())
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

    outlines = []

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
        newstatus, out = export_patchset(patchset[0],
                                         patchset[-1],
                                         output='patches',
                                         n=len(patchset) > 1,
                                         thread=True,
                                         patch_with_stat=True)
        outlines.append(out)
        if status == 0:
            status += newstatus
    return (status, '\n'.join(outlines))


def export_patchset(start, end, output='patches', **kwargs):
    """Export patches from start^ to end."""
    return git.format_patch('-o', output, start + '^..' + end,
                            with_stderr=True,
                            with_status=True,
                            **kwargs)


def unstage_paths(args, head='HEAD'):
    status, output = git.reset(head, '--', with_status=True,
                               *set(args))
    if status == 128:
        # handle git init: we have to use 'git rm --cached'
        # detect this condition by checking if the file is still staged
        return untrack_paths(args, head=head)
    else:
        return (status, output)


def untrack_paths(args, head='HEAD'):
    if not args:
        return (-1, N_('Nothing to do'))
    return git.update_index('--', force_remove=True,
                            with_status=True, *set(args))


def worktree_state(head='HEAD'):
    """Return a tuple of files in various states of being

    Can be staged, unstaged, untracked, unmerged, or changed
    upstream.

    """
    state = worktree_state_dict(head=head)
    return(state.get('staged', []),
           state.get('modified', []),
           state.get('unmerged', []),
           state.get('untracked', []),
           state.get('upstream_changed', []))


def worktree_state_dict(head='HEAD', update_index=False):
    """Return a dict of files in various states of being

    :rtype: dict, keys are staged, unstaged, untracked, unmerged,
            changed_upstream, and submodule.

    """
    if update_index:
        git.update_index(refresh=True)

    staged, unmerged, staged_submods = diff_index(head)
    modified, modified_submods = diff_worktree()
    untracked = untracked_files()

    # Remove unmerged paths from the modified list
    unmerged_set = set(unmerged)
    modified_set = set(modified)
    modified_unmerged = modified_set.intersection(unmerged_set)
    for path in modified_unmerged:
        modified.remove(path)

    # All submodules
    submodules = staged_submods.union(modified_submods)

    # Only include the submodule in the staged list once it has
    # been staged.  Otherwise, we'll see the submodule as being
    # both modified and staged.
    modified_submods = modified_submods.difference(staged_submods)

    # Add submodules to the staged and unstaged lists
    staged.extend(list(staged_submods))
    modified.extend(list(modified_submods))

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
            'submodules': submodules}


def diff_index(head, cached=True):
    decode = core.decode
    submodules = set()
    staged = []
    unmerged = []

    status, output = git.diff_index(head, cached=cached,
                                    z=True, with_status=True)
    if status != 0:
        # handle git init
        return all_files(), unmerged, submodules

    while output:
        rest, output = output.split('\0', 1)
        name, output = output.split('\0', 1)
        status = rest[-1]
        name = decode(name)
        if '160000' in rest[1:14]:
            submodules.add(name)
        elif status  in 'DAMT':
            staged.append(name)
        elif status == 'U':
            unmerged.append(name)

    return staged, unmerged, submodules


def diff_worktree():
    modified = []
    submodules = set()

    status, output = git.diff_files(z=True, with_status=True)
    if status != 0:
        # handle git init
        ls_files = core.decode(git.ls_files(modified=True, z=True))
        if ls_files:
            modified = ls_files[:-1].split('\0')
        return modified, submodules

    while output:
        rest, output = output.split('\0', 1)
        name, output = output.split('\0', 1)
        status = rest[-1]
        name = core.decode(name)
        if '160000' in rest[1:14]:
            submodules.add(name)
        elif status in 'DAMT':
            modified.append(name)

    return modified, submodules


def diff_upstream(head):
    tracked = tracked_branch()
    if not tracked:
        return []
    merge_base = merge_base_to(head, tracked)
    return diff_filenames(merge_base, tracked)


def _branch_status(branch):
    """
    Returns a tuple of staged, unstaged, untracked, and unmerged files

    This shows only the changes that were introduced in branch

    """
    staged = diff_filenames(branch)
    return {'staged': staged,
            'upstream_changed': staged}


def merge_base_to(head, ref):
    """Given `ref`, return $(git merge-base ref HEAD)..ref."""
    return git.merge_base(head, ref)


def merge_base_parent(branch):
    tracked = tracked_branch(branch=branch)
    if tracked:
        return tracked
    return 'HEAD'


def eval_path(path):
    """handles quoted paths."""
    if path.startswith('"') and path.endswith('"'):
        return core.decode(eval(path))
    else:
        return core.decode(path)


def renamed_files(start, end, git=git):
    difflines = git.diff('%s..%s' % (start, end), M=True,
                         **_common_diff_opts()).splitlines()
    return [eval_path(r[12:].rstrip())
                for r in difflines if r.startswith('rename from ')]


def parse_ls_tree(rev):
    """Return a list of(mode, type, sha1, path) tuples."""
    lines = git.ls_tree(rev, r=True).splitlines()
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


# A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile('^([0-9a-f]{40}) (.*)$')

def parse_rev_list(raw_revs):
    """Parse `git log --pretty=online` output into (SHA-1, summary) pairs."""
    revs = []
    for line in map(core.decode, raw_revs.splitlines()):
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
    for line in map(core.decode, output.splitlines()):
        match = REV_LIST_REGEX.match(line)
        if match:
            revs.append(match.group(1))
            summaries.append(match.group(2))
    return (revs, summaries)


def rev_list_range(start, end):
    """Return a (SHA-1, summary) pairs between start and end."""
    revrange = '%s..%s' % (start, end)
    raw_revs = git.rev_list(revrange, pretty='oneline')
    return parse_rev_list(raw_revs)


def merge_message_path():
    """Return the path to .git/MERGE_MSG or .git/SQUASH_MSG."""
    for basename in ('MERGE_MSG', 'SQUASH_MSG'):
        path = git.git_path(basename)
        if os.path.exists(path):
            return path
    return None


def abort_merge():
    """Abort a merge by reading the tree at HEAD."""
    # Reset the worktree
    git.read_tree('HEAD', reset=True, u=True, v=True)
    # remove MERGE_HEAD
    merge_head = git.git_path('MERGE_HEAD')
    if os.path.exists(merge_head):
        os.unlink(merge_head)
    # remove MERGE_MESSAGE, etc.
    merge_msg_path = merge_message_path()
    while merge_msg_path:
        os.unlink(merge_msg_path)
        merge_msg_path = merge_message_path()


def merge_message(revision):
    """Return a merge message for FETCH_HEAD."""
    fetch_head = git.git_path('FETCH_HEAD')
    if os.path.exists(fetch_head):
        return git.fmt_merge_msg('--file', fetch_head)
    return "Merge branch '%s'" % revision
