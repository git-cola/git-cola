import os


def pytest_configure(config):
    if 'USE_QT_API' in os.environ:
        os.environ['QT_API'] = os.environ['USE_QT_API'].lower()


def pytest_report_header(config):

    versions = os.linesep
    versions += 'PyQt4: '

    try:
        from PyQt4 import Qt
        versions += "PyQt: {0} - Qt: {1}".format(Qt.PYQT_VERSION_STR, Qt.QT_VERSION_STR)
    except ImportError:
        versions += 'not installed'
    except AttributeError:
        versions += 'unknown version'

    versions += os.linesep
    versions += 'PyQt5: '

    try:
        from PyQt5 import Qt
        versions += "PyQt: {0} - Qt: {1}".format(Qt.PYQT_VERSION_STR, Qt.QT_VERSION_STR)
    except ImportError:
        versions += 'not installed'
    except AttributeError:
        versions += 'unknown version'

    versions += os.linesep
    versions += 'PySide: '

    try:
        import PySide
        from PySide import QtCore
        versions += "PySide: {0} - Qt: {1}".format(PySide.__version__, QtCore.__version__)
    except ImportError:
        versions += 'not installed'
    except AttributeError:
        versions += 'unknown version'

    versions += os.linesep
    
    return versions
