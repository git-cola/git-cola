import os
import sys
import copy

from cola import core
from cola import gitcmd
from cola import utils


_config = None
def instance():
    """Return a static GitConfig instance."""
    global _config
    if not _config:
        _config = GitConfig()
    return _config


def _find_in_path(app):
    """Find a program in $PATH."""
    is_win32 = sys.platform == 'win32'
    for path in os.environ.get('PATH', '').split(os.pathsep):
        candidate = os.path.join(path, app)
        if os.path.exists(candidate):
            return candidate
        if is_win32:
            candidate = os.path.join(path, app + '.exe')
            if os.path.exists(candidate):
                return candidate
    return None


class GitConfig(object):
    """Encapsulate access to git-config values."""

    def __init__(self):
        self.git = gitcmd.instance()
        self._system = {}
        self._user = {}
        self._repo = {}
        self._cache_key = None
        self._configs = []
        self._config_files = {}
        self._find_config_files()

    def reset(self):
        self._system = {}
        self._user = {}
        self._repo = {}
        self._configs = []
        self._config_files = {}
        self._find_config_files()

    def user(self):
        return copy.deepcopy(self._user)

    def repo(self):
        return copy.deepcopy(self._repo)

    def _find_config_files(self):
        """
        Classify git config files into 'system', 'user', and 'repo'.

        Populates self._configs with a list of the files in
        reverse-precedence order.  self._config_files is populated with
        {category: path} where category is one of 'system', 'user', or 'repo'.

        """
        # Try the git config in git's installation prefix
        git_path = _find_in_path('git')
        if git_path:
            bin_dir = os.path.dirname(git_path)
            prefix = os.path.dirname(bin_dir)
            system_config = os.path.join(prefix, 'etc', 'gitconfig')
            if os.path.exists(system_config):
                self._config_files['system'] = system_config
                self._configs.append(system_config)

        # Try /etc/gitconfig as a fallback for the system config
        if 'system' not in self._config_files:
            system_config = '/etc/gitconfig'
            if os.path.exists(system_config):
                self._config_files['system'] = system_config
                self._configs.append(system_config)

        # Check for the user config
        user_config = os.path.expanduser('~/.gitconfig')
        if os.path.exists(user_config):
            self._config_files['user'] = user_config
            self._configs.append(user_config)

        # Check for the repo config
        repo_config = self.git.git_path('config')
        if os.path.exists(repo_config):
            self._config_files['repo'] = repo_config
            self._configs.append(repo_config)

    def update(self):
        """Read config values from git."""
        if self._cached():
            return
        self._read_configs()

    def _cached(self):
        """
        Return True when the cache matches.

        Updates the cache and returns False when the cache does not match.

        """
        cache_key = map(lambda x: os.stat(x).st_mtime, self._configs)
        if not self._cache_key or cache_key != self._cache_key:
            self._cache_key = cache_key
            return False
        return True

    def _read_configs(self):
        """Read git config value into the system, user and repo dicts."""
        self._system = {}
        self._user = {}
        self._repo = {}

        if 'system' in self._config_files:
            self._system = self.read_config(self._config_files['system'])

        if 'user' in self._config_files:
            self._user = self.read_config(self._config_files['user'])

        if 'repo' in self._config_files:
            self._repo = self.read_config(self._config_files['repo'])

    def read_config(self, path):
        """Return git config data from a path as a dictionary."""
        dest = {}
        args = ('--null', '--file', path, '--list')
        config_lines = self.git.config(*args).split('\0')
        for line in config_lines:
            try:
                k, v = line.split('\n')
            except:
                # the user has an invalid entry in their git config
                continue
            v = core.decode(v)
            if v == 'true' or v == 'false':
                v = bool(eval(v.title()))
            try:
                v = int(eval(v))
            except:
                pass
            dest[k] = v
        return dest

    def get(self, key, default=None):
        """Return the string value for a config key."""
        self.update()
        for dct in (self._repo, self._user, self._system):
            if key in dct:
                return dct[key]
        return default
