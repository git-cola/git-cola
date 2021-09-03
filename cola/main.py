"""Launcher and command line interface to git-cola"""
from __future__ import absolute_import, division, print_function, unicode_literals
import argparse
import sys

from . import app
from . import cmds
from . import compat
from . import core


def main(argv=None):
    app.initialize()
    if argv is None:
        argv = sys.argv[1:]
    # we're using argparse with subparser, but argparse
    # does not allow us to assign a default subparser
    # when none has been specified.  We fake it by injecting
    # 'cola' into the command-line so that parse_args()
    # routes them to the 'cola' parser by default.
    help_commands = core.encode('--help-commands')
    args = [core.encode(arg) for arg in argv]
    if not argv or argv[0].startswith('-') and help_commands not in args:
        argv.insert(0, 'cola')
    elif help_commands in argv:
        argv.append('--help')
    args = parse_args(argv)
    return args.func(args)


def winmain():
    return app.winmain(main)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    # Newer versions of argparse (Python 3.6+) emit an error message for
    # "--help-commands" unless we register the flag on the main parser.
    if compat.PY_VERSION >= (3, 6):
        add_help_options(parser)
        parser.set_defaults(func=lambda _: parser.print_help())

    subparser = parser.add_subparsers(title='valid commands')
    add_cola_command(subparser)
    add_about_command(subparser)
    add_am_command(subparser)
    add_archive_command(subparser)
    add_branch_command(subparser)
    add_browse_command(subparser)
    add_clone_command(subparser)
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
    add_recent_command(subparser)
    add_remote_command(subparser)
    add_search_command(subparser)
    add_stash_command(subparser)
    add_tag_command(subparser)
    add_version_command(subparser)

    return parser.parse_args(argv)


def add_help_options(parser):
    """Add the --help-commands flag to the parser"""
    parser.add_argument(
        '--help-commands',
        default=False,
        action='store_true',
        help='show available sub-commands',
    )


def add_command(parent, name, description, func):
    parser = parent.add_parser(str(name), help=description)
    parser.set_defaults(func=func)
    app.add_common_arguments(parser)
    return parser


def add_cola_command(subparser):
    parser = add_command(subparser, 'cola', 'start git-cola', cmd_cola)
    parser.add_argument(
        '--amend', default=False, action='store_true', help='start in amend mode'
    )
    add_help_options(parser)
    parser.add_argument(
        '--status-filter', '-s', metavar='<path>', default='', help='status path filter'
    )


def add_about_command(parent):
    add_command(parent, 'about', 'about git-cola', cmd_about)


def add_am_command(parent):
    parser = add_command(parent, 'am', 'apply patches using "git am"', cmd_am)
    parser.add_argument(
        'patches', metavar='<patches>', nargs='*', help='patches to apply'
    )


def add_archive_command(parent):
    parser = add_command(parent, 'archive', 'save an archive', cmd_archive)
    parser.add_argument(
        'ref', metavar='<ref>', nargs='?', default=None, help='commit to archive'
    )


def add_branch_command(subparser):
    add_command(subparser, 'branch', 'create a branch', cmd_branch)


def add_browse_command(subparser):
    add_command(subparser, 'browse', 'browse repository', cmd_browse)


def add_clone_command(subparser):
    add_command(subparser, 'clone', 'clone repository', cmd_clone)


def add_config_command(subparser):
    add_command(subparser, 'config', 'edit configuration', cmd_config)


def add_dag_command(subparser):
    parser = add_command(subparser, 'dag', 'start git-dag', cmd_dag)
    parser.add_argument(
        '-c',
        '--count',
        metavar='<count>',
        type=int,
        default=1000,
        help='number of commits to display',
    )
    parser.add_argument(
        '--all',
        action='store_true',
        dest='show_all',
        help='visualize all branches',
        default=False,
    )
    parser.add_argument('args', nargs='*', metavar='<args>', help='git log arguments')


def add_diff_command(subparser):
    parser = add_command(subparser, 'diff', 'view diffs', cmd_diff)
    parser.add_argument('args', nargs='*', metavar='<args>', help='git diff arguments')


def add_fetch_command(subparser):
    add_command(subparser, 'fetch', 'fetch remotes', cmd_fetch)


def add_find_command(subparser):
    parser = add_command(subparser, 'find', 'find files', cmd_find)
    parser.add_argument('paths', nargs='*', metavar='<path>', help='filter by path')


