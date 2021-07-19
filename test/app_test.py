from __future__ import absolute_import, division, print_function, unicode_literals
import argparse

from cola import app


def test_setup_environment():
    # If the function doesn't throw an exception we are happy.
    assert hasattr(app, 'setup_environment')
    app.setup_environment()


def test_add_common_arguments():
    # If the function doesn't throw an exception we are happy.
    parser = argparse.ArgumentParser()
    assert hasattr(app, 'add_common_arguments')
    app.add_common_arguments(parser)
