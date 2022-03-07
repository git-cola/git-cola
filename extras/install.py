from __future__ import absolute_import, division, print_function, unicode_literals
from setuptools.command.install import install


install.sub_commands = [
    ('build_mo', None),
] + list(install.sub_commands)
