import os
from PyQt4 import QtGui

import cola
import cola.app
from cola import i18n
from cola import core
from cola import git
from cola import gitcmds
from cola import qtutils
from cola import signals
from cola.views import itemlist
from cola.views import combo


def install_command_wrapper(parent):
    wrapper = CommandWrapper(parent)
    cola.factory().add_command_wrapper(wrapper)


class CommandWrapper(object):
    def __init__(self, parent):
        self.parent = parent
        self.callbacks = {
                signals.question: self._question,
                signals.information: self._information,
        }

    def _question(self, title, msg):
        return qtutils.question(self.parent, title, msg)

    def _information(self, title, msg):
        if msg is None:
            msg = title
        title = i18n.gettext(title)
        msg = i18n.gettext(msg)
        QtGui.QMessageBox.information(self.parent, title, msg)


def choose_from_combo(title, items):
    """Quickly choose an item from a list using a combo box"""
    parent = QtGui.QApplication.instance().activeWindow()
    return combo.ComboView(parent,
                           title=title,
                           items=items).selected()


def choose_from_list(title, items=None, dblclick=None):
    """Quickly choose an item from a list using a list widget"""
    parent = QtGui.QApplication.instance().activeWindow()
    return itemlist.ListView(parent,
                             title=title,
                             items=items,
                             dblclick=dblclick).selected()


def slot_with_parent(fn, parent):
    """Return an argument-less method for calling fn(parent=parent)

    :param fn: - Function reference, must accept 'parent' as a keyword
    :param parent: - Qt parent widget

    """
    def slot():
        fn(parent=parent)
    return slot


def branch_delete():
    """Launch the 'Delete Branch' dialog."""
    branch = choose_from_combo('Delete Branch',
                               cola.model().local_branches)
    if not branch:
        return
    cola.notifier().broadcast(signals.delete_branch, branch)


def branch_diff():
    """Diff against an arbitrary revision, branch, tag, etc."""
    branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                               ['HEAD^'] +
                               cola.model().all_branches() +
                               cola.model().tags)
    if not branch:
        return
    cola.notifier().broadcast(signals.diff_mode, branch)


def browse_commits():
    """Launch the 'Browse Commits' dialog."""
    from cola.controllers.selectcommits import select_commits

    revs, summaries = gitcmds.log_helper(all=True)
    select_commits('Browse Commits', revs, summaries)


def browse_current():
    """Launch the 'Browse Current Branch' dialog."""
    from cola.controllers.repobrowser import browse_git_branch

    browse_git_branch(gitcmds.current_branch())


def browse_other():
    """Prompt for a branch and inspect content at that point in time."""
    # Prompt for a branch to browse
    from cola.controllers.repobrowser import browse_git_branch

    branch = choose_from_combo('Browse Revision...', gitcmds.all_refs())
    if not branch:
        return
    # Launch the repobrowser
    browse_git_branch(branch)


def checkout_branch():
    """Launch the 'Checkout Branch' dialog."""
    branch = choose_from_combo('Checkout Branch',
                               cola.model().local_branches)
    if not branch:
        return
    cola.notifier().broadcast(signals.checkout_branch, branch)


def cherry_pick():
    """Launch the 'Cherry-Pick' dialog."""
    from cola.controllers.selectcommits import select_commits

    revs, summaries = gitcmds.log_helper(all=True)
    commits = select_commits('Cherry-Pick Commit',
                             revs, summaries, multiselect=False)
    if not commits:
        return
    cola.notifier().broadcast(signals.cherry_pick, commits)


def clone_repo(spawn=True):
    """
    Present GUI controls for cloning a repository

    A new cola session is invoked when 'spawn' is True.

    """
    url, ok = qtutils.prompt('Path or URL to clone (Env. $VARS okay)')
    url = os.path.expandvars(core.encode(url))
    if not ok or not url:
        return None
    try:
        # Pick a suitable basename by parsing the URL
        newurl = url.replace('\\', '/')
        default = newurl.rsplit('/', 1)[-1]
        if default == '.git':
            # The end of the URL is /.git, so assume it's a file path
            default = os.path.basename(os.path.dirname(newurl))
        if default.endswith('.git'):
            # The URL points to a bare repo
            default = default[:-4]
        if url == '.':
            # The URL is the current repo
            default = os.path.basename(os.getcwd())
        if not default:
            raise
    except:
        cola.notifier().broadcast(signals.information,
                                  'Error Cloning',
                                  'Could not parse: "%s"' % url)
        qtutils.log(1, 'Oops, could not parse git url: "%s"' % url)
        return None

    # Prompt the user for a directory to use as the parent directory
    parent = QtGui.QApplication.instance().activeWindow()
    msg = 'Select a parent directory for the new clone'
    dirname = qtutils.opendir_dialog(parent, msg, cola.model().getcwd())
    if not dirname:
        return None
    count = 1
    dirname = core.decode(dirname)
    destdir = os.path.join(dirname, core.decode(default))
    olddestdir = destdir
    if os.path.exists(destdir):
        # An existing path can be specified
        msg = ('"%s" already exists, cola will create a new directory' %
               destdir)
        cola.notifier().broadcast(signals.information,
                                  'Directory Exists', msg)

    # Make sure the new destdir doesn't exist
    while os.path.exists(destdir):
        destdir = olddestdir + str(count)
        count += 1
    cola.notifier().broadcast(signals.clone, core.decode(url), destdir,
                              spawn=spawn)
    return destdir


