try:
    from setuptools.command.build import build as build_base
except ImportError:
    try:
        from setuptools._distutils.command.build import build as build_base
    except ImportError:
        from distutils.command.build import build as build_base
