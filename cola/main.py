"""Launcher and command line interface to git-cola"""
import argparse
import os
import subprocess
import sys

from cola.app import add_common_arguments
from cola.app import application_init
from cola.app import application_start

# NOTE: these must be imported *after* cola.app.
# PyQt4 may not be available until after cola.app has gotten a chance to
# install the homebrew modules in sys.path.
from cola import cmds
from cola import compat
from cola import core
from cola import utils


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    # we're using argparse with subparser, but argparse
    # does not allow us to assign a default subparser
    # when none has been specified.  We fake it by injecting
    # 'cola' into the command-line so that parse_args()
    # routes them to the 'cola' parser by default.
    if (len(argv) < 1 or
            argv[0].startswith('-') and
            '--help-commands' not in argv):
        argv.insert(0, 'cola')
    elif '--help-commands' in argv:
        argv.append('--help')
    args = parse_args(argv)
    return args.func(args)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(title='valid commands')

    add_cola_command(subparser)
    add_am_command(subparser)
    add_archive_command(subparser)
    add_branch_command(subparser)
    add_browse_command(subparser)
    add_config_command(subparser)
    add_dag_command(subparser)
    add_diff_command(subparser)
    add_fetch_command(subparser)
    add_find_command(subparser)
    add_grep_command(subparser)
    add_merge_command(subparser)
    add_pull_command(subparser)
    add_push_command(subparser)
    add_rebase_command(subparser)
    add_remote_command(subparser)
    add_search_command(subparser)
    add_stash_command(subparser)
    add_tag_command(subparser)
    add_version_command(subparser)

    return parser.parse_args(argv)


def add_command(parent, name, description, func):
    parser = parent.add_parser(str(name), help=description)
    parser.set_defaults(func=func)
    add_common_arguments(parser)
    return parser


def add_cola_command(subparser):
    parser = add_command(subparser, 'cola', 'start git-cola', cmd_cola)
    parser.add_argument('--amend', default=False, action='store_true',
                        help='start in amend mode')
    parser.add_argument('--help-commands', default=False, action='store_true',
                        help='show available sub-commands')
    parser.add_argument('--status-filter', '-s', metavar='<path>',
                        default='', help='status path filter')


def add_am_command(parent):
    parser = add_command(parent, 'am', 'apply patches using "git am"', cmd_am)
    parser.add_argument('patches', metavar='<patches>', nargs='*',
                        help='patches to apply')


def add_archive_command(parent):
    parser = add_command(parent, 'archive', 'save an archive', cmd_archive)
    parser.add_argument('ref', metavar='<ref>', nargs='?', default=None,
                        help='SHA-1 to archive')


def add_branch_command(subparser):
    add_command(subparser, 'branch', 'create a branch', cmd_branch)


def add_browse_command(subparser):
    add_command(subparser, 'browse', 'browse repository', cmd_browse)
    add_command(subparser, 'classic', 'browse repository', cmd_browse)


def add_config_command(subparser):
    add_command(subparser, 'config', 'edit configuration', cmd_config)


def add_dag_command(subparser):
    parser = add_command(subparser, 'dag', 'start git-dag', cmd_dag)
    parser.add_argument('-c', '--count', metavar='<count>',
                        type=int, default=1000,
                        help='number of commits to display')
    parser.add_argument('args', nargs='*', metavar='<args>',
                        help='git log arguments')

def add_diff_command(subparser):
    parser = add_command(subparser, 'diff', 'view diffs', cmd_diff)
    parser.add_argument('args', nargs='*', metavar='<args>',
                        help='git diff arguments')


def add_fetch_command(subparser):
    add_command(subparser, 'fetch', 'fetch remotes', cmd_fetch)


def add_find_command(subparser):
    parser = add_command(subparser, 'find', 'find files', cmd_find)
    parser.add_argument('paths', nargs='*', metavar='<path>',
                        help='filter by path')


def add_grep_command(subparser):
    parser = add_command(subparser, 'grep', 'grep source', cmd_grep)
    parser.add_argument('args', nargs='*', metavar='<args>',
                        help='git grep arguments')

