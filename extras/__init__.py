from __future__ import absolute_import, division, unicode_literals
from distutils.command.build import build
from distutils.command.install import install

from extras.build_helpers import build_helpers
from extras.build_mo import build_mo
from extras.build_pot import build_pot
from extras.install_helpers import install_helpers


cmdclass = {
    'build_mo': build_mo,
    'build_pot': build_pot,
    'build_helpers': build_helpers,
    'install_helpers': install_helpers,
}


build.sub_commands.insert(0, ('build_mo', None))
build.sub_commands.append(('build_helpers', None))

install.sub_commands.append(('install_helpers', None))
