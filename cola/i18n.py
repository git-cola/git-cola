"""i18n and l10n support for git-cola"""

import gettext as _gettext
import os
import sys

from cola import compat
from cola import core
from cola import resources
from cola import xdg

_null_translation = _gettext.NullTranslations()
_translation = _null_translation


def gettext(s):
    return _translation.ugettext(s)


def ngettext(s, p, n):
    return _translation.ungettext(s, p, n)


def N_(s):
    return s


def install(locale):
    global _translation
    if sys.platform == 'win32':
        _check_win32_locale()
    if locale:
        compat.putenv('LANG', locale)
        compat.putenv('LC_MESSAGES', locale)
    _install_custom_language()
    _gettext.textdomain('messages')
    _translation = _gettext.translation('git-cola',
                                        localedir=_get_locale_dir(),
                                        fallback=True)

def uninstall():
    global _translation
    _translation = _null_translation


def _get_locale_dir():
    return resources.prefix('share', 'locale')


def _install_custom_language():
    """Allow a custom language to be set in ~/.config/git-cola/language"""
    lang_file = xdg.config_home('language')
    if not os.path.exists(lang_file):
        return
    try:
        fp = open(lang_file, 'r')
        lang = core.read(fp).strip()
        fp.close()
    except:
        return
    if lang:
        compat.putenv('LANGUAGE', lang)


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
            compat.putenv('LANGUAGE', lang)


# additional strings for translation
if 0:
    # file kinds
    N_('file')
    N_('directory')
    N_('symlink')
    # bugs status
    N_('fixed')
    # qcat titles for various file types
    N_('View text file')
    N_('View image file')
    N_('View binary file')
    N_('View symlink')
    N_('View directory')
    #
    N_("No changes selected to commit")
    N_("No changes selected to revert")