def export_patches():
    """Run 'git format-patch' on a list of commits."""
    from cola.controllers.selectcommits import select_commits

    revs, summaries = gitcmds.log_helper()
    to_export = select_commits('Export Patches', revs, summaries)
    if not to_export:
        return
    to_export.reverse()
    revs.reverse()
    cola.notifier().broadcast(signals.format_patch, to_export, revs)


def diff_branch():
    """Launches a diff against a branch."""
    branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                               ['HEAD^'] +
                               cola.model().all_branches() +
                               cola.model().tags)
    if not branch:
        return
    zfiles_str = git.instance().diff(branch, name_only=True,
                                     no_color=True,
                                     z=True).rstrip('\0')
    files = zfiles_str.split('\0')
    filename = choose_from_list('Select File', files)
    if not filename:
        return
    cola.notifier().broadcast(signals.branch_mode, branch, filename)


def diff_expression():
    """Diff using an arbitrary expression."""
    expr = choose_from_combo('Enter Diff Expression',
                             cola.model().all_branches() +
                             cola.model().tags)
    if not expr:
        return
    cola.notifier().broadcast(signals.diff_expr_mode, expr)


def goto_grep(line):
    """Called when Search -> Grep's right-click 'goto' action."""
    filename, line_number, contents = line.split(':', 2)
    filename = core.encode(filename)
    cola.notifier().broadcast(signals.edit, [filename], line_number=line_number)


def grep():
    """Prompt and use 'git grep' to find the content."""
    # This should be a command in cola.cmds.
    txt, ok = qtutils.prompt('grep')
    if not ok:
        return
    cola.notifier().broadcast(signals.grep, txt)


def open_repo(parent):
    """Spawn a new cola session."""
    dirname = qtutils.opendir_dialog(parent,
                                     'Open Git Repository...',
                                     cola.model().getcwd())
    if not dirname:
        return
    cola.notifier().broadcast(signals.open_repo, dirname)

def open_repo_slot(parent):
    return slot_with_parent(open_repo, parent)


def load_commitmsg(parent):
    """Load a commit message from a file."""
    filename = qtutils.open_dialog(parent,
                                   'Load Commit Message...',
                                   cola.model().getcwd())
    if filename:
        cola.notifier().broadcast(signals.load_commit_message, filename)

def load_commitmsg_slot(parent):
    return slot_with_parent(load_commitmsg, parent)


def rebase():
    """Rebase onto a branch."""
    branch = choose_from_combo('Rebase Branch',
                               cola.model().all_branches())
    if not branch:
        return
    #TODO cmd
    status, output = git.instance().rebase(branch,
                                           with_stderr=True,
                                           with_status=True)
    qtutils.log(status, output)


def review_branch():
    """Diff against an arbitrary revision, branch, tag, etc."""
    branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                               cola.model().all_branches() +
                               cola.model().tags)
    if not branch:
        return
    cola.notifier().broadcast(signals.review_branch_mode, branch)


def fetch(parent):
    """Launch the 'fetch' remote dialog."""
    from cola.controllers.remote import remote_action

    remote_action(parent, 'fetch')

def fetch_slot(parent):
    return slot_with_parent(fetch, parent)


def push(parent):
    """Launch the 'push' remote dialog."""
    from cola.controllers.remote import remote_action

    remote_action(parent, 'push')

def push_slot(parent):
    return slot_with_parent(push, parent)


def pull(parent):
    """Launch the 'pull' remote dialog."""
    from cola.controllers.remote import remote_action

    remote_action(parent, 'pull')

def pull_slot(parent):
    return slot_with_parent(pull, parent)
