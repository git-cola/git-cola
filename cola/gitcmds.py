"""Provides commands and queries for Git."""
import os
import re
from cStringIO import StringIO

from cola import core
from cola import git
from cola import gitcfg
from cola import errors
from cola import utils
from cola import version
from cola.compat import set
from cola.decorators import memoize

git = git.instance()
config = gitcfg.instance()

class InvalidRepositoryError(StandardError):
    pass


def default_remote():
    """Return the remote tracked by the current branch."""
    return config.get('branch.%s.remote' % current_branch())


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
    """Cache for current_branch()"""
    key = None
    value = None

def current_branch():
    """Return the current branch"""
    head = git.git_path('HEAD')
    try:
        key = os.stat(head).st_mtime
        if _current_branch.key == key:
            return _current_branch.value
    except OSError, e:
        pass
    data = git.rev_parse('HEAD', with_stderr=True, symbolic_full_name=True)
    if data.startswith('fatal:'):
        # git init -- read .git/HEAD.  We could do this unconditionally
        # and avoid the subprocess call.  It's probably time to start
        # using dulwich.
        data = _read_git_head(head)

    for refs_prefix in ('refs/heads/', 'refs/remotes/'):
        if data.startswith(refs_prefix):
            value = data[len(refs_prefix):]
            _current_branch.key = key
            _current_branch.value = value
            return value
    # Detached head
    return data


def _read_git_head(head, default='master'):
    """Pure-python .git/HEAD reader"""
    # Legacy .git/HEAD symlinks
    if os.path.islink(head):
        refs_heads = os.path.realpath(git.git_path('refs', 'heads'))
        path = os.path.abspath(head).replace('\\', '/')
        if path.startswith(refs_heads + '/'):
            return path[len(refs_heads)+1:]

    # Common .git/HEAD "ref: refs/heads/master" file
    elif os.path.isfile(head):
        data = utils.slurp(head).rstrip()
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


def for_each_ref_basename(refs):
    """Return refs starting with 'refs'."""
    output = git.for_each_ref(refs, format='%(refname)').splitlines()
    non_heads = filter(lambda x: not x.endswith('/HEAD'), output)
    return map(lambda x: x[len(refs) + 1:], non_heads)


def all_refs(split=False):
    """Return a tuple of (local branches, remote branches, tags)."""
    local_branches = []
    remote_branches = []
    tags = []
    triple = lambda x, y: (x, len(x) + 1, y)
    query = (triple('refs/tags', tags),
             triple('refs/heads', local_branches),
             triple('refs/remotes', remote_branches))
    for ref in git.for_each_ref(format='%(refname)').splitlines():
        for prefix, prefix_len, dst in query:
            if ref.startswith(prefix) and not ref.endswith('/HEAD'):
                dst.append(ref[prefix_len:])
                continue
    if split:
        return local_branches, remote_branches, tags
    else:
        return local_branches + remote_branches + tags


def tracked_branch(branch=None):
    """Return the remote branch associated with 'branch'."""
    if branch is None:
        branch = current_branch()
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


def untracked_files():
    """Returns a sorted list of untracked files."""
    ls_files = git.ls_files(z=True,
                            others=True,
                            exclude_standard=True)
    return [core.decode(f) for f in ls_files.split('\0') if f]


def tag_list():
    """Return a list of tags."""
    tags = for_each_ref_basename('refs/tags')
    tags.reverse()
    return tags


def commit_diff(sha1):
    commit = git.show(sha1)
    first_newline = commit.index('\n')
    if commit[first_newline+1:].startswith('Merge:'):
        return (core.decode(commit) + '\n\n' +
                core.decode(diff_helper(commit=sha1,
                                             cached=False,
                                             suppress_header=False)))
    else:
        return core.decode(commit)


@memoize
def _common_diff_opts():
    patience = version.check('patience', version.git_version())
    submodule = version.check('diff-submodule', version.git_version())
    return {
        'patience': patience,
        'submodule': submodule,
        'no_color': True,
        'with_raw_output': True,
        'with_stderr': True,
    }


def sha1_diff(sha1):
    opts = _common_diff_opts()
    return git.diff(sha1 + '^!',
                    unified=config.get('diff.context', 3),
                    **opts)


def diff_info(sha1):
    log = git.log('-1',
                  '--format=Author:\t%aN <%aE>%n'
                  'Date:\t%aD%n%n'
                  '%s%n%n%b',
                  sha1)
    return log + '\n\n' + sha1_diff(sha1)


def diff_helper(commit=None,
                branch=None,
                ref=None,
                endref=None,
                filename=None,
                cached=True,
                with_diff_header=False,
                suppress_header=True,
                reverse=False):
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

    # The '--patience' option did not appear until git 1.6.2
    # so don't allow it to be used on version previous to that
    patience = version.check('patience', version.git_version())
    submodule = version.check('diff-submodule', version.git_version())

    diffoutput = git.diff(R=reverse,
                          M=True,
                          no_color=True,
                          cached=cached,
                          unified=config.get('diff.context', 3),
                          with_raw_output=True,
                          with_stderr=True,
                          patience=patience,
                          submodule=submodule,
                          *argv)
    # Handle 'git init'
    if diffoutput.startswith('fatal:'):
        if with_diff_header:
            return ('', '')
        else:
            return ''

    if diffoutput.startswith('Submodule'):
        if with_diff_header:
            return ('', diffoutput)
        else:
            return diffoutput

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


