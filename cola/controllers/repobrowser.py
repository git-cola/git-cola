"""This controller handles the repository file browser."""


import os

from PyQt4 import QtGui

import cola
from cola import git
from cola import gitcmds
from cola import utils
from cola import resources
from cola import qtutils
from cola.models import browser
from cola.views.selectcommits import SelectCommitsView
from cola.qobserver import QObserver

git = git.instance()


def select_file_from_repo():
    """Launch a dialog for selecting a filename from a branch."""
    # Clone the model to allow opening multiple browsers
    # with different sets of data
    model = browser.BrowserModel(gitcmds.current_branch())
    parent = QtGui.QApplication.instance().activeWindow()
    view = SelectCommitsView(parent, syntax=False)
    controller = RepoBrowserController(model, view,
                                       title='Select File',
                                       get_file=True)
    view.show()
    if view.exec_() == QtGui.QDialog.Accepted:
        return controller.filename
    else:
        return None

def browse_git_branch(branch):
    """Launch a dialog to browse files in a specific branch."""
    if not branch:
        return
    model = browser.BrowserModel(branch)
    parent = QtGui.QApplication.instance().activeWindow()
    view = SelectCommitsView(parent, syntax=False)
    controller = RepoBrowserController(model, view)
    view.show()
    return view.exec_() == QtGui.QDialog.Accepted


class RepoBrowserController(QObserver):
    """Provides control to the Repository Browser."""
    def __init__(self, model, view,
                 title='File Browser', get_file=False):
        QObserver.__init__(self, model, view)

        self.get_file = get_file
        """Whether we should returns a selected file"""

        self.filename = None
        """The last selected filename"""

        view.setWindowTitle(title)
        self.add_signals('itemSelectionChanged()', view.commit_list,)
        self.add_actions(directory = self.action_directory_changed)
        self.add_callbacks(commit_list = self.item_changed)
        view.commit_list.contextMenuEvent = self.context_menu_event
        # Start at the root of the tree
        model.set_directory('')
        self.refresh_view()

    def context_menu_event(self, event):
        """Generate a context menu for the repository browser."""
        menu = QtGui.QMenu(self.view);
        menu.addAction(self.tr('Blame'), self.blame)
        menu.exec_(self.view.commit_list.mapToGlobal(event.pos()))

    def blame(self):
        """Show git-blame output for a file path."""
        current = self.view.commit_list.currentRow()
        item = self.view.commit_list.item(current)
        if item is None or not item.isSelected():
            return
        directories = self.model.directories
        directory_entries = self.model.directory_entries
        if current < len(directories):
            # ignore directories
            return
        idx = current - len(directories)
        if idx >= len(self.model.subtree_sha1s):
            return
        objtype, sha1, name = self.model.subtree_node(idx)
        curdir = self.model.directory
        if curdir:
            filename = os.path.join(curdir, name)
        else:
            filename = name
        blame = git.blame(self.model.currentbranch, filename)
        self.view.commit_text.setText(blame)

    ######################################################################
    # Actions
    def action_directory_changed(self):
        """Called in response to a change in the model's directory."""
        self.model.init_browser_data()
        self._display_items()

    ######################################################################
    # Qt callbacks
    def item_changed(self,*rest):
        """Called when the current item changes"""
        current = self.view.commit_list.currentRow()
        item = self.view.commit_list.item(current)
        if item is None or not item.isSelected():
            self.view.revision.setText('')
            self.view.commit_text.setText('')
            return
        directories = self.model.directories
        directory_entries = self.model.directory_entries
        if current < len(directories):
            # This is a directory...
            self.filename = None
            dirent = directories[current]
            if dirent != '..':
                # This is a real directory for which
                # we have child entries
                entries = directory_entries[dirent]
            else:
                # This is '..' which is a special case
                # since it doesn't really exist
                entries = []
            self.view.commit_text.setText('\n'.join(entries))
            self.view.revision.setText('')
        else:
            # This is a file entry.  The current row is absolute,
            # so get a relative index by subtracting the number
            # of directory entries
            idx = current - len(directories)
            if idx >= len(self.model.subtree_sha1s):
                # This can happen when changing directories
                self.filename = None
                return
            objtype, sha1, name = self.model.subtree_node(idx)

            curdir = self.model.directory
            if curdir:
                self.filename = os.path.join(curdir, name)
            else:
                self.filename = name

            catguts = git.cat_file(objtype, sha1, with_raw_output=True)
            self.view.commit_text.setText(catguts)

            self.view.revision.setText(sha1)
            self.view.revision.selectAll()

            # Copy the sha1 into the clipboard
            qtutils.set_clipboard(sha1)

    # automatically called by qobserver
    def commit_list_doubleclick(self,*rest):
        """
        Called when an entry is double-clicked.

        This callback changes the model's directory when
        invoked on a directory item.  When invoked on a file
        it allows the file to be saved.

        """
        current = self.view.commit_list.currentRow()
        directories = self.model.directories

        # A file item was double-clicked.
        # Create a save-as dialog and export the file,
        # or if in get_file mode, grab the filename and finish the dialog.
        if current >= len(directories):
            idx = current - len(directories)

            objtype, sha1, name = self.model.subtree_node(idx)

            if self.get_file:
                if self.model.directory:
                    curdir = self.model.directory
                    self.filename = os.path.join(curdir, name)
                else:
                    self.filename = name
                self.view.accept()
                return

            nameguess = os.path.join(self.model.directory, name)
            filename = qtutils.save_dialog(self.view, 'Save', nameguess)
            if not filename:
                return
            self.model.set_directory(os.path.dirname(filename))
            contents = git.cat_file(objtype, sha1, with_raw_output=True)
            utils.write(filename, contents)
            return

        dirent = directories[current]
        curdir = self.model.directory

        # "change directories"
        # '..' is a special case--it doesn't really exist...
        if dirent == '..':
            newdir = os.path.dirname(os.path.dirname(curdir))
            if newdir == '':
                self.model.set_directory(newdir)
            else:
                self.model.set_directory(newdir + os.sep)
        else:
            self.model.set_directory(curdir + dirent)

    def _display_items(self):
        """
        Populate the commit_list with the current directories and items

        Directories are always listed first.

        """

        # Clear commit/revision fields
        self.view.commit_text.setText('')
        self.view.revision.setText('')

        dir_icon = resources.icon('dir.png')
        file_icon = resources.icon('generic.png')
        # Factory method for creating items
        creator = qtutils.create_listwidget_item

        # First the directories,
        qtutils.set_items(self.view.commit_list,
                          map(lambda d: creator(d, dir_icon),
                              self.model.directories))
        # and now the filenames
        qtutils.add_items(self.view.commit_list,
                          map(lambda s: creator(s, file_icon),
                              self.model.subtree_names))
