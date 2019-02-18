"""Provides High DPI support by wrapping Qt options"""
from __future__ import absolute_import, division, unicode_literals
import os

from qtpy.QtCore import QT_VERSION

from . import compat
from .i18n import N_


class EChoice(object):
    AUTO = '0'
    TIMES_1 = '1'
    TIMES_1_5 = '1.5'
    TIMES_2 = '2'


def is_supported():
    return QT_VERSION >= 0x050600


def apply_choice(value):
    if value == EChoice.AUTO:
        compat.setenv('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
        compat.unsetenv('QT_SCALE_FACTOR')
    else:
        compat.unsetenv('QT_AUTO_SCREEN_SCALE_FACTOR')
        compat.setenv('QT_SCALE_FACTOR', str(value))


def choices_map():
    result = dict()
    result[N_('Auto')] = EChoice.AUTO
    result[N_('x 1')] = EChoice.TIMES_1
    result[N_('x 1.5')] = EChoice.TIMES_1_5
    result[N_('x 2')] = EChoice.TIMES_2
    return result
