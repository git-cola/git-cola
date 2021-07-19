"""i18n and l10n support for git-cola"""
from __future__ import absolute_import, division, print_function, unicode_literals
import gettext as _gettext
import os
import sys

from . import compat
from . import core
from . import resources

_null_translation = _gettext.NullTranslations()
_translation = _null_translation


def gettext(s):
    try:
        txt = _translation.ugettext(s)
    except AttributeError:
        # Python 3 compat
        _translation.ugettext = _translation.gettext
        txt = _translation.gettext(s)
    # handle @@verb / @@noun
    txt = txt.replace('@@verb', '').replace('@@noun', '')
    return txt


def ngettext(s, p, n):
    try:
        txt = _translation.ungettext(s, p, n)
    except AttributeError:
        # Python 3 compat
        _translation.ungettext = _translation.ngettext
        txt = _translation.ngettext(s, p, n)
    return txt


def N_(s):
    return gettext(s)


def install(locale):
    # pylint: disable=global-statement
    global _translation
    if sys.platform == 'win32':
        _check_win32_locale()
    if locale:
        _set_language(locale)
    _install_custom_language()
    _gettext.textdomain('messages')
    _translation = _gettext.translation(
        'git-cola', localedir=_get_locale_dir(), fallback=True
    )


def uninstall():
    # pylint: disable=global-statement
    global _translation
    _translation = _null_translation


def _get_locale_dir():
    return resources.prefix('share', 'locale')


def _install_custom_language():
    """Allow a custom language to be set in ~/.config/git-cola/language"""
    lang_file = resources.config_home('language')
    if not core.exists(lang_file):
        return
    try:
        locale = core.read(lang_file).strip()
    except (OSError, IOError):
        return
    if locale:
        _set_language(locale)


def _set_language(locale):
    compat.setenv('LANGUAGE', locale)
    compat.setenv('LANG', locale)
    compat.setenv('LC_ALL', locale)
    compat.setenv('LC_MESSAGES', locale)


def _check_win32_locale():
    for i in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
        if os.environ.get(i):
            break
    else:
        lang = None
        import locale  # pylint: disable=all

        try:
            import ctypes  # pylint: disable=all
        except ImportError:
            # use only user's default locale
            lang = locale.getdefaultlocale()[0]
        else:
            # using ctypes to determine all locales
            lcid_user = ctypes.windll.kernel32.GetUserDefaultLCID()
            lcid_system = ctypes.windll.kernel32.GetSystemDefaultLCID()
            if lcid_user != lcid_system:
                lcid = [lcid_user, lcid_system]
            else:
                lcid = [lcid_user]
            lang = [locale.windows_locale.get(i) for i in lcid]
            lang = ':'.join([i for i in lang if i])
        # set lang code for gettext
        if lang:
            compat.setenv('LANGUAGE', lang)
