"""install_helpers command for setup.py"""
# pylint: disable=attribute-defined-outside-init
from __future__ import absolute_import, division, unicode_literals
from distutils.command.install_scripts import install_scripts
import os
import sys


class install_helpers(install_scripts):

    description = "install helper scripts"

    boolean_options = ['force', 'skip-build']

    def initialize_options(self):
        install_scripts.initialize_options(self)
        self.skip_build_helpers = None
        self.install_scripts_dir = None

    def finalize_options(self):
        self.set_undefined_options(
            'install',
            ('install_scripts', 'install_scripts_dir'),
            ('force', 'force'),
            ('skip_build', 'skip_build_helpers'),
        )
        self.build_dir = os.path.join(
            'build', 'helpers-%s.%s' % sys.version_info[:2])
        self.install_prefix = os.path.dirname(self.install_scripts_dir)
        self.install_dir = os.path.join(
            self.install_prefix, 'share', 'git-cola', 'bin')
        self.skip_build = True

    def run(self):
        if not self.skip_build_helpers:
            self.run_command('build_helpers')

        install_scripts.run(self)
