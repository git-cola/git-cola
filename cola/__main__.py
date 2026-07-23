"""Run cola as a Python module.

Usage: python -m cola
"""

from cola import main


def run() -> None:
    """Start the command-line interface. test comment for garden checks"""
    main.main()


if __name__ == '__main__':
    run()
