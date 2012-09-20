# Copyright (c) 2012 David Aguilar
"""XDG user dirs
"""
import os


def config_home(*args):
    config = os.getenv('XDG_CONFIG_HOME',
                       os.path.join(os.path.expanduser('~'), '.config'))
    return os.path.join(config, 'git-cola', *args)