def add_merge_command(subparser):
    add_command(subparser, 'merge', 'merge branches', cmd_merge)


def add_pull_command(subparser):
    parser = add_command(subparser, 'pull', 'pull remote branches', cmd_pull)
    parser.add_argument('--rebase', default=False, action='store_true',
                        help='rebase local branch when pulling')


def add_push_command(subparser):
    add_command(subparser, 'push', 'push remote branches', cmd_push)


def add_rebase_command(subparser):
    parser = add_command(subparser, 'rebase', 'interactive rebase', cmd_rebase)
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='display a diffstat of what changed upstream')
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='be quiet. implies --no-stat')
    parser.add_argument('-i', '--interactive', default=True, action='store_true',
                        help=argparse.SUPPRESS)
    parser.add_argument('--autostash', default=False, action='store_true',
                        help='automatically stash/stash pop before and after')
    parser.add_argument('--fork-point', default=False, action='store_true',
                        help="use 'merge-base --fork-point' to refine upstream")
    parser.add_argument('--onto', default=None, metavar='<newbase>',
                        help='rebase onto given branch instead of upstream')
    parser.add_argument('-p', '--preserve-merges',
                        default=False, action='store_true',
                        help='try to recreate merges instead of ignoring them')
    parser.add_argument('-s', '--strategy', default=None, metavar='<strategy>',
                        help='use the given merge strategy')
    parser.add_argument('--no-ff', default=False, action='store_true',
                        help='cherry-pick all commits, even if unchanged')
    parser.add_argument('-m', '--merge', default=False, action='store_true',
                        help='use merging strategies to rebase')
    parser.add_argument('-x', '--exec', default=None,
                        help='add exec lines after each commit of the editable list')
    parser.add_argument('-k', '--keep-empty', default=False, action='store_true',
                        help='preserve empty commits during rebase')
    parser.add_argument('-f', '--force-rebase', default=False, action='store_true',
                        help='force rebase even if branch is up to date')
    parser.add_argument('-X', '--strategy-option', default=None, metavar='<arg>',
                        help='pass the argument through to the merge strategy')
    parser.add_argument('--stat', default=False, action='store_true',
                        help='display a diffstat of what changed upstream')
    parser.add_argument('-n', '--no-stat', default=False, action='store_true',
                        help='do not show diffstat of what changed upstream')
    parser.add_argument('--verify', default=False, action='store_true',
                        help='allow pre-rebase hook to run')
    parser.add_argument('--rerere-autoupdate',
                        default=False, action='store_true',
                        help='allow rerere to update index with '
                             'resolved conflicts')
    parser.add_argument('--root', default=False, action='store_true',
                        help='rebase all reachable commits up to the root(s)')
    parser.add_argument('--autosquash', default=True, action='store_true',
                        help='move commits that begin with '
                             'squash!/fixup! under -i')
    parser.add_argument('--no-autosquash', default=True, action='store_false',
                        dest='autosquash',
                        help='do not move commits that begin with '
                             'squash!/fixup! under -i')
    parser.add_argument('--committer-date-is-author-date',
                        default=False, action='store_true',
                        help="passed to 'git am' by 'git rebase'")
    parser.add_argument('--ignore-date', default=False, action='store_true',
                        help="passed to 'git am' by 'git rebase'")
    parser.add_argument('--whitespace', default=False, action='store_true',
                        help="passed to 'git apply' by 'git rebase'")
    parser.add_argument('--ignore-whitespace', default=False, action='store_true',
                        help="passed to 'git apply' by 'git rebase'")
    parser.add_argument('-C', dest='context_lines', default=None, metavar='<n>',
                        help="passed to 'git apply' by 'git rebase'")

    actions = parser.add_argument_group('actions')
    actions.add_argument('--continue', default=False, action='store_true',
                        help='continue')
    actions.add_argument('--abort', default=False, action='store_true',
                        help='abort and check out the original branch')
    actions.add_argument('--skip', default=False, action='store_true',
                        help='skip current patch and continue')
    actions.add_argument('--edit-todo', default=False, action='store_true',
                        help='edit the todo list during an interactive rebase')

    parser.add_argument('upstream', nargs='?', default=None, metavar='<upstream>',
                        help='the upstream configured in branch.<name>.remote '
                             'and branch.<name>.merge options will be used '
                             'when <upstream> is omitted; see git-rebase(1) '
                             'for details. If you are currently not on any '
                             'branch or if the current branch does not have '
                             'a configured upstream, the rebase will abort')
    parser.add_argument('branch', nargs='?', default=None, metavar='<branch>',
                        help='git rebase will perform an automatic '
                             '"git checkout <branch>" before doing anything '
                             'else when <branch> is specified')


