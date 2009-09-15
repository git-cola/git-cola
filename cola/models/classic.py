import os

import cola
from cola import utils
from cola.models.observable import ObservableModel


# Provides access to a global ClassicModel instance
_instance = None
def model():
    """Returns the main model singleton"""
    global _instance
    if _instance:
        return _instance
    _instance = ClassicModel()
    return _instance


class ClassicModel(ObservableModel):
    """Defines data used by the classic view."""
    message_paths_staged   = 'paths_staged'
    message_paths_unstaged = 'paths_unstaged'
    message_paths_reverted = 'paths_reverted'

    def __init__(self):
        ObservableModel.__init__(self)
        self.model = cola.model()

    def stage_paths(self, paths):
        """Adds paths to git and notifies observers."""

        # Grab the old lists of untracked + modified files
        self.model.update_status()
        old_modified = set(self.model.modified)
        old_untracked = set(self.model.untracked)

        # Add paths and scan for changes
        paths = set(paths)
        self.model.git.add('--', *paths)
        self.model.update_status()

        # Grab the new lists of untracked + modified files
        new_modified = set(self.model.modified)
        new_untracked = set(self.model.untracked)

        # Handle 'git add' on a directory
        newly_not_modified = utils.add_parents(old_modified - new_modified)
        newly_not_untracked = utils.add_parents(old_untracked - new_untracked)
        for path in newly_not_modified.union(newly_not_untracked):
            paths.add(path)

        self.notify_message_observers(self.message_paths_staged, paths=paths)

    def unstage_paths(self, paths):
        """Unstages paths from the staging area and notifies observers."""
        self.model.update_status()
        self.model.reset_helper(paths)

        paths = set(paths)

        # Grab the old list of staged files
        old_staged = set(self.model.staged)

        # Rescan for new changes
        self.model.update_status()

        # Grab the new list of staged file
        new_staged = set(self.model.staged)

        # Handle 'git reset' on a directory
        newly_unstaged = utils.add_parents(old_staged - new_staged)

        for path in newly_unstaged:
            paths.add(path)

        self.notify_message_observers(self.message_paths_unstaged, paths=paths)

    def revert_paths(self, paths):
        """Revert paths to the content from HEAD."""
        self.model.update_status()
        self.model.git.checkout('HEAD', '--', *paths)

        paths = set(paths)

        # Grab the old set of changed files
        old_modified = set(self.model.modified)
        old_staged = set(self.model.staged)
        old_changed = old_modified.union(old_staged)

        # Rescan for new changes
        self.model.update_status()

        # Grab the new set of changed files
        new_modified = set(self.model.modified)
        new_staged = set(self.model.staged)
        new_changed = new_modified.union(new_staged)

        # Handle 'git checkout' on a directory
        newly_reverted = utils.add_parents(old_changed - new_changed)

        for path in newly_reverted:
            paths.add(path)

        self.notify_message_observers(self.message_paths_reverted, paths=paths)