def add_grep_command(subparser):
    parser = add_command(subparser, 'grep', 'grep source', cmd_grep)
    parser.add_argument('args', nargs='*', metavar='<args>', help='git grep arguments')


def add_merge_command(subparser):
    parser = add_command(subparser, 'merge', 'merge branches', cmd_merge)
    parser.add_argument(
        'ref', nargs='?', metavar='<ref>', help='branch, tag, or commit to merge'
    )


def add_pull_command(subparser):
    parser = add_command(subparser, 'pull', 'pull remote branches', cmd_pull)
    parser.add_argument(
        '--rebase',
        default=False,
        action='store_true',
        help='rebase local branch when pulling',
    )


def add_push_command(subparser):
    add_command(subparser, 'push', 'push remote branches', cmd_push)


def add_rebase_command(subparser):
    parser = add_command(subparser, 'rebase', 'interactive rebase', cmd_rebase)
    parser.add_argument(
        '-v',
        '--verbose',
        default=False,
        action='store_true',
        help='display a diffstat of what changed upstream',
    )
    parser.add_argument(
        '-q',
        '--quiet',
        default=False,
        action='store_true',
        help='be quiet. implies --no-stat',
    )
    parser.add_argument(
        '-i', '--interactive', default=True, action='store_true', help=argparse.SUPPRESS
    )
    parser.add_argument(
        '--autostash',
        default=False,
        action='store_true',
        help='automatically stash/stash pop before and after',
    )
    parser.add_argument(
        '--fork-point',
        default=False,
        action='store_true',
        help="use 'merge-base --fork-point' to refine upstream",
    )
    parser.add_argument(
        '--onto',
        default=None,
        metavar='<newbase>',
        help='rebase onto given branch instead of upstream',
    )
    parser.add_argument(
        '-p',
        '--preserve-merges',
        default=False,
        action='store_true',
        help='try to recreate merges instead of ignoring them',
    )
    parser.add_argument(
        '-s',
        '--strategy',
        default=None,
        metavar='<strategy>',
        help='use the given merge strategy',
    )
    parser.add_argument(
        '--no-ff',
        default=False,
        action='store_true',
        help='cherry-pick all commits, even if unchanged',
    )
    parser.add_argument(
        '-m',
        '--merge',
        default=False,
        action='store_true',
        help='use merging strategies to rebase',
    )
    parser.add_argument(
        '-x',
        '--exec',
        default=None,
        help='add exec lines after each commit of ' 'the editable list',
    )
    parser.add_argument(
        '-k',
        '--keep-empty',
        default=False,
        action='store_true',
        help='preserve empty commits during rebase',
    )
    parser.add_argument(
        '-f',
        '--force-rebase',
        default=False,
        action='store_true',
        help='force rebase even if branch is up to date',
    )
    parser.add_argument(
        '-X',
        '--strategy-option',
        default=None,
        metavar='<arg>',
        help='pass the argument through to the merge strategy',
    )
    parser.add_argument(
        '--stat',
        default=False,
        action='store_true',
        help='display a diffstat of what changed upstream',
    )
    parser.add_argument(
        '-n',
        '--no-stat',
        default=False,
        action='store_true',
        help='do not show diffstat of what changed upstream',
    )
    parser.add_argument(
        '--verify',
        default=False,
        action='store_true',
        help='allow pre-rebase hook to run',
    )
    parser.add_argument(
        '--rerere-autoupdate',
        default=False,
        action='store_true',
        help='allow rerere to update index with ' 'resolved conflicts',
    )
    parser.add_argument(
        '--root',
        default=False,
        action='store_true',
        help='rebase all reachable commits up to the root(s)',
    )
    parser.add_argument(
        '--autosquash',
        default=True,
        action='store_true',
        help='move commits that begin with ' 'squash!/fixup! under -i',
    )
    parser.add_argument(
        '--no-autosquash',
        default=True,
        action='store_false',
        dest='autosquash',
        help='do not move commits that begin with ' 'squash!/fixup! under -i',
    )
    parser.add_argument(
        '--committer-date-is-author-date',
        default=False,
        action='store_true',
        help="passed to 'git am' by 'git rebase'",
    )
    parser.add_argument(
        '--ignore-date',
        default=False,
        action='store_true',
        help="passed to 'git am' by 'git rebase'",
    )
    parser.add_argument(
        '--whitespace',
        default=False,
        action='store_true',
        help="passed to 'git apply' by 'git rebase'",
    )
    parser.add_argument(
        '--ignore-whitespace',
        default=False,
        action='store_true',
        help="passed to 'git apply' by 'git rebase'",
    )
    parser.add_argument(
        '-C',
        dest='context_lines',
        default=None,
        metavar='<n>',
        help="passed to 'git apply' by 'git rebase'",
    )

    actions = parser.add_argument_group('actions')
    actions.add_argument(
        '--continue', default=False, action='store_true', help='continue'
    )
    actions.add_argument(
        '--abort',
        default=False,
        action='store_true',
        help='abort and check out the original branch',
    )
    actions.add_argument(
        '--skip',
        default=False,
        action='store_true',
        help='skip current patch and continue',
    )
    actions.add_argument(
        '--edit-todo',
        default=False,
        action='store_true',
        help='edit the todo list during an interactive rebase',
    )

    parser.add_argument(
        'upstream',
        nargs='?',
        default=None,
        metavar='<upstream>',
        help='the upstream configured in branch.<name>.remote '
        'and branch.<name>.merge options will be used '
        'when <upstream> is omitted; see git-rebase(1) '
        'for details. If you are currently not on any '
        'branch or if the current branch does not have '
        'a configured upstream, the rebase will abort',
    )
    parser.add_argument(
        'branch',
        nargs='?',
        default=None,
        metavar='<branch>',
        help='git rebase will perform an automatic '
        '"git checkout <branch>" before doing anything '
        'else when <branch> is specified',
    )


