# pylint: disable=import-error,no-name-in-module
from __future__ import absolute_import, division, print_function, unicode_literals
from distutils.command.build import build

from extras.build_mo import build_mo
from extras.build_pot import build_pot


cmdclass = {
    'build_mo': build_mo,
    'build_pot': build_pot,
}


build.sub_commands.insert(0, ('build_mo', None))
