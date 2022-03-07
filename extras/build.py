from __future__ import absolute_import, division, print_function, unicode_literals

from . import build_mo
from . import build_base as build


build.sub_commands = [
    ('build_mo', None),
] + list(build.sub_commands)
