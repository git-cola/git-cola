pythondir = os.path.join(scriptdir, 'Python')
os.environ['PATH'] = (
    pythondir + os.pathsep + pkgdir + os.pathsep + os.environ.get('PATH', ''))
