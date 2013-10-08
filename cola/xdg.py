# Copyright (c) 2012 David Aguilar
"""XDG user dirs
"""
import os
from cola import core


def config_home(*args):
    config = core.getenv('XDG_CONFIG_HOME',
                         os.path.join(core.expanduser('~'), '.config'))
    return os.path.join(config, 'git-cola', *args)
