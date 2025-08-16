from binascii import unhexlify
import collections
import copy
import fnmatch
import os
import struct

try:
    import pwd

    _use_pwd = True
except ImportError:
    _use_pwd = False


from qtpy import QtCore
from qtpy.QtCore import Signal

from . import core
from . import utils
from . import version
from . import resources


def create(context):
    """Create GitConfig instances"""
    return GitConfig(context)


def _cache_key_from_paths(paths):
    """Return a stat cache from the given paths"""
    if not paths:
        return None
    mtimes = []
    for path in sorted(paths):
        try:
            mtimes.append(core.stat(path).st_mtime)
        except OSError:
            continue
    if mtimes:
        return mtimes
    return None


def _config_to_python(value):
    """Convert a Git config string into a Python value"""
    if value in ('true', 'yes'):
        value = True
    elif value in ('false', 'no'):
        value = False
    else:
        try:
            value = int(value)
        except ValueError:
            pass
    return value


def unhex(value):
    """Convert a value (int or hex string) into bytes"""
    if isinstance(value, int):
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


def _append_tab(value):
    """Return a value and the same value with tab appended"""
    return (value, value + '\t')


class GitConfig(QtCore.QObject):
    """Encapsulate access to git-config values."""

    user_config_changed = Signal(str, object)
    repo_config_changed = Signal(str, object)
    updated = Signal()

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.git = context.git
        self._system = {}
        self._global = {}
        self._global_or_system = {}
        self._local = {}
        self._all = {}
        self._renamed_keys = {}
        self._multi_values = collections.defaultdict(list)
        self._cache_key = None
        self._cache_paths = []
        self._attr_cache = {}
        self._binary_cache = {}

    def reset(self):
        self._cache_key = None
        self._cache_paths = []
        self._attr_cache.clear()
        self._binary_cache.clear()
        self.reset_values()

    def reset_values(self):
        self._system.clear()
        self._global.clear()
        self._global_or_system.clear()
        self._local.clear()
        self._all.clear()
        self._renamed_keys.clear()
        self._multi_values.clear()

    def user(self):
        return copy.deepcopy(self._global)

    def repo(self):
        return copy.deepcopy(self._local)

    def all(self):
        return copy.deepcopy(self._all)

    def _is_cached(self):
        """
        Return True when the cache matches.

        Updates the cache and returns False when the cache does not match.

        """
        cache_key = _cache_key_from_paths(self._cache_paths)
        return self._cache_key and cache_key == self._cache_key

    def update(self):
        """Read git config value into the system, user and repo dicts."""
        if self._is_cached():
            return

        self.reset_values()

        show_scope = version.check_git(self.context, 'config-show-scope')
        show_origin = version.check_git(self.context, 'config-show-origin')
        if show_scope:
            reader = _read_config_with_scope
        elif show_origin:
            reader = _read_config_with_origin
        else:
            reader = _read_config_fallback

        unknown_scope = 'unknown'
        system_scope = 'system'
        global_scope = 'global'
        local_scope = 'local'
        worktree_scope = 'worktree'
        cache_paths = set()

        for current_scope, current_key, current_value, continuation in reader(
            self.context, cache_paths, self._renamed_keys
        ):
            # Store the values for fast cached lookup.
            self._all[current_key] = current_value

            # macOS has credential.helper=osxkeychain in the "unknown" scope from
            # /Applications/Xcode.app/Contents/Developer/usr/share/git-core/gitconfig.
            # Treat "unknown" as equivalent to "system" (lowest priority).
            if current_scope in (system_scope, unknown_scope):
                self._system[current_key] = current_value
                self._global_or_system[current_key] = current_value
            elif current_scope == global_scope:
                self._global[current_key] = current_value
                self._global_or_system[current_key] = current_value
            # "worktree" is treated as equivalent to "local".
            elif current_scope in (local_scope, worktree_scope):
                self._local[current_key] = current_value

            # Add this value to the multi-values storage used by get_all().
            # This allows us to handle keys that store multiple values.
            if continuation:
                # If this is a continuation line then we should *not* append to its
                # multi-values list. We should update it in-place.
                self._multi_values[current_key][-1] = current_value
            else:
                self._multi_values[current_key].append(current_value)

        # Update the cache
        self._cache_paths = sorted(cache_paths)
        self._cache_key = _cache_key_from_paths(self._cache_paths)

        # Send a notification that the configuration has been updated.
        self.updated.emit()

    def _get(self, src, key, default, func=None, cached=True):
        if not cached or not src:
            self.update()
        try:
            value = self._get_value(src, key)
        except KeyError:
            if func:
                value = func()
            else:
                value = default
        return value

    def _get_value(self, src, key):
        """Return a value from the map"""
        try:
            return src[key]
        except KeyError:
            pass
        # Try the original key name.
        key = self._renamed_keys.get(key.lower(), key)
        try:
            return src[key]
        except KeyError:
            pass
        # Allow the final KeyError to bubble up
        return src[key.lower()]

    def get(self, key, default=None, func=None, cached=True):
        """Return the string value for a config key."""
        return self._get(self._all, key, default, func=func, cached=cached)

    def get_all(self, key):
        """Return all values for a key sorted in priority order

        The purpose of this function is to group the values returned by
        `git config --show-origin --list` so that the relative order is
        preserved and can be overridden at each level.

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

        get_all() allows for this use case by reading from a defaultdict
        that contains all of the per-config values separately so that the
        caller can order them according to its preferred precedence.
        """
        if not self._multi_values:
            self.update()
        # Check for this key as-is.
        if key in self._multi_values:
            return self._multi_values[key]

        # Check for a renamed version of this key (x.kittycat -> x.kittyCat)
        renamed_key = self._renamed_keys.get(key.lower(), key)
        if renamed_key in self._multi_values:
            return self._multi_values[renamed_key]

        key_lower = key.lower()
        if key_lower in self._multi_values:
            return self._multi_values[key_lower]
        # Nothing found -> empty list.
        return []

    def get_user(self, key, default=None):
        return self._get(self._global, key, default)

    def get_repo(self, key, default=None):
        return self._get(self._local, key, default)

    def get_user_or_system(self, key, default=None):
        return self._get(self._global_or_system, key, default)

    def get_object_format(self):
        """Return the cached repostiory object format (sha256, sha1)"""
        try:
            object_format = self._get_value(self._all, 'extensions.objectformat')
        except KeyError:
            object_format = 'sha1'
        return object_format

    def set_user(self, key, value):
        if value in (None, ''):
            self.git.config('--global', key, unset=True, _readonly=True)
        else:
            self.git.config('--global', key, python_to_git(value), _readonly=True)
        self.update()
        self.user_config_changed.emit(key, value)

    def set_repo(self, key, value):
        if value in (None, ''):
            self.git.config(key, unset=True, _readonly=True)
            self._local.pop(key, None)
        else:
            self.git.config(key, python_to_git(value), _readonly=True)
            self._local[key] = value
        self.updated.emit()
        self.repo_config_changed.emit(key, value)

    def find(self, pat):
        """Return a dict of values for all keys matching the specified pattern"""
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
            'cola.fileattributes', func=lambda: os.path.exists('.gitattributes')
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
        status, out, _ = self.git.check_attr(attr, '--', path, _readonly=True)
        if status == 0:
            header = f'{path}: {attr}: '
            if out.startswith(header):
                value = out[len(header) :].strip()
        return value

    def get_author(self):
        """Return (name, email) for authoring commits"""
        if _use_pwd:
            user = pwd.getpwuid(os.getuid()).pw_name
        else:
            user = os.getenv('USER', 'unknown')

        name = self.get('user.name', user)
        email = self.get('user.email', f'{user}@{core.node()}')
        return (name, email)

    def get_guitool_opts(self, name):
        """Return the guitool.<name> namespace as a dict

        The dict keys are simplified so that "guitool.$name.cmd" is accessible
        as `opts[cmd]`.

        """
        guitools = self.find(f'guitool.{name}.*')
        return utils.strip_prefixes_from_keys(guitools, f'guitool.{name}.')

    def get_guitool_names(self):
        """Return guitool names"""
        guitools = self.find('guitool.*.cmd')
        return utils.strip_prefixes_and_suffixes(guitools, 'guitool.', '.cmd')

    def get_guitool_names_and_shortcuts(self):
        """Return guitool names and their configured shortcut"""
        names = self.get_guitool_names()
        return [(name, self.get(f'guitool.{name}.shortcut')) for name in names]

    def terminal(self):
        """Return a suitable terminal command for running a shell"""
        term = self.get('cola.terminal', default=None)
        if term:
            return term

        # find a suitable default terminal
        if utils.is_win32():
            # Try to find Git's sh.exe directory in
            # one of the typical locations
            pf = os.environ.get('ProgramFiles', r'C:\Program Files')
            pf32 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
            pf64 = os.environ.get('ProgramW6432', r'C:\Program Files')

            for p in [pf64, pf32, pf, 'C:\\']:
                candidate = os.path.join(p, r'Git\bin\sh.exe')
                if os.path.isfile(candidate):
                    return candidate
            return None

        # If no terminal has been configured then we'll look for the following programs
        # and use the first one we find.
        terminals = (
            # (<executable>, <command> for running arbitrary commands)
            ('kitty', 'kitty'),
            ('alacritty', 'alacritty -e'),
            ('uxterm', 'uxterm -e'),
            ('konsole', 'konsole -e'),
            ('gnome-terminal', 'gnome-terminal --'),
            ('mate-terminal', 'mate-terminal --'),
            ('xterm', 'xterm -e'),
        )
        for executable, command in terminals:
            if core.find_executable(executable):
                return command
        return None

    def color(self, key, default):
        value = self.get('cola.color.%s' % key, default=default)
        struct_layout = core.encode('BBB')
        try:
            red, green, blue = struct.unpack(struct_layout, unhex(value))
        except (struct.error, TypeError):
            red, green, blue = struct.unpack(struct_layout, unhex(default))
        return (red, green, blue)

    def hooks(self):
        """Return the path to the git hooks directory"""
        gitdir_hooks = self.git.git_path('hooks')
        return self.get('core.hookspath', default=gitdir_hooks)

    def hooks_path(self, *paths):
        """Return a path from within the git hooks directory"""
        return os.path.join(self.hooks(), *paths)


