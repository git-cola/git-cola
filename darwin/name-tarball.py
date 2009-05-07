#!/usr/bin/env python
# This is used by the Makefile to name the final app.tar.bz2 file

import platform
import sys

if not hasattr(platform, 'mac_ver'):
    print 'This only runs on os x'
    sys.exit(1)

if not len(sys.argv) > 1:
    print 'usage: prep-tarball.py [darwin tarball]'
    sys.exit(1)

filename = sys.argv[1]
# git-cola-v1.3.7-45-g7862.app.tar.bz2
# git-cola-v1.3.7.app.tar.bz2
dashcount = filename.count('-')
if dashcount != 2 and dashcount != 4:
    print 'error: unsupported filename pattern'
    sys.exit(1)

# get the platform
macstuff = platform.mac_ver()

proc = {'i386': 'intel'}.get(macstuff[2], macstuff[2])
name = 'unknown'
version = macstuff[0]
if version[:4] == '10.5':
    name = 'leopard'
elif version[:4] == '10.4':
    name = 'tiger'
elif version[:4] == '10.3':
    name = 'panther'
else:
    print 'unrecognized mac version:', version
    sys.exit(1)

parts = filename.split('-')
if dashcount == 2:
    # git-cola-intel-leopard-v1.2.3.app.tar.bz2
    print('git-cola-%s-%s-%s' % (proc, name, parts[-1]))

elif dashcount == 4:
    # git-cola-intel-leopard-v1.2.3-N-xxxx.app.tar.bz2
    print('git-cola-%s-%s-%s.%s.%s' %
            (proc, name, parts[-3], parts[-2], parts[-1]))
else:
    print 'git-cola-%s-%s-snapshot.app.tar.bz2' % (proc, name)
