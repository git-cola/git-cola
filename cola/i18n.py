"""i18n and l10n support for git-cola"""
from __future__ import division, absolute_import, unicode_literals

import gettext as _gettext
import os
import sys

from cola import compat
from cola import core
from cola import resources

_null_translation = _gettext.NullTranslations()
# Python 3 compat
if not hasattr(_null_translation, 'ugettext'):
    _null_translation.ugettext = _null_translation.gettext
    _null_translation.ungettext = _null_translation.ngettext
_translation = _null_translation


def gettext(s):
    txt = _translation.ugettext(s)
    if txt[-6:-4] == '@@': # handle @@verb / @@noun
        txt = txt[:-6]
    return txt


def ngettext(s, p, n):
    return _translation.ungettext(s, p, n)


def N_(s):
    return gettext(s)


def install(locale):
    global _translation
    if sys.platform == 'win32':
        _check_win32_locale()
    if locale:
        compat.setenv('LANGUAGE', locale)
        compat.setenv('LANG', locale)
        compat.setenv('LC_MESSAGES', locale)
    _install_custom_language()
    _gettext.textdomain('messages')
    _translation = _gettext.translation('git-cola',
                                        localedir=_get_locale_dir(),
                                        fallback=True)
    # Python 3 compat
    if not hasattr(_translation, 'ugettext'):
        _translation.ugettext = _translation.gettext
        _translation.ungettext = _translation.ngettext

def uninstall():
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
        lang = core.read(lang_file).strip()
    except:
        return
    if lang:
        compat.setenv('LANGUAGE', lang)


def _check_win32_locale():
    for i in ('LANGUAGE','LC_ALL','LC_MESSAGES','LANG'):
        if os.environ.get(i):
            break
    else:
        lang = None
        import locale
        try:
            import ctypes
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