def add_remote_command(subparser):
    add_command(subparser, 'remote', 'edit remotes', cmd_remote)


def add_search_command(subparser):
    add_command(subparser, 'search', 'search commits', cmd_search)


def add_stash_command(subparser):
    add_command(subparser, 'stash', 'stash and unstash changes', cmd_stash)


def add_tag_command(subparser):
    parser = add_command(subparser, 'tag', 'create tags', cmd_tag)
    parser.add_argument('name', metavar='<name>', nargs='?', default=None,
                        help='tag name')
    parser.add_argument('ref', metavar='<ref>', nargs='?', default=None,
                        help='SHA-1 to tag')
    parser.add_argument('-s', '--sign', default=False, action='store_true',
                        help='annotated and GPG-signed tag')

def add_version_command(subparser):
    parser = add_command(subparser, 'version', 'print the version', cmd_version)
    parser.add_argument('--brief', action='store_true', default=False,
                        help='print the version number only')

# entry points

def cmd_cola(args):
    status_filter = args.status_filter
    if status_filter:
        status_filter = core.abspath(status_filter)

    context = application_init(args)
    from cola.widgets.main import MainView
    view = MainView(context.model, settings=args.settings)
    if args.amend:
        cmds.do(cmds.AmendMode, True)

    if status_filter:
        view.set_filter(core.relpath(status_filter))

    return application_start(context, view)


def cmd_am(args):
    context = application_init(args)
    from cola.widgets.patch import new_apply_patches
    view = new_apply_patches(patches=args.patches)
    return application_start(context, view)


def cmd_archive(args):
    context = application_init(args, update=True)
    if args.ref is None:
        args.ref = context.model.currentbranch

    from cola.widgets.archive import GitArchiveDialog
    view = GitArchiveDialog(args.ref)
    return application_start(context, view)


def cmd_branch(args):
    context = application_init(args, update=True)
    from cola.widgets.createbranch import create_new_branch
    view = create_new_branch()
    return application_start(context, view)


def cmd_browse(args):
    context = application_init(args)
    from cola.widgets.browse import worktree_browser
    view = worktree_browser(update=False)
    return application_start(context, view)


def cmd_config(args):
    context = application_init(args)
    from cola.widgets.prefs import preferences
    view = preferences()
    return application_start(context, view)


def cmd_dag(args):
    context = application_init(args)
    from cola.widgets.dag import git_dag
    view = git_dag(context.model, args=args, settings=args.settings)
    return application_start(context, view)


def cmd_diff(args):
    context = application_init(args)
    from cola.difftool import diff_expression
    expr = subprocess.list2cmdline(map(core.decode, args.args))
    view = diff_expression(None, expr, create_widget=True)
    return application_start(context, view)


def cmd_fetch(args):
    # TODO: the calls to update_status() can be done asynchronously
    # by hooking into the message_updated notification.
    context = application_init(args)
    from cola.widgets import remote
    context.model.update_status()
    view = remote.fetch()
    return application_start(context, view)


def cmd_find(args):
    context = application_init(args)
    from cola.widgets import finder
    paths = subprocess.list2cmdline(map(core.decode, args.paths))
    view = finder.finder(paths=paths)
    return application_start(context, view)


def cmd_grep(args):
    context = application_init(args)
    from cola.widgets import grep
    text = subprocess.list2cmdline(map(core.decode, args.args))
    view = grep.new_grep(text=text, parent=None)
    return application_start(context, view)


