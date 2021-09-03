from __future__ import absolute_import, division, print_function, unicode_literals
from binascii import unhexlify
import copy
import fnmatch
import os
from os.path import join
import re
import struct

from . import core
from . import observable
from . import utils
from . import version
from .compat import int_types
from .git import STDOUT
from .compat import ustr

BUILTIN_READER = os.environ.get('GIT_COLA_BUILTIN_CONFIG_READER', False)

_USER_CONFIG = core.expanduser(join('~', '.gitconfig'))
_USER_XDG_CONFIG = core.expanduser(
    join(core.getenv('XDG_CONFIG_HOME', join('~', '.config')), 'git', 'config')
)


def create(context):
    """Create GitConfig instances"""
    return GitConfig(context)


def _stat_info(git):
    # Try /etc/gitconfig as a fallback for the system config
    paths = [
        ('system', '/etc/gitconfig'),
        ('user', _USER_XDG_CONFIG),
        ('user', _USER_CONFIG),
    ]
    config = git.git_path('config')
    if config:
        paths.append(('repo', config))

    statinfo = []
    for category, path in paths:
        try:
            statinfo.append((category, path, core.stat(path).st_mtime))
        except OSError:
            continue
    return statinfo


def _cache_key(git):
    # Try /etc/gitconfig as a fallback for the system config
    paths = [
        '/etc/gitconfig',
        _USER_XDG_CONFIG,
        _USER_CONFIG,
    ]
    config = git.git_path('config')
    if config:
        paths.append(config)

    mtimes = []
    for path in paths:
        try:
            mtimes.append(core.stat(path).st_mtime)
        except OSError:
            continue
    return mtimes


def _config_to_python(v):
    """Convert a Git config string into a Python value"""
    if v in ('true', 'yes'):
        v = True
    elif v in ('false', 'no'):
        v = False
    else:
        try:
            v = int(v)  # pylint: disable=redefined-variable-type
        except ValueError:
            pass
    return v


def unhex(value):
    """Convert a value (int or hex string) into bytes"""
    if isinstance(value, int_types):
        # If the value is an integer then it's a value that was converted
        # by the config reader.  Zero-pad it into a 6-digit hex number.
        value = '%06d' % value
    return unhexlify(core.encode(value.lstrip('#')))


def _config_key_value(line, splitchar):
    """Split a config line into a (key, value) pair"""

    try:
        k, v = line.split(splitchar, 1)
    except ValueError:
        # the user has an empty entry in their git config,
        # which Git interprets as meaning "true"
        k = line
        v = 'true'
    return k, _config_to_python(v)


