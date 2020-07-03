import os

pythondir = os.path.join(installdir, 'Python')
path = os.environ.get('PATH', '')
os.environ['PATH'] = os.pathsep.join([pythondir, pkgdir, path])  # noqa
