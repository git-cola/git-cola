"""Functions for finding cola resources"""
import os
from os.path import dirname
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
    _prefix = dirname(dirname(dirname(dirname(_package))))
elif _package.endswith(os.path.join('pkgs', 'cola')):
    # Windows release tree
    # __file__ = $installdir/pkgs/cola
    _prefix = dirname(dirname(_package))
else:
    # this is the source tree
    # __file__ = '$prefix/cola/__file__.py'
    _prefix = dirname(_package)


def get_prefix():
    """Return the installation prefix"""
    return _prefix


def prefix(*args):
    """Return a path relative to cola's installation prefix"""
    return os.path.join(get_prefix(), *args)


def command(name):
    """Return a command from the bin/ directory"""
    if compat.WIN32:
        # Check for "${name}.exe" on Windows.
        exe_path = prefix('bin', '%s.exe' % name)
        scripts_exe_path = prefix('Scripts', '%s.exe' % name)
        scripts_path = prefix('Scripts', name)
        path = prefix('bin', name)

        if core.exists(exe_path):
            result = exe_path
        elif core.exists(scripts_exe_path):
            result = scripts_exe_path
        elif core.exists(scripts_path):
            result = scripts_path
        else:
            result = path
    else:
        result = prefix('bin', name)
    return result


def doc(*args):
    """Return a path relative to cola's /usr/share/doc/ directory"""
    return share('doc', 'git-cola', *args)


def i18n(*args):
    """Return a path relative to cola's i18n locale directory, eg. cola/i18n"""
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
    """Return the XDG_DATA_HOME configuration directory, eg. ~/.local/share"""
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
    """Return git-cola's configuration directory, eg. ~/.config/git-cola"""
    return xdg_config_home('git-cola', *args)
