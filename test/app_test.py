#!/usr/bin/env python
from __future__ import absolute_import, division, unicode_literals
import argparse
import unittest

from cola import app

from .helper import run_unittest


class AppTestCase(unittest.TestCase):

    def test_setup_environment(self):
        # If the function doesn't throw an exception we are happy.
        self.assertTrue(hasattr(app, 'setup_environment'))
        app.setup_environment()

    def test_add_common_arguments(self):
        # If the function doesn't throw an exception we are happy.
        parser = argparse.ArgumentParser()
        self.assertTrue(hasattr(app, 'add_common_arguments'))
        app.add_common_arguments(parser)


def test_suite():
    return unittest.makeSuite(AppTestCase)


if __name__ == "__main__":
    run_unittest(test_suite())
