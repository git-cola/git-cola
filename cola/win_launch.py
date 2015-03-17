"""Launch git-cola from a Windows shortcut."""
import os
from cola import core

class DummyArgs(object):
    version = False
    prompt = True
    session = None

    @property
    def repo(self):
        return core.getcwd()

    @property
    def git_path(self):
        # For now, we assume that git is installed in one of the typical
        # locations. This should be smarter.
        pf = os.environ.get('ProgramFiles', 'C:\\Program Files')
        pf32 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
        for p in [pf32, pf]:
            candidate = os.path.join(p, 'Git\\bin')
            if os.path.isdir(candidate):
                return os.path.join(candidate, 'git')

def launch():
    from cola.app import application_init, application_start
    from cola.widgets.main import MainView

    context = application_init(DummyArgs())
    view = MainView(context.model)
    return application_start(context, view)