def cmd_merge(args):
    context = application_init(args, update=True)
    from cola.widgets.merge import MergeView
    view = MergeView(context.cfg, context.model, parent=None)
    return application_start(context, view)


def cmd_version(args):
    from cola import version
    version.print_version(brief=args.brief)
    return 0


def cmd_pull(args):
    context = application_init(args, update=True)
    from cola.widgets import remote
    view = remote.pull()
    if args.rebase:
        view.set_rebase(True)
    return application_start(context, view)


def cmd_push(args):
    context = application_init(args, update=True)
    from cola.widgets import remote
    view = remote.push()
    return application_start(context, view)


def cmd_rebase(args):
    kwargs = {
            'verbose': args.verbose,
            'quiet': args.quiet,
            'autostash': args.autostash,
            'fork_point': args.fork_point,
            'onto': args.onto,
            'preserve_merges': args.preserve_merges,
            'strategy': args.strategy,
            'no_ff': args.no_ff,
            'merge': args.merge,
            'exec': getattr(args, 'exec', None), # python keyword
            'keep_empty': args.keep_empty,
            'force_rebase': args.force_rebase,
            'strategy_option': args.strategy_option,
            'stat': args.stat,
            'no_stat': args.no_stat,
            'verify': args.verify,
            'rerere_autoupdate': args.rerere_autoupdate,
            'root': args.root,
            'autosquash': args.autosquash,
            'committer_date_is_author_date': args.committer_date_is_author_date,
            'ignore_date': args.ignore_date,
            'whitespace': args.whitespace,
            'ignore_whitespace': args.ignore_whitespace,
            'C': args.context_lines,
            'continue': getattr(args, 'continue', False), # python keyword
            'abort': args.abort,
            'skip': args.skip,
            'edit_todo': args.edit_todo,
            'upstream': args.upstream,
            'branch': args.branch,
            'capture_output': False,
    }
    status, out, err = cmds.do(cmds.Rebase, **kwargs)
    if out:
        core.stdout(out)
    if err:
        core.stderr(err)
    return status


def cmd_remote(args):
    context = application_init(args)
    from cola.widgets import editremotes
    view = editremotes.new_remote_editor()
    return application_start(context, view)


def cmd_search(args):
    context = application_init(args)
    from cola.widgets.search import search
    view = search()
    return application_start(context, view)


def cmd_stash(args):
    context = application_init(args)
    from cola.widgets.stash import stash
    view = stash()
    return application_start(context, view)


def cmd_tag(args):
    context = application_init(args)
    from cola.widgets.createtag import new_create_tag
    view = new_create_tag(name=args.name, ref=args.ref, sign=args.sign)
    return application_start(context, view)


# Windows shortcut launch features:

def find_git():
    """Return the path of git.exe, or None if we can't find it."""
    if not utils.is_win32():
        return None  # UNIX systems have git in their $PATH

    # If the user wants to use a Git/bin/ directory from a non-standard
    # directory then they can write its location into
    # ~/.config/git-cola/git-bindir
    git_bindir = os.path.expanduser(os.path.join('~', '.config', 'git-cola',
                                                 'git-bindir'))
    if core.exists(git_bindir):
        custom_path = core.read(git_bindir).strip()
        if custom_path and core.exists(custom_path):
            return custom_path

    # Try to find Git's bin/ directory in one of the typical locations
    pf = os.environ.get('ProgramFiles', 'C:\\Program Files')
    pf32 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
    for p in [pf32, pf, 'C:\\']:
        candidate = os.path.join(p, 'Git\\bin')
        if os.path.isdir(candidate):
            return candidate

    return None


def shortcut_launch():
    """Launch from a shortcut

    Prompt for the repository by default, and try to find git.
    """
    argv = ['cola', '--prompt']
    git_path = find_git()
    if git_path:
        prepend_path(git_path)

    return main(argv)


def prepend_path(path):
    # Adds git to the PATH.  This is needed on Windows.
    path = core.decode(path)
    path_entries = core.getenv('PATH', '').split(os.pathsep)
    if path not in path_entries:
        path_entries.insert(0, path)
        compat.setenv('PATH', os.pathsep.join(path_entries))