def add_recent_command(subparser):
    add_command(subparser, 'recent', 'edit recent files', cmd_recent)


def add_remote_command(subparser):
    add_command(subparser, 'remote', 'edit remotes', cmd_remote)


def add_search_command(subparser):
    add_command(subparser, 'search', 'search commits', cmd_search)


def add_stash_command(subparser):
    add_command(subparser, 'stash', 'stash and unstash changes', cmd_stash)


def add_tag_command(subparser):
    parser = add_command(subparser, 'tag', 'create tags', cmd_tag)
    parser.add_argument(
        'name', metavar='<name>', nargs='?', default=None, help='tag name'
    )
    parser.add_argument(
        'ref', metavar='<ref>', nargs='?', default=None, help='commit to tag'
    )
    parser.add_argument(
        '-s',
        '--sign',
        default=False,
        action='store_true',
        help='annotated and GPG-signed tag',
    )


def add_version_command(subparser):
    parser = add_command(subparser, 'version', 'print the version', cmd_version)
    parser.add_argument(
        '--brief',
        action='store_true',
        default=False,
        help='print the version number only',
    )
    parser.add_argument(
        '--build', action='store_true', default=False, help='print the build version'
    )


# entry points
def cmd_cola(args):
    from .widgets.main import MainView  # pylint: disable=all

    status_filter = args.status_filter
    if status_filter:
        status_filter = core.abspath(status_filter)

    context = app.application_init(args)

    context.timer.start('view')
    view = MainView(context)
    if args.amend:
        cmds.do(cmds.AmendMode, context, amend=True)

    if status_filter:
        view.set_filter(core.relpath(status_filter))

    context.timer.stop('view')
    if args.perf:
        context.timer.display('view')

    return app.application_run(context, view, start=start_cola, stop=app.default_stop)


def start_cola(context, view):
    app.default_start(context, view)
    view.start(context)


def cmd_about(args):
    from .widgets import about  # pylint: disable=all

    context = app.application_init(args)
    view = about.about_dialog(context)
    return app.application_start(context, view)


def cmd_am(args):
    from .widgets.patch import new_apply_patches  # pylint: disable=all

    context = app.application_init(args)
    view = new_apply_patches(context, patches=args.patches)
    return app.application_start(context, view)


def cmd_archive(args):
    from .widgets import archive  # pylint: disable=all

    context = app.application_init(args, update=True)
    if args.ref is None:
        args.ref = context.model.currentbranch
    view = archive.Archive(context, args.ref)
    return app.application_start(context, view)


def cmd_branch(args):
    from .widgets.createbranch import create_new_branch  # pylint: disable=all

    context = app.application_init(args, update=True)
    view = create_new_branch(context)
    return app.application_start(context, view)


def cmd_browse(args):
    from .widgets.browse import worktree_browser  # pylint: disable=all

    context = app.application_init(args)
    view = worktree_browser(context, show=False, update=False)
    return app.application_start(context, view)


