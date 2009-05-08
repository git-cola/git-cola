#!/usr/bin/env python
import os
import sys
import glob
import shutil
import platform

# Find the root of the source tree
sourcedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, sourcedir)

from setup import cola_data_files
import setuptools

# Copy bin/git-cola to darwin/git-cola
src = os.path.join(sourcedir, 'bin', 'git-cola')
dst = os.path.join(sourcedir, 'darwin', 'git-cola.py')
shutil.copy(src, dst)

# About argv_inject:
# When someone drags a folder onto git-cola.app we need
# to add '--repo' before the path.  Unfortunately, py2app
# does this unconditionally, even when there are no
# arguments to process.
try:
    prefer_ppc = platform.processor() == 'powerpc'
    setuptools.setup(app=['darwin/git-cola.py'],
                     data_files=cola_data_files(),
                     options={'py2app': {'argv_emulation': True,
                                         'argv_inject': '--repo',
                                         'LSPrefersPPC': prefer_ppc,
                                         'iconfile': 'darwin/git-cola.icns',
                                         'includes': ['sip', 'PyQt4._qt']}},
                     setup_requires=['py2app'])
finally:
    # Remove the temporary file
    os.remove(dst)

# Copy our custom __boot__.py for handling --repo
bootsrc = os.path.join(sourcedir, 'darwin', '__boot__.py')
bootdst = os.path.join(sourcedir, 'dist', 'git-cola.app',
                       'Contents', 'Resources', '__boot__.py')
shutil.copy(bootsrc, bootdst)
