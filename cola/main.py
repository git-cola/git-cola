# Copyright(C) 2008, David Aguilar <davvid@gmail.com>

import optparse
import sys
import os

from cola import utils
from cola import version
from cola.models import Model

def main():
    parser = optparse.OptionParser(usage='%prog [options]')

    parser.add_option('-v', '--version',
                      help='Show cola version',
                      dest='version',
                      default=False,
                      action='store_true')
    parser.add_option('-s', '--style',
                      help='Applies an alternate stylesheet.  '
                           'The allowed values are: "dark" or a file path.',
                      dest='style',
                      metavar='PATH or STYLE',
                      default='')
    parser.add_option('-r', '--repo',
                      help='Specifies the path to a git repository.',
                      dest='repo',
                      metavar='PATH',
                      default=os.getcwd())
    opts, args = parser.parse_args()

    if opts.version or 'version' in args:
        print "cola version", version.version
        sys.exit(0)

    repo = os.path.realpath(opts.repo)
    if not os.path.isdir(repo):
        print >> sys.stderr, "fatal: '%s' is not a directory.  Consider supplying -r <path>.\n" % repo
        sys.exit(-1)

    # load the model right away so that we can bail out when
    # no git repo exists
    os.chdir(repo)
    model = Model()
    try:
        # Defer these imports to allow git cola --version without pyqt installed
        from PyQt4 import QtCore
        from PyQt4 import QtGui
    except ImportError:
        print >> sys.stderr, 'Sorry, you do not seem to have PyQt4 installed.'
        print >> sys.stderr, 'Please install it before using cola.'
        print >> sys.stderr, 'e.g.:    sudo apt-get install python-qt4'
        sys.exit(-1)

    class ColaApplication(QtGui.QApplication):
        """This makes translation work by throwing out the context."""
        wrapped = QtGui.QApplication.translate
        def translate(*args):
            trtxt = unicode(ColaApplication.wrapped('', *args[2:]))
            if trtxt[-6:-4] == '@@': # handle @@verb / @@noun
                trtxt = trtxt[:-6]
            return trtxt

    app = ColaApplication(sys.argv)
    QtGui.QApplication.translate = app.translate
    app.setWindowIcon(QtGui.QIcon(utils.get_icon('git.png')))
    locale = str(QtCore.QLocale().system().name())
    qmfile = utils.get_qm_for_locale(locale)
    if os.path.exists(qmfile):
        translator = QtCore.QTranslator(app)
        translator.load(qmfile)
        app.installTranslator(translator)

    if opts.style:
        # This loads the built-in and user-specified stylesheets.
        # We allows absolute and relative paths to a stylesheet
        # by assuming that non-file arguments refer to a built-in style.
        if os.path.isabs(opts.style) or os.path.isfile(opts.style):
            filename = opts.style
        else:
            filename = utils.get_stylesheet(opts.style)

        try:
            # Automatically register each subdirectory in the style dir
            # as a Qt resource directory.
            dirname = os.path.dirname(filename)
            resource_paths = []
            resource_paths.extend(utils.get_resource_dirs(dirname))
            for r in resource_paths:
                basename = os.path.basename(r)
                QtCore.QDir.setSearchPaths(basename, [r])
            stylesheet = open(filename, 'r')
            style = stylesheet.read()
            stylesheet.close()
            app.setStyleSheet(style)
        except:
            print >> sys.stderr, ("warn: '%s' is not a valid style."
                                  % opts.style)
    # simple mvc
    from cola.views import View
    from cola.controllers import Controller
    view = View(app.activeWindow())
    ctl = Controller(model, view)
    view.show()
    sys.exit(app.exec_())