def unstage_paths(args):
    status, output = git.reset('--', with_stderr=True, with_status=True,
                               *set(args))
    if status != 128:
        return (status, output)
    # handle git init: we have to use 'git rm --cached'
    # detect this condition by checking if the file is still staged
    status, output = git.update_index('--',
                                      force_remove=True,
                                      with_status=True,
                                      with_stderr=True,
                                      *set(args))
    return (status, output)



def worktree_state(head='HEAD', staged_only=False):
    """Return a tuple of files in various states of being

    Can be staged, unstaged, untracked, unmerged, or changed
    upstream.

    """
    state = worktree_state_dict(head=head, staged_only=staged_only)
    return(state.get('staged', []),
           state.get('modified', []),
           state.get('unmerged', []),
           state.get('untracked', []),
           state.get('upstream_changed', []))


def worktree_state_dict(head='HEAD', staged_only=False):
    """Return a dict of files in various states of being

    :rtype: dict, keys are staged, unstaged, untracked, unmerged,
            changed_upstream, and submodule.

    """
    git.update_index(refresh=True)

    if staged_only:
        return _branch_status(head)

    staged_set = set()
    modified_set = set()

    staged = []
    modified = []
    unmerged = []
    untracked = []
    upstream_changed = []
    submodules = set()
    try:
        output = git.diff_index(head, cached=True, with_stderr=True)
        if output.startswith('fatal:'):
            raise errors.GitInitError('git init')
        for line in output.splitlines():
            rest, name = line.split('\t', 1)
            status = rest[-1]
            name = eval_path(name)
            if '160000' in rest[1:14]:
                submodules.add(name)
            if status  == 'M':
                staged.append(name)
                staged_set.add(name)
                # This file will also show up as 'M' without --cached
                # so by default don't consider it modified unless
                # it's truly modified
                modified_set.add(name)
                if not staged_only and is_modified(name):
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

    except errors.GitInitError:
        # handle git init
        staged.extend(all_files())

    try:
        output = git.diff_index(head, with_stderr=True)
        if output.startswith('fatal:'):
            raise errors.GitInitError('git init')
        for line in output.splitlines():
            rest , name = line.split('\t', 1)
            status = rest[-1]
            name = eval_path(name)
            if '160000' in rest[1:13]:
                submodules.add(name)
            if status == 'M' or status == 'D':
                if name not in modified_set:
                    modified.append(name)
            elif status == 'A':
                # newly-added yet modified
                if (name not in modified_set and not staged_only and
                        is_modified(name)):
                    modified.append(name)

    except errors.GitInitError:
        # handle git init
        ls_files = git.ls_files(modified=True, z=True)[:-1].split('\0')
        modified.extend(map(core.decode, [f for f in ls_files if f]))

    untracked.extend(untracked_files())

    # Look for upstream modified files if this is a tracking branch
    tracked = tracked_branch()
    if tracked:
        try:
            diff_expr = merge_base_to(tracked)
            output = git.diff(diff_expr, name_only=True, z=True)

            if output.startswith('fatal:'):
                raise errors.GitInitError('git init')

            for name in [n for n in output.split('\0') if n]:
                name = core.decode(name)
                upstream_changed.append(name)

        except errors.GitInitError:
            # handle git init
            pass

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


def _branch_status(branch):
    """
    Returns a tuple of staged, unstaged, untracked, and unmerged files

    This shows only the changes that were introduced in branch

    """
    status, output = git.diff(name_only=True,
                              M=True, z=True,
                              with_stderr=True,
                              with_status=True,
                              *branch.strip().split())
    if status != 0:
        return {}

    staged = map(core.decode, [n for n in output.split('\0') if n])
    return {'staged': staged,
            'upstream_changed': staged}


def merge_base_to(ref):
    """Given `ref`, return $(git merge-base ref HEAD)..ref."""
    base = git.merge_base('HEAD', ref)
    return '%s..%s' % (base, ref)


def merge_base_parent(branch):
    tracked = tracked_branch(branch=branch)
    if tracked:
        return '%s..%s' % (tracked, branch)
    return 'master..%s' % branch


def is_modified(name):
    status, out = git.diff('--', name,
                           name_only=True,
                           exit_code=True,
                           with_status=True)
    return status != 0


def eval_path(path):
    """handles quoted paths."""
    if path.startswith('"') and path.endswith('"'):
        return core.decode(eval(path))
    else:
        return path


def renamed_files(start, end):
    difflines = git.diff('%s..%s' % (start, end),
                         no_color=True,
                         M=True).splitlines()
    return [eval_path(r[12:].rstrip())
                for r in difflines if r.startswith('rename from ')]


def changed_files(start, end):
    zfiles_str = git.diff('%s..%s' % (start, end),
                          name_only=True, z=True).strip('\0')
    return [core.decode(enc) for enc in zfiles_str.split('\0') if enc]


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
    output = git.log(pretty='oneline', no_color=True, all=all, *args)
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
