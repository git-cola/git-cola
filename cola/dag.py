from __future__ import absolute_import, division, print_function, unicode_literals
import argparse
import sys

from cola import app
from cola.widgets.dag import git_dag


def main(argv=None):
    """Run git-dag"""
    app.initialize()
    args = parse_args(argv=argv)
    return args.func(args)


def winmain():
    """Windows git-dag entrypoint"""
    return app.winmain(main)


def shortcut_launch():
    """Run git-dag from a Windows shortcut"""
    return app.winmain(main, ['--prompt'])


def parse_args(argv=None):
    """Parse command-line arguments"""
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=cmd_dag)

    app.add_common_arguments(parser)
    parser.add_argument(
        '-c',
        '--count',
        '--max-count',
        metavar='<count>',
        type=int,
        default=1000,
        help='number of commits to display',
    )
    parser.add_argument('args', nargs='*', metavar='<args>', help='git log arguments')
    args, rest = parser.parse_known_args(args=argv)
    if rest:
        # splice unknown arguments to the beginning ~
        # these are forwarded to git-log(1).
        args.args[:0] = rest
    return args


def cmd_dag(args):
    """Run git-dag via the `git cola dag` sub-command"""
    context = app.application_init(args)
    view = git_dag(context, args=args, show=False)
    return app.application_start(context, view)