def cmd_clone(args):
    from .widgets import clone  # pylint: disable=all

    context = app.application_init(args)
    view = clone.clone(context)
    context.set_view(view)
    result = 0 if view.exec_() == view.Accepted else 1
    app.default_stop(context, view)
    return result


def cmd_config(args):
    from .widgets.prefs import preferences  # pylint: disable=all

    context = app.application_init(args)
    view = preferences(context)
    return app.application_start(context, view)


def cmd_dag(args):
    from .widgets import dag  # pylint: disable=all

    context = app.application_init(args)
    # cola.main() uses parse_args(), unlike dag.main() which uses
    # parse_known_args(), thus we aren't able to automatically forward
    # all unknown arguments.  Special-case support for "--all" since it's
    # used by the history viewer command on Windows.
    if args.show_all:
        args.args.insert(0, '--all')
    view = dag.git_dag(context, args=args, show=False)
    return app.application_start(context, view)


def cmd_diff(args):
    from .difftool import diff_expression  # pylint: disable=all

    context = app.application_init(args)
    expr = core.list2cmdline(args.args)
    view = diff_expression(context, None, expr, create_widget=True)
    return app.application_start(context, view)


def cmd_fetch(args):
    # TODO: the calls to update_status() can be done asynchronously
    # by hooking into the message_updated notification.
    from .widgets import remote  # pylint: disable=all

    context = app.application_init(args)
    context.model.update_status()
    view = remote.fetch(context)
    return app.application_start(context, view)


def cmd_find(args):
    from .widgets import finder  # pylint: disable=all

    context = app.application_init(args)
    paths = core.list2cmdline(args.paths)
    view = finder.finder(context, paths=paths)
    return app.application_start(context, view)


def cmd_grep(args):
    from .widgets import grep  # pylint: disable=all

    context = app.application_init(args)
    text = core.list2cmdline(args.args)
    view = grep.new_grep(context, text=text, parent=None)
    return app.application_start(context, view)


def cmd_merge(args):
    from .widgets.merge import Merge  # pylint: disable=all

    context = app.application_init(args, update=True)
    view = Merge(context, parent=None, ref=args.ref)
    return app.application_start(context, view)


def cmd_version(args):
    from . import version  # pylint: disable=all

    version.print_version(brief=args.brief, build=args.build)
    return 0


def cmd_pull(args):
    from .widgets import remote  # pylint: disable=all

    context = app.application_init(args, update=True)
    view = remote.pull(context)
    if args.rebase:
        view.set_rebase(True)
    return app.application_start(context, view)


def cmd_push(args):
    from .widgets import remote  # pylint: disable=all

    context = app.application_init(args, update=True)
    view = remote.push(context)
    return app.application_start(context, view)


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
        'exec': getattr(args, 'exec', None),  # python keyword
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
        'continue': getattr(args, 'continue', False),  # python keyword
        'abort': args.abort,
        'skip': args.skip,
        'edit_todo': args.edit_todo,
        'upstream': args.upstream,
        'branch': args.branch,
    }
    context = app.application_init(args)
    status, _, _ = cmds.do(cmds.Rebase, context, **kwargs)
    return status


def cmd_recent(args):
    from .widgets import recent  # pylint: disable=all

    context = app.application_init(args)
    view = recent.browse_recent_files(context)
    return app.application_start(context, view)


def cmd_remote(args):
    from .widgets import editremotes  # pylint: disable=all

    context = app.application_init(args)
    view = editremotes.editor(context, run=False)
    return app.application_start(context, view)


def cmd_search(args):
    from .widgets.search import search  # pylint: disable=all

    context = app.application_init(args)
    view = search(context)
    return app.application_start(context, view)


def cmd_stash(args):
    from .widgets import stash  # pylint: disable=all

    context = app.application_init(args)
    view = stash.view(context, show=False)
    return app.application_start(context, view)


def cmd_tag(args):
    from .widgets.createtag import new_create_tag  # pylint: disable=all

    context = app.application_init(args)
    view = new_create_tag(context, name=args.name, ref=args.ref, sign=args.sign)
    return app.application_start(context, view)


# Windows shortcut launch features:
def shortcut_launch():
    """Launch from a shortcut

    Prompt for the repository by default.

    """
    argv = sys.argv[1:]
    if not argv:
        argv = ['cola', '--prompt']
    return app.winmain(main, argv)
