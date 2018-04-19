"""Git commands and queries for Git"""
from __future__ import division, absolute_import, unicode_literals
import json
import os
import re
from io import StringIO

from . import core
from . import gitcfg
from . import utils
from . import version
from .git import git
from .git import STDOUT
from .i18n import N_
from .interaction import Interaction


# Object ID / SHA1-related constants
MISSING_BLOB_OID = '0000000000000000000000000000000000000000'
EMPTY_TREE_OID = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
OID_LENGTH = 40


class InvalidRepositoryError(Exception):
    pass


def add(items, u=False):
    """Run "git add" while preventing argument overflow"""
    add = git.add
    return utils.slice_fn(
        items, lambda paths: add('--', force=True, verbose=True, u=u, *paths))


def apply_diff(filename):
    return git.apply(filename, index=True, cached=True)


def apply_diff_to_worktree(filename):
    return git.apply(filename)


def get_branch(branch):
    if branch is None:
        branch = current_branch()
    return branch


def get_config(config):
    if config is None:
        config = gitcfg.current()
    return config



def upstream_remote(branch=None, config=None):
    """Return the remote associated with the specified branch"""
    config = get_config(config)
    branch = get_branch(branch)
    return config.get('branch.%s.remote' % branch)


def remote_url(remote, push=False, config=None):
    """Return the URL for the specified remote"""
    config = get_config(config)
    url = config.get('remote.%s.url' % remote, '')
    if push:
        url = config.get('remote.%s.pushurl' % remote, url)
    return url


def diff_index_filenames(ref):
    """Return a of filenames that have been modified relative to the index"""
    out = git.diff_index(ref, name_only=True, z=True)[STDOUT]
    return _parse_diff_filenames(out)


def diff_filenames(*args):
    """Return a list of filenames that have been modified"""
    out = git.diff_tree(name_only=True, no_commit_id=True, r=True, z=True,
                        _readonly=True, *args)[STDOUT]
    return _parse_diff_filenames(out)


def listdir(dirname):
    """Get the contents of a directory

    Scan the filesystem while categorizing directories and files.

    """
    dirs = []
    files = []

    for relpath in os.listdir(dirname):
        if relpath == '.git':
            continue
        if dirname == './':
            path = relpath
        else:
            path = dirname + relpath

        if os.path.isdir(path):
            dirs.append(path)
        else:
            files.append(path)

    dirs.sort()
    files.sort()

    return (dirs, files)


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


class _current_branch(object):
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
    # Common .git/HEAD "ref: refs/heads/master" files
    islink = core.islink(head)
    if core.isfile(head) and not islink:
        data = core.read(head).rstrip()
        ref_prefix = 'ref: '
        if data.startswith(ref_prefix):
            return data[len(ref_prefix):]
        # Detached head
        return data
    # Legacy .git/HEAD symlinks
    elif islink:
        refs_heads = core.realpath(git.git_path('refs', 'heads'))
        path = core.abspath(head).replace('\\', '/')
        if path.startswith(refs_heads + '/'):
            return path[len(refs_heads)+1:]

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


def _version_sort():
    if version.check_git('version-sort'):
        sort = 'version:refname'
    else:
        sort = False
    return sort


def for_each_ref_basename(refs, git=git):
    """Return refs starting with 'refs'."""
    sort = _version_sort()
    status, out, err = git.for_each_ref(refs, format='%(refname)',
                                        sort=sort, _readonly=True)
    output = out.splitlines()
    non_heads = [x for x in output if not x.endswith('/HEAD')]
    return list(map(lambda x: x[len(refs) + 1:], non_heads))


def _triple(x, y):
    return (x, len(x) + 1, y)


def all_refs(split=False, git=git):
    """Return a tuple of (local branches, remote branches, tags)."""
    local_branches = []
    remote_branches = []
    tags = []
    triple = _triple
    query = (triple('refs/tags', tags),
             triple('refs/heads', local_branches),
             triple('refs/remotes', remote_branches))
    sort = _version_sort()
    status, out, err = git.for_each_ref(format='%(refname)',
                                        sort=sort, _readonly=True)
    for ref in out.splitlines():
        for prefix, prefix_len, dst in query:
            if ref.startswith(prefix) and not ref.endswith('/HEAD'):
                dst.append(ref[prefix_len:])
                continue
    tags.reverse()
    if split:
        return local_branches, remote_branches, tags
    else:
        return local_branches + remote_branches + tags


def tracked_branch(branch=None, config=None):
    """Return the remote branch associated with 'branch'."""
    config = get_config(config)
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


