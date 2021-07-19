"""Run cola as a Python module.

Usage: python -m cola
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from cola import main


def run():
    """Start the command-line interface."""
    main.main()


if __name__ == '__main__':
    run()
