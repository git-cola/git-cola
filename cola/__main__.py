"""
Run cola as a Python module.

Usage:

    python -m cola

"""
from __future__ import absolute_import, division, unicode_literals

import sys

from cola import main


def run():
    """Start the command-line interface."""
    main.main()


def run_dag():
    args = ["dag"] + sys.argv[1:]
    main.main(args)


if __name__ == '__main__':
    run()
