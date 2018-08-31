# TODO pynsist commands call it "installdir", entry points call it "scriptdir"
import os
try:
    installdir = scriptdir  # noqa
except NameError:
    pass
pythondir = os.path.join(installdir, 'Python')
os.environ['PATH'] = (
    pythondir + os.pathsep
    + pkgdir  # noqa
    + os.pathsep + os.environ.get('PATH', ''))
