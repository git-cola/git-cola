"""Provides High DPI support by wrapping Qt options"""
from __future__ import absolute_import, division, unicode_literals

from qtpy.QtCore import QT_VERSION

from . import compat
from .i18n import N_


class Option(object):
    AUTO = '0'
    TIMES_1 = '1'
    TIMES_1_5 = '1.5'
    TIMES_2 = '2'


def is_supported():
    return QT_VERSION >= 0x050600


def apply_choice(value):
    value = compat.ustr(value)
    if value == Option.AUTO:
        compat.setenv('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
        compat.unsetenv('QT_SCALE_FACTOR')
    else:
        compat.unsetenv('QT_AUTO_SCREEN_SCALE_FACTOR')
        compat.setenv('QT_SCALE_FACTOR', value)


def options():
    return (
        (N_('Auto'), Option.AUTO),
        (N_('x 1'), Option.TIMES_1),
        (N_('x 1.5'), Option.TIMES_1_5),
        (N_('x 2'), Option.TIMES_2),
    )