def _read_config_with_scope(context, cache_paths, renamed_keys):
    """Read the output from "git config --show-scope --show-origin --list

    ``--show-scope`` was introduced in Git v2.26.0.
    """
    unknown_key = 'unknown\t'
    system_key = 'system\t'
    global_key = 'global\t'
    local_key = 'local\t'
    worktree_key = 'worktree\t'
    command_scope, command_key = _append_tab('command')
    command_line = 'command line:'
    file_scheme = 'file:'

    current_value = ''
    current_key = ''
    current_scope = ''
    current_path = ''

    status, config_output, _ = context.git.config(
        show_origin=True, show_scope=True, list=True, includes=True
    )
    if status != 0:
        return

    for line in config_output.splitlines():
        if not line:
            continue
        if (
            line.startswith(system_key)
            or line.startswith(global_key)
            or line.startswith(local_key)
            or line.startswith(command_key)
            or line.startswith(worktree_key)  # worktree and unknown are uncommon.
            or line.startswith(unknown_key)
        ):
            continuation = False
            current_scope, current_path, rest = line.split('\t', 2)
            if current_scope == command_scope:
                continue
            current_key, current_value = _config_key_value(rest, '=')
            if current_path.startswith(file_scheme):
                cache_paths.add(current_path[len(file_scheme) :])
            elif current_path == command_line:
                continue
            renamed_keys[current_key.lower()] = current_key
        else:
            # Values are allowed to span multiple lines when \n is embedded
            # in the value. Detect this and append to the previous value.
            continuation = True
            if current_value and isinstance(current_value, str):
                current_value += '\n'
                current_value += line
            else:
                current_value = line

        yield current_scope, current_key, current_value, continuation


