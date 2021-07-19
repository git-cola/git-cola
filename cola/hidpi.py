"""Provides High DPI support by wrapping Qt options"""
from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtCore

from .i18n import N_
from . import core
from . import compat
from . import version


class Option(object):
    AUTO = '0'
    DISABLE = 'disable'
    TIMES_1 = '1'
    TIMES_1_5 = '1.5'
    TIMES_2 = '2'


def is_supported():
    return version.check('qt-hidpi-scale', QtCore.__version__)


def apply_choice(value):
    value = compat.ustr(value)
    if value == Option.AUTO:
        # Do not override the configuration when either of these
        # two environment variables are defined.
        if not core.getenv('QT_AUTO_SCREEN_SCALE_FACTOR') and not core.getenv(
            'QT_SCALE_FACTOR'
        ):
            compat.setenv('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
            compat.unsetenv('QT_SCALE_FACTOR')
    elif value in (Option.TIMES_1, Option.TIMES_1_5, Option.TIMES_2):
        compat.unsetenv('QT_AUTO_SCREEN_SCALE_FACTOR')
        compat.setenv('QT_SCALE_FACTOR', value)


def options():
    return (
        (N_('Auto'), Option.AUTO),
        (N_('Disable'), Option.DISABLE),
        (N_('x 1'), Option.TIMES_1),
        (N_('x 1.5'), Option.TIMES_1_5),
        (N_('x 2'), Option.TIMES_2),
    )
