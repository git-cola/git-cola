"""build_helpers command for setup.py"""
# pylint: disable=attribute-defined-outside-init
# pylint: disable=import-error,no-name-in-module
from __future__ import absolute_import, division, unicode_literals
from distutils.command.build_scripts import build_scripts
import os
import sys


class build_helpers(build_scripts):

    description = "fixup #! lines for private share/git-cola/bin scripts"

    # Private share/git-cola/bin scripts that are visible to cola only.
    helpers = []

    def finalize_options(self):
        """Set variables to copy/edit files to build/helpers-x.y"""
        build_scripts.finalize_options(self)

        self.build_dir = os.path.join(
            'build', 'helpers-%s.%s' % sys.version_info[:2])

        self.scripts = self.helpers