def _read_config_with_origin(context, cache_paths, renamed_keys):
    """Read the output from "git config --show-origin --list

    ``--show-origin`` was introduced in Git v2.8.0.
    """
    command_line = 'command line:\t'
    system_scope = 'system'
    global_scope = 'global'
    local_scope = 'local'
    file_scheme = 'file:'

    system_scope_id = 0
    global_scope_id = 1
    local_scope_id = 2

    current_value = ''
    current_key = ''
    current_path = ''
    current_scope = system_scope
    current_scope_id = system_scope_id

    status, config_output, _ = context.git.config(
        show_origin=True, list=True, includes=True
    )
    if status != 0:
        return

    for line in config_output.splitlines():
        if not line or line.startswith(command_line):
            continue
        try:
            tab_index = line.index('\t')
        except ValueError:
            tab_index = 0
        if line.startswith(file_scheme) and tab_index > 5:
            continuation = False
            current_path = line[:tab_index]
            rest = line[tab_index + 1 :]

            cache_paths.add(current_path)
            current_key, current_value = _config_key_value(rest, '=')
            renamed_keys[current_key.lower()] = current_key

            # The valid state machine transitions are system -> global,
            # system -> local and global -> local. We start from the system state.
            basename = os.path.basename(current_path)
            if current_scope_id == system_scope_id and basename == '.gitconfig':
                # system -> global
                current_scope_id = global_scope_id
                current_scope = global_scope
            elif current_scope_id < local_scope_id and basename == 'config':
                # system -> local, global -> local
                current_scope_id = local_scope_id
                current_scope = local_scope
        else:
            # Values are allowed to span multiple lines when \n is embedded
            # in the value. Detect this and append to the previous value.
            continuation = True
            if current_value and isinstance(current_value, str):
                current_value += '\n'
                current_value += line
            else:
                current_value = line

        yield current_scope, current_key, current_value, continuation