def untracked_files(git=git, paths=None, **kwargs):
    """Returns a sorted list of untracked files."""

    if paths is None:
        paths = []
    args = ['--'] + paths
    out = git.ls_files(z=True, others=True, exclude_standard=True,
                       *args, **kwargs)[STDOUT]
    if out:
        return out[:-1].split('\0')
    return []


def tag_list():
    """Return a list of tags."""
    result = for_each_ref_basename('refs/tags')
    result.reverse()
    return result


def log(git, *args, **kwargs):
    return git.log(no_color=True, no_abbrev_commit=True,
                   no_ext_diff=True, _readonly=True, *args, **kwargs)[STDOUT]


def commit_diff(oid, git=git):
    return log(git, '-1', oid, '--') + '\n\n' + oid_diff(git, oid)


_diff_overrides = {}


def update_diff_overrides(space_at_eol, space_change,
                          all_space, function_context):
    _diff_overrides['ignore_space_at_eol'] = space_at_eol
    _diff_overrides['ignore_space_change'] = space_change
    _diff_overrides['ignore_all_space'] = all_space
    _diff_overrides['function_context'] = function_context


def common_diff_opts(config=None):
    config = get_config(config)
    # Default to --patience when diff.algorithm is unset
    patience = not config.get('diff.algorithm', default='')
    submodule = version.check('diff-submodule', version.git_version())
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


def oid_diff(git, oid, filename=None):
    """Return the diff for an oid"""
    # Naively "$oid^!" is what we'd like to use but that doesn't
    # give the correct result for merges--the diff is reversed.
    # Be explicit and compare oid against its first parent.
    args = [oid + '~', oid]
    opts = common_diff_opts()
    _add_filename(args, filename)
    status, out, err = git.diff(*args, **opts)
    if status != 0:
        # We probably don't have "$oid~" because this is the root commit.
        # "git show" is clever enough to handle the root commit.
        args = [oid + '^!']
        _add_filename(args, filename)
        status, out, err = git.show(pretty='format:', _readonly=True,
                                    *args, **opts)
        out = out.lstrip()
    return out


def diff_info(oid, git=git, filename=None):
    decoded = log(git, '-1', oid, '--', pretty='format:%b').strip()
    if decoded:
        decoded += '\n\n'
    return decoded + oid_diff(git, oid, filename=filename)


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

    result = extract_diff_header(status, deleted,
                                 with_diff_header, suppress_header, out)
    return core.UStr(result, out.encoding)


