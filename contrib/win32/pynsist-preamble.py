# TODO pynsist commands call it "installdir", entry points call it "scriptdir"
import os

try:
    installdir = scriptdir
except NameError:
    pass
pythondir = os.path.join(installdir, 'Python')
path = os.environ.get('PATH', '')
os.environ['PATH'] = os.pathsep.join([pythondir, pkgdir, path])  # noqa
