from __future__  import absolute_import, division, unicode_literals

from extras.build_mo import build_mo
from extras.build_pot import build_pot


cmdclass = {
    'build_mo': build_mo,
    'build_pot': build_pot,
}
