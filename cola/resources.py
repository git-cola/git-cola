"""Functions for finding cola resources"""
import os
import sys
import webbrowser

from . import core
from . import compat


# Default git-cola icon theme
_default_icon_theme = 'light'

_resources = core.abspath(core.realpath(__file__))
_package = os.path.dirname(_resources)

if _package.endswith(os.path.join('site-packages', 'cola')):
    # Unix release tree
    # __file__ = '$prefix/lib/pythonX.Y/site-packages/cola/__file__.py'
    # _package = '$prefix/lib/pythonX.Y/site-packages/cola'
    _prefix = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(_package)))
    )
elif _package.endswith(os.path.join('pkgs', 'cola')):
    # Windows release tree
    # __file__ = $installdir/pkgs/cola
    _prefix = os.path.dirname(os.path.dirname(_package))
else:
    # this is the source tree
    # __file__ = '$prefix/cola/__file__.py'
    _prefix = os.path.dirname(_package)


def get_prefix():
    """Return the installation prefix"""
    return _prefix


def prefix(*args):
    """Return a path relative to cola's installation prefix"""
    return os.path.join(get_prefix(), *args)


def sibling_bindir(*args):
    """Return a command sibling to sys.argv[0]"""
    relative_bindir = os.path.dirname(sys.argv[0])
    return os.path.join(relative_bindir, *args)


def command(name):
    """Return a command from the bin/ directory"""
    if compat.WIN32:
        # On Windows we have to support being installed via the pynsist installation
        # layout and the pip-installed layout. We also have check for .exe launchers
        # and prefer them when present.
        sibling = sibling_bindir(name)
        scripts = prefix('Scripts', name)
        bindir = prefix('bin', name)
        # Check for "${name}.exe" on Windows.
        exe = f'{name}.exe'
        sibling_exe = sibling_bindir(exe)
        scripts_exe = prefix('Scripts', exe)
        bindir_exe = prefix('bin', exe)
        if core.exists(sibling_exe):
            result = sibling_exe
        elif core.exists(sibling):
            result = sibling
        elif core.exists(bindir_exe):
            result = bindir_exe
        elif core.exists(scripts_exe):
            result = scripts_exe
        elif core.exists(scripts):
            result = scripts
        else:
            result = bindir
    else:
        result = sibling_bindir(name)
        if not core.exists(result):
            result = prefix('bin', name)

    return result


def doc(*args):
    """Return a path relative to cola's /usr/share/doc/ or the docs/ directory"""
    # pyproject.toml does not support data_files in pyproject.toml so we install the
    # hotkey files as cola/data/ package data. This is a fallback location for when
    # users did not use the garden.yaml or Makefile to install cola.
    path = share('doc', 'git-cola', *args)
    if not os.path.exists(path):
        path = prefix('docs', *args)
    return path


def i18n(*args):
    """Return a path relative to cola's i18n locale directory, e.g. cola/i18n"""
    return package_data('i18n', *args)


def html_docs():
    """Return the path to the cola html documentation."""
    # html/index.html only exists after the install-docs target is run.
    # Fallback to the source tree and lastly git-cola.rst.
    paths_to_try = (('html', 'index.html'), ('_build', 'html', 'index.html'))
    for paths in paths_to_try:
        docdir = doc(*paths)
        if core.exists(docdir):
            return docdir
    return doc('git-cola.rst')


def show_html_docs():
    """Open the HTML documentation in a browser"""
    url = html_docs()
    webbrowser.open_new_tab('file://' + url)


def share(*args):
    """Return a path relative to cola's /usr/share/ directory"""
    return prefix('share', *args)


def package_data(*args):
    """Return a path relative to cola's Python modules"""
    return os.path.join(_package, *args)


def data_path(*args):
    """Return a path relative to cola's data directory"""
    return package_data('data', *args)


def icon_path(*args):
    """Return a path relative to cola's icons directory"""
    return package_data('icons', *args)


def package_command(*args):
    """Return a path relative to cola's private bin/ directory"""
    return package_data('bin', *args)


def icon_dir(theme):
    """Return the icons directory for the specified theme

    This returns the ``icons`` directory inside the ``cola`` Python package.
    When theme is defined then it will return a subdirectory of the icons/
    directory, e.g. "dark" for the dark icon theme.

    When theme is set to an absolute directory path, that directory will be
    returned, which effectively makes git-cola use those icons.
    """
    if not theme or theme == _default_icon_theme:
        icons = package_data('icons')
    else:
        theme_dir = package_data('icons', theme)
        if os.path.isabs(theme) and os.path.isdir(theme):
            icons = theme
        elif os.path.isdir(theme_dir):
            icons = theme_dir
        else:
            icons = package_data('icons')

    return icons


def xdg_config_home(*args):
    """Return the XDG_CONFIG_HOME configuration directory, eg. ~/.config"""
    config = core.getenv(
        'XDG_CONFIG_HOME', os.path.join(core.expanduser('~'), '.config')
    )
    return os.path.join(config, *args)


def xdg_data_home(*args):
    """Return the XDG_DATA_HOME configuration directory, e.g. ~/.local/share"""
    config = core.getenv(
        'XDG_DATA_HOME', os.path.join(core.expanduser('~'), '.local', 'share')
    )
    return os.path.join(config, *args)


def xdg_data_dirs():
    """Return the current set of XDG data directories

    Returns the values from $XDG_DATA_DIRS when defined in the environment.
    If $XDG_DATA_DIRS is either not set or empty, a value equal to
    /usr/local/share:/usr/share is used.
    """
    paths = []
    xdg_data_home_dir = xdg_data_home()
    if os.path.isdir(xdg_data_home_dir):
        paths.append(xdg_data_home_dir)

    xdg_data_dirs_env = core.getenv('XDG_DATA_DIRS', '')
    if not xdg_data_dirs_env:
        xdg_data_dirs_env = '/usr/local/share:/usr/share'
    paths.extend(path for path in xdg_data_dirs_env.split(':') if os.path.isdir(path))
    return paths


def find_first(subpath, paths, validate=os.path.isfile):
    """Return the first `subpath` found in the specified directory paths"""
    if os.path.isabs(subpath):
        return subpath
    for path in paths:
        candidate = os.path.join(path, subpath)
        if validate(candidate):
            return candidate
    # Nothing was found so return None.
    return None


def config_home(*args):
    """Return git-cola's configuration directory, e.g. ~/.config/git-cola"""
    return xdg_config_home('git-cola', *args)
