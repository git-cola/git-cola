from extras.build_mo import build_mo
from extras.build_qm import build_qm
from extras.build_pot import build_pot


cmdclass = {
    'build_mo': build_mo,
    'build_qm': build_qm,
    'build_pot': build_pot,
}
