from __future__ import absolute_import, division, print_function, unicode_literals
import os
from functools import partial

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import cmds
from .. import core
from .. import icons
from .. import utils
from .. import qtutils
from ..i18n import N_
from ..interaction import Interaction
from ..qtutils import get
from . import defs
from . import standard
from . import text


def clone(context, spawn=True, show=True, parent=None):
    """Clone a repository and spawn a new git-cola instance"""
    parent = qtutils.active_window()
    progress = standard.progress('', '', parent)
    return clone_repo(context, parent, show, progress, task_finished, spawn)


def clone_repo(context, parent, show, progress, finish, spawn):
    """Clone a repository asynchronously with progress animation"""
    fn = partial(start_clone_task, context, parent, progress, finish, spawn)
    prompt = prompt_for_clone(context, show=show)
    prompt.result.connect(fn)
    return prompt


def prompt_for_clone(context, show=True):
    """Presents a GUI for cloning a repository"""
    view = Clone(context, parent=qtutils.active_window())
    if show:
        view.show()
    return view


def task_finished(task):
    """Report errors from the clone task if they exist"""
    cmd = task.cmd
    if cmd is None:
        return
    status = cmd.status
    out = cmd.out
    err = cmd.err
    title = N_('Error: could not clone "%s"') % cmd.url
    Interaction.command(title, 'git clone', status, out, err)


def start_clone_task(
    context, parent, progress, finish, spawn, url, destdir, submodules, shallow
):
    # Use a thread to update in the background
    runtask = context.runtask
    progress.set_details(N_('Clone Repository'), N_('Cloning repository at %s') % url)
    task = CloneTask(context, url, destdir, submodules, shallow, spawn, parent)
    runtask.start(task, finish=finish, progress=progress)


class CloneTask(qtutils.Task):
    """Clones a Git repository"""

    def __init__(self, context, url, destdir, submodules, shallow, spawn, parent):
        qtutils.Task.__init__(self, parent)
        self.context = context
        self.url = url
        self.destdir = destdir
        self.submodules = submodules
        self.shallow = shallow
        self.spawn = spawn
        self.cmd = None

    def task(self):
        """Runs the model action and captures the result"""
        self.cmd = cmds.do(
            cmds.Clone,
            self.context,
            self.url,
            self.destdir,
            self.submodules,
            self.shallow,
            spawn=self.spawn,
        )
        return self.cmd


class Clone(standard.Dialog):

    # Signal binding for returning the input data
    result = QtCore.Signal(object, object, bool, bool)

    def __init__(self, context, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.context = context
        self.model = context.model

        self.setWindowTitle(N_('Clone Repository'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        # Repository location
        self.url_label = QtWidgets.QLabel(N_('URL'))
        hint = 'git://git.example.com/repo.git'
        self.url = text.HintedLineEdit(context, hint, parent=self)
        self.url.setToolTip(N_('Path or URL to clone (Env. $VARS okay)'))

        # Initialize submodules
        self.submodules = qtutils.checkbox(
            text=N_('Inititalize submodules'), checked=False
        )

        # Reduce commit history
        self.shallow = qtutils.checkbox(
            text=N_('Reduce commit history to minimum'), checked=False
        )

        # Buttons
        self.ok_button = qtutils.create_button(
            text=N_('Clone'), icon=icons.ok(), default=True
        )
        self.close_button = qtutils.close_button()

        # Form layout for inputs
        self.input_layout = qtutils.form(
            defs.no_margin, defs.button_spacing, (self.url_label, self.url)
        )

        self.button_layout = qtutils.hbox(
            defs.margin,
            defs.spacing,
            self.submodules,
            defs.button_spacing,
            self.shallow,
            qtutils.STRETCH,
            self.ok_button,
            self.close_button,
        )

        self.main_layout = qtutils.vbox(
            defs.margin, defs.spacing, self.input_layout, self.button_layout
        )
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.close_button, self.close)
        qtutils.connect_button(self.ok_button, self.prepare_to_clone)
        # pylint: disable=no-member
        self.url.textChanged.connect(lambda x: self.update_actions())

        self.init_state(context.settings, self.resize, 720, 200)
        self.update_actions()

    def update_actions(self):
        url = get(self.url).strip()
        enabled = bool(url)
        self.ok_button.setEnabled(enabled)

    def prepare_to_clone(self):
        """Grabs and validates the input data"""

        submodules = get(self.submodules)
        shallow = get(self.shallow)

        url = get(self.url)
        url = utils.expandpath(url)
        if not url:
            return
        # Pick a suitable basename by parsing the URL
        newurl = url.replace('\\', '/').rstrip('/')
        try:
            default = newurl.rsplit('/', 1)[-1]
        except IndexError:
            default = ''
        if default == '.git':
            # The end of the URL is /.git, so assume it's a file path
            default = os.path.basename(os.path.dirname(newurl))
        if default.endswith('.git'):
            # The URL points to a bare repo
            default = default[:-4]
        if url == '.':
            # The URL is the current repo
            default = os.path.basename(core.getcwd())
        if not default:
            Interaction.information(
                N_('Error Cloning'), N_('Could not parse Git URL: "%s"') % url
            )
            Interaction.log(N_('Could not parse Git URL: "%s"') % url)
            return

        # Prompt the user for a directory to use as the parent directory
        msg = N_('Select a parent directory for the new clone')
        dirname = qtutils.opendir_dialog(msg, self.model.getcwd())
        if not dirname:
            return
        count = 1
        destdir = os.path.join(dirname, default)
        olddestdir = destdir
        if core.exists(destdir):
            # An existing path can be specified
            msg = N_('"%s" already exists, cola will create a new directory') % destdir
            Interaction.information(N_('Directory Exists'), msg)

        # Make sure the new destdir doesn't exist
        while core.exists(destdir):
            destdir = olddestdir + str(count)
            count += 1

        # Return the input data and close the dialog
        self.result.emit(url, destdir, submodules, shallow)
        self.close()