def extract_diff_header(status, deleted,
                        with_diff_header, suppress_header, diffoutput):
    """Split a diff into a header section and payload section"""

    if diffoutput.startswith('Submodule'):
        if with_diff_header:
            return ('', diffoutput)
        else:
            return diffoutput

    start = False
    del_tag = 'deleted file mode '

    output = StringIO()
    headers = StringIO()

    for line in diffoutput.split('\n'):
        if not start and '@@' == line[:2] and '@@' in line[2:]:
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
    else:
        return output_text


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
        try:
            master_idx = revs[cur_master_idx:].index(rev)
            master_idx += cur_master_idx
        except ValueError:
            master_idx = revs.index(rev)

        if master_idx == cur_master_idx + 1:
            patches_to_export[patchset_idx].append(rev)
            cur_master_idx += 1
            continue
        else:
            patches_to_export.append([rev])
            cur_master_idx = master_idx
            patchset_idx += 1

    # Export each patchsets
    status = 0
    for patchset in patches_to_export:
        stat, out, err = export_patchset(patchset[0],
                                         patchset[-1],
                                         output=output,
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


def reset_paths(items):
    """Run "git reset" while preventing argument overflow"""
    reset = git.reset
    status, out, err = utils.slice_fn(items, lambda paths: reset('--', *paths))
    return (status, out, err)


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
        args[0] = EMPTY_TREE_OID
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
    return git.merge_base(head, ref, _readonly=True)[STDOUT]


def merge_base_parent(branch):
    tracked = tracked_branch(branch=branch)
    if tracked:
        return tracked
    return 'HEAD'


def parse_ls_tree(rev):
    """Return a list of (mode, type, oid, path) tuples."""
    output = []
    lines = git.ls_tree(rev, r=True, _readonly=True)[STDOUT].splitlines()
    regex = re.compile(r'^(\d+)\W(\w+)\W(\w+)[ \t]+(.*)$')
    for line in lines:
        match = regex.match(line)
        if match:
            mode = match.group(1)
            objtype = match.group(2)
            oid = match.group(3)
            filename = match.group(4)
            output.append((mode, objtype, oid, filename,))
    return output


def ls_tree(path, ref='HEAD'):
    """Return a parsed git ls-tree result for a single directory"""

    result = []
    status, out, err = git.ls_tree(ref, '--', path, z=True, full_tree=True)
    if status == 0 and out:
        for line in out[:-1].split('\0'):
            # .....6 ...4 ......................................40
            # 040000 tree c127cde9a0c644a3a8fef449a244f47d5272dfa6	relative
            # 100644 blob 139e42bf4acaa4927ec9be1ec55a252b97d3f1e2	relative/path
            # 0..... 7... 12......................................	53
            # path offset = 6 + 1 + 4 + 1 + 40 + 1 = 53
            objtype = line[7:11]
            relpath = line[53:]
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
            revs.append((rev_id, summary,))
    return revs


def log_helper(all=False, extra_args=None):
    """Return parallel arrays containing oids and summaries."""
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
    """Return (oid, summary) pairs between start and end."""
    revrange = '%s..%s' % (start, end)
    out = git.rev_list(revrange, pretty='oneline')[STDOUT]
    return parse_rev_list(out)


def commit_message_path():
    """Return the path to .git/GIT_COLA_MSG"""
    path = git.git_path('GIT_COLA_MSG')
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


def prepare_commit_message_hook(config=None):
    default_hook = git.git_path('hooks', 'cola-prepare-commit-msg')
    config = get_config(config)
    return config.get('cola.preparecommitmessagehook', default=default_hook)


def abort_merge():
    """Abort a merge by reading the tree at HEAD."""
    # Reset the worktree
    status, out, err = git.read_tree('HEAD', reset=True, u=True, v=True)
    # remove MERGE_HEAD
    merge_head = git.git_path('MERGE_HEAD')
    if core.exists(merge_head):
        core.unlink(merge_head)
    # remove MERGE_MESSAGE, etc.
    merge_msg_path = merge_message_path()
    while merge_msg_path:
        core.unlink(merge_msg_path)
        merge_msg_path = merge_message_path()
    return status, out, err


def strip_remote(remotes, remote_branch):
    for remote in remotes:
        prefix = remote + '/'
        if remote_branch.startswith(prefix):
            return remote_branch[len(prefix):]
    return remote_branch.split('/', 1)[-1]


def parse_refs(argv):
    """Parse command-line arguments into object IDs"""
    status, out, err = git.rev_parse(*argv)
    if status == 0:
        oids = [oid for oid in out.splitlines() if oid]
    else:
        oids = argv
    return oids


def prev_commitmsg(*args):
    """Queries git for the latest commit message."""
    return git.log('-1', no_color=True, pretty='format:%s%n%n%b',
                   *args)[STDOUT]


def rev_parse(name):
    """Call git rev-parse and return the output"""
    status, out, err = git.rev_parse(name)
    if status == 0:
        result = out.strip()
    else:
        result = name
    return result


def write_blob(oid, filename):
    """Write a blob to a temporary file and return the path

    Modern versions of Git allow invoking filters.  Older versions
    get the object content as-is.

    """
    if version.check_git('cat-file-filters-path'):
        return cat_file_to_path(filename, oid)
    else:
        return cat_file_blob(filename, oid)


def cat_file_blob(filename, oid):
    return cat_file(filename, 'blob', oid)


def cat_file_to_path(filename, oid):
    return cat_file(filename, oid, path=filename, filters=True)


def cat_file(filename, *args, **kwargs):
    """Redirect git cat-file output to a path"""
    result = None
    # Use the original filename in the suffix so that the generated filename
    # has the correct extension, and so that it resembles the original name.
    basename = os.path.basename(filename)
    suffix = '-' + basename  # ensures the correct filename extension
    path = utils.tmp_filename('blob', suffix=suffix)
    with open(path, 'wb') as fp:
        status, out, err = git.cat_file(
            _raw=True, _readonly=True, _stdout=fp, *args, **kwargs)
        Interaction.command(
            N_('Error'), 'git cat-file', status, out, err)
        if status == 0:
            result = path
    if not result:
        core.unlink(path)
    return result


def write_blob_path(head, oid, filename):
    """Use write_blob() when modern git is available"""
    if version.check_git('cat-file-filters-path'):
        return write_blob(oid, filename)
    else:
        return cat_file_blob(filename, head + ':' + filename)


def annex_path(head, filename, config=None):
    """Return the git-annex path for a filename at the specified commit"""
    config = get_config(config)
    path = None
    annex_info = {}

    # unfortunately there's no way to filter this down to a single path
    # so we just have to scan all reported paths
    status, out, err = git.annex('findref', '--json', head)
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
        status, out, err = git.annex('contentlocation', key)
        if status == 0 and os.path.exists(out):
            path = out

    return path
