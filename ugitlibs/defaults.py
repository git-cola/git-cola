#!/usr/bin/env python

import os
from PyQt4.QtCore import QEvent

VERSION = '0.8.0'
DIRECTORY = os.getcwd()

WIDTH = 780
HEIGHT = 600
X = 262
Y = 254

SPLITTER_TOP_0 = 152
SPLITTER_TOP_1 = 394
SPLITTER_BOTTOM_0 = 144
SPLITTER_BOTTOM_1 = 275

DIFF_CONTEXT = 5

INOTIFY_EVENT = QEvent.User + 0
