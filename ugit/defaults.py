#!/usr/bin/env python

import os
from PyQt4.QtCore import QEvent
from ugit import version

VERSION = version.VERSION
DIRECTORY = os.getcwd()

WIDTH = 780
HEIGHT = 600

X = 262
Y = 254

DIFF_CONTEXT = 5

INOTIFY_EVENT = QEvent.User + 0
