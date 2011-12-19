import os
import copy
import fnmatch

from cola import core
from cola import git
from cola import observable
from cola.decorators import memoize


@memoize
def instance():
    """Return a static GitConfig instance."""
    return GitConfig()


def _stat_info():
    # Try /etc/gitconfig as a fallback for the system config
    userconfig = os.path.expanduser(os.path.join('~', '.gitconfig'))
    paths = (('system', '/etc/gitconfig'),
             ('user', core.decode(userconfig)),
             ('repo', core.decode(git.instance().git_path('config'))))
    statinfo = []
    for category, path in paths:
        try:
            statinfo.append((category, path, os.stat(path).st_mtime))
        except OSError:
            continue
    return statinfo


def _cache_key():
    # Try /etc/gitconfig as a fallback for the system config
    userconfig = os.path.expanduser(os.path.join('~', '.gitconfig'))
    paths = ('/etc/gitconfig',
             userconfig,
             git.instance().git_path('config'))
    mtimes = []
    for path in paths:
        try:
            mtimes.append(os.stat(path).st_mtime)
        except OSError:
            continue
    return mtimes


class GitConfig(observable.Observable):
    """Encapsulate access to git-config values."""

    message_user_config_changed = 'user_config_changed'
    message_repo_config_changed = 'repo_config_changed'

    def __init__(self):
        observable.Observable.__init__(self)
        self.git = git.instance()
        self._system = {}
        self._user = {}
        self._repo = {}
        self._all = {}
        self._cache_key = None
        self._configs = []
        self._config_files = {}
        self._find_config_files()

    def reset(self):
        self._system = {}
        self._user = {}
        self._repo = {}
        self._all = {}
        self._cache_key = None
        self._configs = []
        self._config_files = {}
        self._find_config_files()

    def user(self):
        return copy.deepcopy(self._user)

    def repo(self):
        return copy.deepcopy(self._repo)

    def all(self):
        return copy.deepcopy(self._all)

    def _find_config_files(self):
        """
        Classify git config files into 'system', 'user', and 'repo'.

        Populates self._configs with a list of the files in
        reverse-precedence order.  self._config_files is populated with
        {category: path} where category is one of 'system', 'user', or 'repo'.

        """
        # Try the git config in git's installation prefix
        statinfo = _stat_info()
        self._configs = map(lambda x: x[1], statinfo)
        self._config_files = {}
        for (cat, path, mtime) in statinfo:
            self._config_files[cat] = path

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
        cache_key = _cache_key()
        if not self._cache_key or cache_key != self._cache_key:
            self._cache_key = cache_key
            return False
        return True

    def _read_configs(self):
        """Read git config value into the system, user and repo dicts."""
        self._system = {}
        self._user = {}
        self._repo = {}
        self._all = {}

        if 'system' in self._config_files:
            self._system = self.read_config(self._config_files['system'])

        if 'user' in self._config_files:
            self._user = self.read_config(self._config_files['user'])

        if 'repo' in self._config_files:
            self._repo = self.read_config(self._config_files['repo'])

        self._all = {}
        for dct in (self._system, self._user, self._repo):
            self._all.update(dct)

    def read_config(self, path):
        """Return git config data from a path as a dictionary."""
        dest = {}
        args = ('--null', '--file', path, '--list')
        config_lines = self.git.config(*args).split('\0')
        for line in config_lines:
            try:
                k, v = line.split('\n', 1)
            except ValueError:
                # the user has an invalid entry in their git config
                if not line:
                    continue
                k = line
                v = 'true'
            v = core.decode(v)

            if v in ('true', 'yes'):
                v = True
            elif v in ('false', 'no'):
                v = False
            else:
                try:
                    v = int(v)
                except ValueError:
                    pass
            dest[k.lower()] = v
        return dest

    def get(self, key, default=None, source=None):
        """Return the string value for a config key."""
        self.update()
        return self._all.get(key, default)

    def get_user(self, key, default=None):
        self.update()
        return self._user.get(key, default)

    def get_repo(self, key, default=None):
        self.update()
        return self._repo.get(key, default)

    def python_to_git(self, value):
        if type(value) is bool:
            if value:
                return 'true'
            else:
                return 'false'
        if type(value) is int:
            return unicode(value)
        return value

    def set_user(self, key, value):
        msg = self.message_user_config_changed
        self.git.config('--global', key, self.python_to_git(value))
        self.update()
        self.notify_observers(msg, key, value)

    def set_repo(self, key, value):
        msg = self.message_repo_config_changed
        self.git.config(key, self.python_to_git(value))
        self.update()
        self.notify_observers(msg, key, value)

    def find(self, pat):
        result = {}
        for key, val in self._all.items():
            if fnmatch.fnmatch(key, pat):
                result[key] = val
        return result

    def get_encoding(self, default='utf-8'):
        return self.get('gui.encoding', default=default)

    guitool_opts = ('cmd', 'needsfile', 'noconsole', 'norescan', 'confirm',
                    'argprompt', 'revprompt', 'revunmerged', 'title', 'prompt')

    def get_guitool_opts(self, name):
        """Return the guitool.<name> namespace as a dict"""
        keyprefix = 'guitool.' + name + '.'
        opts = {}
        for cfg in self.guitool_opts:
            value = self.get(keyprefix + cfg)
            if value is None:
                continue
            opts[cfg] = value
        return opts

    def get_guitool_names(self):
        cmds = []
        guitools = self.find('guitool.*.cmd')
        for name, cmd in guitools.items():
            name = name[len('guitool.'):-len('.cmd')]
            cmds.append(name)
        return cmds
