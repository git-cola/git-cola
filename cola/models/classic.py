import os

from cola import utils
from cola.models.main import MainModel


class ClassicModel(MainModel):
    """Defines data used by the classic view."""
    message_paths_staged   = 'paths_staged'
    message_paths_unstaged = 'paths_unstaged'

    def __init__(self):
        MainModel.__init__(self)
        self.use_worktree(os.getcwd())
        self.update_status()

    def stage_paths(self, paths):
        """Adds paths to git and notifies observers."""
        self.update_status()
        self.git.add('--', *paths)

        paths = set(paths)

        # Grab the old lists of untracked + modified files
        old_modified = set(self.modified)
        old_untracked = set(self.untracked)

        # Rescan for new changes
        self.update_status()

        # Grab the new lists of untracked + modified files
        new_modified = set(self.modified)
        new_untracked = set(self.untracked)

        # Handle 'git add' on a directory
        newly_not_modified = utils.add_parents(old_modified - new_modified)
        newly_not_untracked = utils.add_parents(old_untracked - new_untracked)

        for path in newly_not_modified.union(newly_not_untracked):
            paths.add(path)

        self.notify_message_observers(self.message_paths_staged, paths=paths)

    def unstage_paths(self, paths):
        """Unstages paths from the staging area and notifies observers."""
        self.update_status()
        self.reset_helper(paths)

        paths = set(paths)

        # Grab the old list of staged files
        old_staged = set(self.staged)

        # Rescan for new changes
        self.update_status()

        # Grab the new list of staged file
        new_staged = set(self.staged)

        # Handle 'git reset' on a directory
        newly_unstaged = utils.add_parents(old_staged - new_staged)

        for path in newly_unstaged:
            paths.add(path)

        self.notify_message_observers(self.message_paths_unstaged, paths=paths)


    def everything(self):
        """Returns a sorted list of all files, including untracked files."""
        files = self.all_files() + self.untracked
        files.sort()
        return files