class GitConfig(observable.Observable):
    """Encapsulate access to git-config values."""

    message_user_config_changed = 'user_config_changed'
    message_repo_config_changed = 'repo_config_changed'
    message_updated = 'updated'

    def __init__(self, context):
        observable.Observable.__init__(self)
        self.git = context.git
        self._map = {}
        self._system = {}
        self._user = {}
        self._user_or_system = {}
        self._repo = {}
        self._all = {}
        self._cache_key = None
        self._configs = []
        self._config_files = {}
        self._attr_cache = {}
        self._binary_cache = {}
        self._find_config_files()

    def reset(self):
        self._cache_key = None
        self._configs = []
        self._config_files.clear()
        self._attr_cache = {}
        self._binary_cache = {}
        self._find_config_files()
        self.reset_values()

    def reset_values(self):
        self._map.clear()
        self._system.clear()
        self._user.clear()
        self._user_or_system.clear()
        self._repo.clear()
        self._all.clear()

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
        statinfo = _stat_info(self.git)
        self._configs = [x[1] for x in statinfo]
        self._config_files = {}
        for (cat, path, _) in statinfo:
            self._config_files[cat] = path

    def _cached(self):
        """
        Return True when the cache matches.

        Updates the cache and returns False when the cache does not match.

        """
        cache_key = _cache_key(self.git)
        if self._cache_key is None or cache_key != self._cache_key:
            self._cache_key = cache_key
            return False
        return True

    def update(self):
        """Read git config value into the system, user and repo dicts."""
        if self._cached():
            return

        self.reset_values()

        if 'system' in self._config_files:
            self._system.update(self.read_config(self._config_files['system']))

        if 'user' in self._config_files:
            self._user.update(self.read_config(self._config_files['user']))

        if 'repo' in self._config_files:
            self._repo.update(self.read_config(self._config_files['repo']))

        for dct in (self._system, self._user):
            self._user_or_system.update(dct)

        for dct in (self._system, self._user, self._repo):
            self._all.update(dct)

        self.notify_observers(self.message_updated)

    def read_config(self, path):
        """Return git config data from a path as a dictionary."""

        if BUILTIN_READER:
            return self._read_config_file(path)

        dest = {}
        if version.check_git(self, 'config-includes'):
            args = ('--null', '--file', path, '--list', '--includes')
        else:
            args = ('--null', '--file', path, '--list')
        config_lines = self.git.config(*args)[STDOUT].split('\0')
        for line in config_lines:
            if not line:
                # the user has an invalid entry in their git config
                continue
            k, v = _config_key_value(line, '\n')
            self._map[k.lower()] = k
            dest[k] = v
        return dest

    def _read_config_file(self, path):
        """Read a .gitconfig file into a dict"""

        config = {}
        header_simple = re.compile(r'^\[(\s+)]$')
        header_subkey = re.compile(r'^\[(\s+) "(\s+)"\]$')

        with core.xopen(path, 'rt') as f:
            file_lines = f.readlines()

        stripped_lines = [line.strip() for line in file_lines]
        lines = [line for line in stripped_lines if bool(line)]
        prefix = ''
        for line in lines:
            if line.startswith('#'):
                continue

            match = header_simple.match(line)
            if match:
                prefix = match.group(1) + '.'
                continue
            match = header_subkey.match(line)
            if match:
                prefix = match.group(1) + '.' + match.group(2) + '.'
                continue

            k, v = _config_key_value(line, '=')
            k = prefix + k
            self._map[k.lower()] = k
            config[k] = v

        return config

    def _get(self, src, key, default, fn=None, cached=True):
        if not cached or not src:
            self.update()
        try:
            value = self._get_with_fallback(src, key)
        except KeyError:
            if fn:
                value = fn()
            else:
                value = default
        return value

    def _get_with_fallback(self, src, key):
        try:
            return src[key]
        except KeyError:
            pass
        key = self._map.get(key.lower(), key)
        try:
            return src[key]
        except KeyError:
            pass
        # Allow the final KeyError to bubble up
        return src[key.lower()]

    def get(self, key, default=None, fn=None, cached=True):
        """Return the string value for a config key."""
        return self._get(self._all, key, default, fn=fn, cached=cached)

    def get_all(self, key):
        """Return all values for a key sorted in priority order

        The purpose of this function is to group the values returned by
        `git config --show-origin --get-all` so that the relative order is
        preserved but can still be overridden at each level.

        One use case is the `cola.icontheme` variable, which is an ordered
        list of icon themes to load.  This value can be set both in
        ~/.gitconfig as well as .git/config, and we want to allow a
        relative order to be defined in either file.

        The problem is that git will read the system /etc/gitconfig,
        global ~/.gitconfig, and then the local .git/config settings
        and return them in that order, so we must post-process them to
        get them in an order which makes sense for use for our values.
        Otherwise, we cannot replace the order, or make a specific theme used
        first, in our local .git/config since the native order returned by
        git will always list the global config before the local one.

        get_all() allows for this use case by gathering all of the per-config
        values separately and then orders them according to the expected
        local > global > system order.

        """
        result = []
        status, out, _ = self.git.config(key, z=True, get_all=True, show_origin=True)
        if status == 0:
            current_source = ''
            current_result = []
            partial_results = []
            items = [x for x in out.rstrip(chr(0)).split(chr(0)) if x]
            for i in range(len(items) // 2):
                source = items[i * 2]
                value = items[i * 2 + 1]
                if source != current_source:
                    current_source = source
                    current_result = []
                    partial_results.append(current_result)
                current_result.append(value)
            # Git's results are ordered System, Global, Local.
            # Reverse the order here so that Local has the highest priority.
            for partial_result in reversed(partial_results):
                result.extend(partial_result)

        return result

    def get_user(self, key, default=None):
        return self._get(self._user, key, default)

    def get_repo(self, key, default=None):
        return self._get(self._repo, key, default)

    def get_user_or_system(self, key, default=None):
        return self._get(self._user_or_system, key, default)

    def set_user(self, key, value):
        if value in (None, ''):
            self.git.config('--global', key, unset=True)
        else:
            self.git.config('--global', key, python_to_git(value))
        self.update()
        msg = self.message_user_config_changed
        self.notify_observers(msg, key, value)

    def set_repo(self, key, value):
        if value in (None, ''):
            self.git.config(key, unset=True)
        else:
            self.git.config(key, python_to_git(value))
        self.update()
        msg = self.message_repo_config_changed
        self.notify_observers(msg, key, value)

    def find(self, pat):
        pat = pat.lower()
        match = fnmatch.fnmatch
        result = {}
        if not self._all:
            self.update()
        for key, val in self._all.items():
            if match(key.lower(), pat):
                result[key] = val
        return result

    def is_annex(self):
        """Return True when git-annex is enabled"""
        return bool(self.get('annex.uuid', default=False))

    def gui_encoding(self):
        return self.get('gui.encoding', default=None)

    def is_per_file_attrs_enabled(self):
        return self.get(
            'cola.fileattributes', fn=lambda: os.path.exists('.gitattributes')
        )

    def is_binary(self, path):
        """Return True if the file has the binary attribute set"""
        if not self.is_per_file_attrs_enabled():
            return None
        cache = self._binary_cache
        try:
            value = cache[path]
        except KeyError:
            value = cache[path] = self._is_binary(path)
        return value

    def _is_binary(self, path):
        """Return the file encoding for a path"""
        value = self.check_attr('binary', path)
        return value == 'set'

    def file_encoding(self, path):
        if not self.is_per_file_attrs_enabled():
            return self.gui_encoding()
        cache = self._attr_cache
        try:
            value = cache[path]
        except KeyError:
            value = cache[path] = self._file_encoding(path) or self.gui_encoding()
        return value

    def _file_encoding(self, path):
        """Return the file encoding for a path"""
        encoding = self.check_attr('encoding', path)
        if encoding in ('unspecified', 'unset', 'set'):
            result = None
        else:
            result = encoding
        return result

    def check_attr(self, attr, path):
        """Check file attributes for a path"""
        value = None
        status, out, _ = self.git.check_attr(attr, '--', path)
        if status == 0:
            header = '%s: %s: ' % (path, attr)
            if out.startswith(header):
                value = out[len(header) :].strip()
        return value

    def get_guitool_opts(self, name):
        """Return the guitool.<name> namespace as a dict

        The dict keys are simplified so that "guitool.$name.cmd" is accessible
        as `opts[cmd]`.

        """
        prefix = len('guitool.%s.' % name)
        guitools = self.find('guitool.%s.*' % name)
        return dict([(key[prefix:], value) for (key, value) in guitools.items()])

    def get_guitool_names(self):
        guitools = self.find('guitool.*.cmd')
        prefix = len('guitool.')
        suffix = len('.cmd')
        return sorted([name[prefix:-suffix] for (name, _) in guitools.items()])

    def get_guitool_names_and_shortcuts(self):
        """Return guitool names and their configured shortcut"""
        names = self.get_guitool_names()
        return [(name, self.get('guitool.%s.shortcut' % name)) for name in names]

    def terminal(self):
        term = self.get('cola.terminal', default=None)
        if not term:
            # find a suitable default terminal
            term = 'xterm -e'  # for mac osx
            if utils.is_win32():
                # Try to find Git's sh.exe directory in
                # one of the typical locations
                pf = os.environ.get('ProgramFiles', 'C:\\Program Files')
                pf32 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
                pf64 = os.environ.get('ProgramW6432', 'C:\\Program Files')

                for p in [pf64, pf32, pf, 'C:\\']:
                    candidate = os.path.join(p, 'Git\\bin\\sh.exe')
                    if os.path.isfile(candidate):
                        return candidate
                return None
            else:
                candidates = ('xfce4-terminal', 'konsole', 'gnome-terminal')
                for basename in candidates:
                    if core.exists('/usr/bin/%s' % basename):
                        if basename == 'gnome-terminal':
                            term = '%s --' % basename
                        else:
                            term = '%s -e' % basename
                        break
        return term

    def color(self, key, default):
        value = self.get('cola.color.%s' % key, default=default)
        struct_layout = core.encode('BBB')
        try:
            # pylint: disable=no-member
            r, g, b = struct.unpack(struct_layout, unhex(value))
        except (struct.error, TypeError):
            # pylint: disable=no-member
            r, g, b = struct.unpack(struct_layout, unhex(default))
        return (r, g, b)

    def hooks(self):
        """Return the path to the git hooks directory"""
        gitdir_hooks = self.git.git_path('hooks')
        return self.get('core.hookspath', default=gitdir_hooks)

    def hooks_path(self, *paths):
        """Return a path from within the git hooks directory"""
        return os.path.join(self.hooks(), *paths)


def python_to_git(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int_types):
        return ustr(value)
    return value
