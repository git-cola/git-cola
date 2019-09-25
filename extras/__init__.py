from __future__ import absolute_import, division, unicode_literals
from distutils.command import build, install

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

build.build.sub_commands.append(('build_helpers', lambda self: True))
install.install.sub_commands.append(('install_helpers', lambda self: True))
