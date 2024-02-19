"""i18n and l10n support for git-cola"""
import locale
import os

try:
    import polib
except ImportError:
    from . import polib
import sys

from . import core
from . import resources


class NullTranslation:
    """This is a pass-through object that does nothing"""

    def gettext(self, value):
        return value


class State:
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


class Translation:
    def __init__(self, lang):
        self.lang = lang
        self.messages = {}
        self.filename = get_filename_for_locale(lang)
        if self.filename:
            self.load()

    def load(self):
        """Read the .po file content into memory"""
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


def install(lang):
    if sys.platform == 'win32' and not lang:
        lang = _get_win32_default_locale()
    lang = _install_custom_language(lang)
    State.update(lang)


def uninstall():
    State.reset()


def _install_custom_language(lang):
    """Allow a custom language to be set in ~/.config/git-cola/language"""
    lang_file = resources.config_home('language')
    if not core.exists(lang_file):
        return lang
    try:
        lang = core.read(lang_file).strip()
    except OSError:
        return lang
    return lang


def _get_win32_default_locale():
    """Get the default locale on Windows"""
    for name in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
        lang = os.environ.get(name)
        if lang:
            return lang
    try:
        import ctypes
    except ImportError:
        # use only user's default locale
        return locale.getdefaultlocale()[0]
    # using ctypes to determine all locales
    lcid_user = ctypes.windll.kernel32.GetUserDefaultLCID()
    lcid_system = ctypes.windll.kernel32.GetSystemDefaultLCID()
    lang_user = locale.windows_locale.get(lcid_user)
    lang_system = locale.windows_locale.get(lcid_system)
    if lang_user:
        lang = lang_user
    else:
        lang = lang_system
    return lang
