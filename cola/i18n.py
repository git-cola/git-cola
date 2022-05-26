"""i18n and l10n support for git-cola"""
from __future__ import absolute_import, division, print_function, unicode_literals
import locale
import os
import sys

from . import compat
from . import core
from . import polib
from . import resources


class NullTranslation(object):
    """This is a pass-through object that does nothing"""

    def gettext(self, value):
        return value


class State(object):
    """The application-wide current translation state"""

    translation = NullTranslation()

    @classmethod
    def reset(cls):
        cls.translation = NullTranslation()

    @classmethod
    def update(cls, lang):
        cls.translation = Translation(lang)

    @classmethod
    def gettext(cls, value):
        """Return a translated value"""
        return cls.translation.gettext(value)


class Translation(object):
    def __init__(self, lang):
        self.lang = lang
        self.messages = {}
        self.filename = get_filename_for_locale(lang)
        if self.filename:
            self.load()

    def load(self):
        """Read the pofile content into memory"""
        po = polib.pofile(self.filename, encoding='utf-8')
        messages = self.messages
        for entry in po.translated_entries():
            messages[entry.msgid] = entry.msgstr

    def gettext(self, value):
        return self.messages.get(value, value)


def gettext(value):
    """Translate a string"""
    txt = State.gettext(value)
    # handle @@verb / @@noun
    if txt[-6:-4] == '@@':
        txt = txt.replace('@@verb', '').replace('@@noun', '')
    return txt


def N_(value):
    """Marker function for translated values

    N_("Some string value") is used to mark strings for translation.
    """
    return gettext(value)


def get_filename_for_locale(name):
    """Return the .po file for the specified locale"""
    # When <name> is "foo_BAR.UTF-8", the name is truncated to "foo_BAR".
    # When <name> is "foo_BAR", the <short_name> is "foo"
    # Try the following locations:
    #   cola/i18n/<name>.po
    #   cola/i18n/<short_name>.po
    if not name:  # If no locale was specified then try the current locale.
        name = locale.getdefaultlocale()[0]

    if not name:
        return None

    name = name.split('.', 1)[0]  # foo_BAR.UTF-8 -> foo_BAR

    filename = resources.i18n('%s.po' % name)
    if os.path.exists(filename):
        return filename

    short_name = name.split('_', 1)[0]
    filename = resources.i18n('%s.po' % short_name)
    if os.path.exists(filename):
        return filename
    return None


def install(locale):
    # pylint: disable=global-statement
    if sys.platform == 'win32':
        _check_win32_locale()
    if locale:
        _set_language(locale)
    _install_custom_language()

    State.update(locale)


def uninstall():
    # pylint: disable=global-statement
    State.reset()


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
