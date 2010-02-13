#!/usr/bin/env python
# This is used by the Makefile to name the final app.tar.bz2 file

import os
import sys
import platform

sys.path.insert(0, os.getcwd())

if not hasattr(platform, 'mac_ver'):
    print 'This only runs on os x'
    sys.exit(1)

# get the platform
macstuff = platform.mac_ver()
cpu = platform.processor()
proc = {'i386': 'intel'}.get(cpu, cpu)
name = 'unknown'
version = macstuff[0]

if version[:4] == '10.6':
    name = 'snow_leopard'
elif version[:4] == '10.5':
    name = 'leopard'
elif version[:4] == '10.4':
    name = 'tiger'
elif version[:4] == '10.3':
    name = 'panther'
else:
    name = 'unknown'

# git-cola-intel-leopard.app.tar.bz2
print('git-cola-%s-%s.app.tar.bz2' % (proc, name))
