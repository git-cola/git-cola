import re

import cola
from cola import gitcmds
from cola.models import observable


class BrowserModel(observable.ObservableModel):
    def __init__(self, branch=None):
        observable.ObservableModel.__init__(self)
        self.copy_params(cola.model())
        if branch:
            self.currentbranch = branch

        # These are parallel lists
        # ref^{tree}
        self.types = []
        self.sha1s = []
        self.names = []

        self.directories = []
        self.directory_entries = {}

        # parallel lists
        self.subtree_types = []
        self.subtree_sha1s = []
        self.subtree_names = []

    def init_browser_data(self):
        """This scans over self.(names, sha1s, types) to generate
        directories, directory_entries, and subtree_*"""

        # Collect data for the model
        if not self.currentbranch:
            return

        self.subtree_types = []
        self.subtree_sha1s = []
        self.subtree_names = []
        self.directories = []
        self.directory_entries = {}

        # Lookup the tree info
        tree_info = gitcmds.parse_ls_tree(self.currentbranch)

        self.set_types(map(lambda(x): x[1], tree_info ))
        self.set_sha1s(map(lambda(x): x[2], tree_info ))
        self.set_names(map(lambda(x): x[3], tree_info ))

        if self.directory:
            self.directories.append('..')

        dir_entries = self.directory_entries
        dir_regex = re.compile('([^/]+)/')
        dirs_seen = {}
        subdirs_seen = {}

        for idx, name in enumerate(self.names):
            if not name.startswith(self.directory):
                continue
            name = name[ len(self.directory): ]
            if name.count('/'):
                # This is a directory...
                match = dir_regex.match(name)
                if not match:
                    continue
                dirent = match.group(1) + '/'
                if dirent not in self.directory_entries:
                    self.directory_entries[dirent] = []

                if dirent not in dirs_seen:
                    dirs_seen[dirent] = True
                    self.directories.append(dirent)

                entry = name.replace(dirent, '')
                entry_match = dir_regex.match(entry)
                if entry_match:
                    subdir = entry_match.group(1) + '/'
                    if subdir in subdirs_seen:
                        continue
                    subdirs_seen[subdir] = True
                    dir_entries[dirent].append(subdir)
                else:
                    dir_entries[dirent].append(entry)
            else:
                self.subtree_types.append(self.types[idx])
                self.subtree_sha1s.append(self.sha1s[idx])
                self.subtree_names.append(name)

    def subtree_node(self, idx):
        return (self.subtree_types[idx],
                self.subtree_sha1s[idx],
                self.subtree_names[idx])