def _read_config_fallback(context, cache_paths, renamed_keys):
    """Fallback config reader for Git < 2.8.0"""
    system_scope = 'system'
    global_scope = 'global'
    local_scope = 'local'
    includes = version.check_git(context, 'config-includes')

    current_path = '/etc/gitconfig'
    if os.path.exists(current_path):
        cache_paths.add(current_path)
        status, config_output, _ = context.git.config(
            z=True,
            list=True,
            includes=includes,
            system=True,
        )
        if status == 0:
            for key, value in _read_config_from_null_list(config_output):
                renamed_keys[key.lower()] = key
                yield system_scope, key, value, False

    gitconfig_home = core.expanduser(os.path.join('~', '.gitconfig'))
    gitconfig_xdg = resources.xdg_config_home('git', 'config')

    if os.path.exists(gitconfig_home):
        gitconfig = gitconfig_home
    elif os.path.exists(gitconfig_xdg):
        gitconfig = gitconfig_xdg
    else:
        gitconfig = None

    if gitconfig:
        cache_paths.add(gitconfig)
        status, config_output, _ = context.git.config(
            z=True, list=True, includes=includes, **{'global': True}
        )
        if status == 0:
            for key, value in _read_config_from_null_list(config_output):
                renamed_keys[key.lower()] = key
                yield global_scope, key, value, False

    local_config = context.git.git_path('config')
    if local_config and os.path.exists(local_config):
        cache_paths.add(gitconfig)
        status, config_output, _ = context.git.config(
            z=True,
            list=True,
            includes=includes,
            local=True,
        )
        if status == 0:
            for key, value in _read_config_from_null_list(config_output):
                renamed_keys[key.lower()] = key
                yield local_scope, key, value, False


def _read_config_from_null_list(config_output):
    """Parse the "git config --list -z" records"""
    for record in config_output.rstrip('\0').split('\0'):
        try:
            name, value = record.split('\n', 1)
        except ValueError:
            name = record
            value = 'true'
        yield (name, _config_to_python(value))


def python_to_git(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    return value


def get_remotes(cfg):
    """Get all of the configured git remotes"""
    # Gather all of the remote.*.url entries.
    values = cfg.find('remote.*.url')
    return utils.strip_prefixes_and_suffixes_from_keys(values, 'remote.', '.url')
