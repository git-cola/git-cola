"""i18n and l10n support for git-cola"""
# https://www.linux.com/news/controlling-your-locale-environment-variables/
# and locale(1) that environment variables are checked in this order:
#   LANGUAGE, LC_ALL, LC_MESSAGES, LANG
#
# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1140489
# was a report where the user's LC_MESSAGES was not resetting the translations.
from __future__ import annotations
import ctypes
import locale
import os

try:
    import polib
except ImportError:
    from . import polib

from . import core
from . import resources
from . import utils


class NullTranslation:
    """This is a pass-through object that does nothing"""

    def gettext(self, value: str) -> str:
        return value


class State:
    """The application-wide current translation state"""

    translation: NullTranslation | Translation = NullTranslation()

    @classmethod
    def reset(cls) -> None:
        cls.translation = NullTranslation()

    @classmethod
    def update(cls, lang: str | None) -> str | None:
        cls.translation = Translation(lang)

    @classmethod
    def gettext(cls, value: str) -> str:
        """Return a translated value"""
        return cls.translation.gettext(value)


class Translation:
    def __init__(self, lang: str | None) -> None:
        self.lang = lang
        self.messages = {}
        self.filename = get_filename_for_locale(lang)
        if self.filename:
            self.load()

    def load(self) -> None:
        """Read the .po file content into memory"""
        po = polib.pofile(self.filename, encoding='utf-8')
        messages = self.messages
        messages.clear()  # reset state to make this function reentrant.
        for entry in po.translated_entries():
            messages[entry.msgid] = entry.msgstr

    def gettext(self, value: str) -> str:
        return self.messages.get(value, value)


def gettext(value: str) -> str:
    """Translate a string"""
    txt = State.gettext(value)
    # handle @@verb / @@noun
    if txt[-6:-4] == '@@':
        txt = txt.replace('@@verb', '').replace('@@noun', '')
    return txt


def N_(value: str) -> str:
    """Marker function for translated values

    N_("Some string value") is used to mark strings for translation.
    """
    return gettext(value)


def get_filename_for_locale(name: str | None) -> str | None:
    """Return the .po file for the specified locale"""
    # When <name> is "foo_BAR.UTF-8", the name is truncated to "foo_BAR".
    # When <name> is "foo_BAR", the <short_name> is "foo"
    # Try the following locations:
    #   cola/i18n/<name>.po
    #   cola/i18n/<short_name>.po
    if not name:  # If no locale was specified then try the current locale.
        name = get_current_locale()

    if not name:
        return None

    name: str = name.split('.', 1)[0]  # foo_BAR.UTF-8 -> foo_BAR

    filename = resources.i18n('%s.po' % name)
    if os.path.exists(filename):
        return filename

    short_name = name.split('_', 1)[0]
    filename = resources.i18n('%s.po' % short_name)
    if os.path.exists(filename):
        return filename
    return None


def install(lang: str | None) -> str | None:
    if not lang:
        lang = get_default_locale()
    lang = _install_custom_language(lang)
    State.update(lang)


def uninstall() -> None:
    State.reset()


def _install_custom_language(lang: str | None) -> str | None:
    """Allow a custom language to be set in ~/.config/git-cola/language"""
    lang_file = resources.config_home('language')
    if not core.exists(lang_file):
        return lang
    try:
        lang = core.read(lang_file).strip()
    except OSError:
        return lang
    return lang


def get_default_locale() -> str | None:
    """Get the default locale via environment variables and other platform-specific methods"""
    # gettext() supports LANGAUGES as a colon-separate list of locales to try.
    lang_env = os.environ.get('LANGUAGE', '')
    for lang in (lang for lang in lang_env.split(':') if lang):
        if get_filename_for_locale(lang) or is_untranslated_locale(lang):
            return lang

    # From locale(7):
    # (1)  If there is a non-null environment variable LC_ALL, the value of LC_ALL is used.
    # (2)  If an environment variable (LC_MESSAGES) with the same name as one of the categories above
    # exists and is non-null, its value is used for that category.
    # (3)  If there is a non-null environment variable LANG, the value of LANG is used.
    for name in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        lang = os.environ.get(name, '')
        if lang:
            return lang

    # Windows method for getting the user's locale.
    if (
        utils.is_win32()
        and hasattr(ctypes, 'windll')
        and hasattr(locale, 'windows_locale')
    ):
        lcid_user = ctypes.windll.kernel32.GetUserDefaultLCID()
        lcid_system = ctypes.windll.kernel32.GetSystemDefaultLCID()
        lang_user = locale.windows_locale.get(lcid_user)
        lang_system = locale.windows_locale.get(lcid_system)
        if lang_user:
            lang = lang_user
        else:
            lang = lang_system
        return lang

    # Let python determine the locale.
    current_locale = get_current_locale()
    if get_filename_for_locale(current_locale):
        return current_locale

    # None means that the untranslated English string values will be used.
    return None


def get_current_locale() -> str:
    """Forwards-compatibility wrapper for Python 3.15+"""
    if hasattr(locale, 'getlocale'):
        return locale.getlocale()[0]
    # getdefaultlocale() was deprecated in Python 3.14 and will be removed in Python 3.14.
    return locale.getdefaultlocale()[0]


def is_untranslated_locale(lang):
    """Accessing the default untranslated language (en) requires special handling"""
    return lang in ('en', 'en_US', 'en_US.UTF-8')
