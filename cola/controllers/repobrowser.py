#!/usr/bin/env python
import os
from PyQt4.QtGui import QDialog

from cola import utils
from cola import qtutils
from cola import defaults
from cola.views import CommitView
from cola.qobserver import QObserver

def select_file_from_repo(model, parent):
    model = model.clone()
    view = CommitView(parent)
    controller = RepoBrowserController(model, view,
                                       title='Select File',
                                       get_file=True)
    view.show()
    if view.exec_() == QDialog.Accepted:
        return controller.filename
    else:
        return None

def browse_git_branch(model, parent, branch):
    if not branch:
        return
    # Clone the model to allow opening multiple browsers
    # with different sets of data
    model = model.clone()
    model.set_currentbranch(branch)
    view = CommitView(parent)
    controller = RepoBrowserController(model, view)
    view.show()
    return view.exec_() == QDialog.Accepted

class RepoBrowserController(QObserver):
    def init(self, model, view, title='File Browser', get_file=False):
        self.get_file = get_file
        self.filename = None
        view.setWindowTitle(title)
        self.add_signals('itemSelectionChanged()', view.commit_list,)
        self.add_actions(directory = self.action_directory_changed)
        self.add_callbacks(commit_list = self.item_changed)
        self.connect(view.commit_list,
                     'itemDoubleClicked(QListWidgetItem*)',
                     self.item_double_clicked)
        # Start at the root of the tree
        model.set_directory('')

    ######################################################################
    # Actions
    def action_directory_changed(self):
        """This is called in response to a change in the the
        model's directory."""
        self.model.init_browser_data()
        self.__display_items()

    ######################################################################
    # Qt callbacks
    def item_changed(self,*rest):
        """This is called when the current item changes in the
        file/directory list(aka the commit_list)."""
        current = self.view.commit_list.currentRow()
        item = self.view.commit_list.item(current)
        if item is None or not item.isSelected():
            self.view.revision.setText('')
            self.view.commit_text.setText('')
            return
        directories = self.model.get_directories()
        directory_entries = self.model.get_directory_entries()
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
            if idx >= len(self.model.get_subtree_sha1s()):
                # This can happen when changing directories
                self.filename = None
                return
            objtype, sha1, name = self.model.get_subtree_node(idx)

            curdir = self.model.get_directory()
            if curdir:
                self.filename = os.path.join(curdir, name)
            else:
                self.filename = name

            catguts = self.model.git.cat_file(objtype, sha1,
                                              with_raw_output=True)
            self.view.commit_text.setText(catguts)

            self.view.revision.setText(sha1)
            self.view.revision.selectAll()

            # Copy the sha1 into the clipboard
            qtutils.set_clipboard(sha1)

    def item_double_clicked(self,*rest):
        """This is called when an entry is double-clicked.
        This callback changes the model's directory when
        invoked on a directory item.  When invoked on a file
        it allows the file to be saved."""

        current = self.view.commit_list.currentRow()
        directories = self.model.get_directories()

        # A file item was double-clicked.
        # Create a save-as dialog and export the file,
        # or if in get_file mode, grab the filename and finish the dialog.
        if current >= len(directories):
            idx = current - len(directories)

            objtype, sha1, name = self.model.get_subtree_node(idx)

            if self.get_file:
                if self.model.get_directory():
                    curdir = self.model.get_directory()
                    self.filename = os.path.join(curdir, name)
                else:
                    self.filename = name
                self.view.accept()
                return

            nameguess = os.path.join(defaults.DIRECTORY, name)

            filename = qtutils.save_dialog(self.view, 'Save', nameguess)
            if not filename:
                return
            defaults.DIRECTORY = os.path.dirname(filename)
            contents = self.model.cat_file(objtype, sha1, raw=True)

            utils.write(filename, contents)
            return

        dirent = directories[current]
        curdir = self.model.get_directory()

        # '..' is a special case--it doesn't really exist...
        if dirent == '..':
            newdir = os.path.dirname(os.path.dirname(curdir))
            if newdir == '':
                self.model.set_directory(newdir)
            else:
                self.model.set_directory(newdir + os.sep)
        else:
            self.model.set_directory(curdir + dirent)

    ######################################################################

    def __display_items(self):
        """This method populates the commit_list(aka item list)
        with the current directories and items.  Directories are
        always listed first."""

        self.view.commit_text.setText('')
        self.view.revision.setText('')

        dir_icon = utils.get_icon('dir.png')
        file_icon = utils.get_icon('generic.png')
        creator = qtutils.create_listwidget_item

        qtutils.set_items(self.view.commit_list,
                          map(lambda d: creator(d, dir_icon),
                              self.model.get_directories()))

        qtutils.add_items(self.view.commit_list,
                          map(lambda s: creator(s, file_icon),
                              self.model.get_subtree_names()))
