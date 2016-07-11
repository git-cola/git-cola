from __future__ import absolute_import

from qtpy.QtGui import QKeySequence
from qtpy.QtCore import Qt

# A-G
STAGE_MODIFIED = QKeySequence(Qt.ALT + Qt.Key_A)
WORD_LEFT = QKeySequence(Qt.Key_B)
BLAME = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_B)
BRANCH = QKeySequence(Qt.CTRL + Qt.Key_B)
CHECKOUT = QKeySequence(Qt.ALT + Qt.Key_B)
CHERRY_PICK = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_C)
DIFFSTAT = QKeySequence(Qt.ALT + Qt.Key_D)
DIFF = QKeySequence(Qt.CTRL + Qt.Key_D)
DIFF_SECONDARY = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_D)
EDIT = QKeySequence(Qt.CTRL + Qt.Key_E)
EDIT_SECONDARY = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_E)
EXPORT = QKeySequence(Qt.ALT + Qt.Key_E)
FIT = QKeySequence(Qt.Key_F)
FETCH = QKeySequence(Qt.CTRL + Qt.Key_F)
FILTER = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_F)
GREP = QKeySequence(Qt.CTRL + Qt.Key_G)
# H-P
MOVE_LEFT = QKeySequence(Qt.Key_H)
MOVE_LEFT_SHIFT = QKeySequence(Qt.SHIFT + Qt.Key_H)
HISTORY = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_H)
SIGNOFF = QKeySequence(Qt.CTRL + Qt.Key_I)
MOVE_DOWN = QKeySequence(Qt.Key_J)
MOVE_DOWN_SHIFT = QKeySequence(Qt.SHIFT + Qt.Key_J)
MOVE_DOWN_SECONDARY = QKeySequence(Qt.ALT + Qt.Key_J)
MOVE_DOWN_TERTIARY = QKeySequence(Qt.SHIFT + Qt.Key_J)
MOVE_UP = QKeySequence(Qt.Key_K)
MOVE_UP_SHIFT = QKeySequence(Qt.SHIFT + Qt.Key_K)
MOVE_UP_SECONDARY = QKeySequence(Qt.ALT + Qt.Key_K)
MOVE_UP_TERTIARY = QKeySequence(Qt.SHIFT + Qt.Key_K)
MOVE_RIGHT = QKeySequence(Qt.Key_L)
MOVE_RIGHT_SHIFT = QKeySequence(Qt.SHIFT + Qt.Key_L)
FOCUS = QKeySequence(Qt.CTRL + Qt.Key_L)
FOCUS_STATUS = QKeySequence(Qt.CTRL + Qt.Key_K)
AMEND = QKeySequence(Qt.CTRL + Qt.Key_M)
MERGE = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_M)
PUSH = QKeySequence(Qt.CTRL + Qt.Key_P)
PULL = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_P)
# Q-Z
QUIT = QKeySequence(Qt.CTRL + Qt.Key_Q)
REFRESH = QKeySequence(Qt.CTRL + Qt.Key_R)
REFRESH_SECONDARY = QKeySequence(Qt.Key_F5)
REFRESH_HOTKEYS = (REFRESH, REFRESH_SECONDARY)
STAGE_DIFF = QKeySequence(Qt.Key_S)
STAGE_SELECTION = QKeySequence(Qt.CTRL + Qt.Key_S)
STASH = QKeySequence(Qt.ALT + Qt.SHIFT + Qt.Key_S)
FINDER = QKeySequence(Qt.CTRL + Qt.Key_T)
FINDER_SECONDARY = QKeySequence(Qt.Key_T)
TERMINAL = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_T)
STAGE_UNTRACKED = QKeySequence(Qt.ALT + Qt.Key_U)
REVERT = QKeySequence(Qt.CTRL + Qt.Key_U)
WORD_RIGHT = QKeySequence(Qt.Key_W)
UNDO = QKeySequence(Qt.CTRL + Qt.Key_Z)

# Numbers
START_OF_LINE = QKeySequence(Qt.Key_0)

# Special keys
BACKSPACE = QKeySequence(Qt.Key_Backspace)
TRASH = QKeySequence(Qt.CTRL + Qt.Key_Backspace)
DELETE_FILE = QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_Backspace)
DELETE_FILE_SECONDARY = QKeySequence(Qt.CTRL + Qt.Key_Backspace)
PREFERENCES = QKeySequence(Qt.CTRL + Qt.Key_Comma)
END_OF_LINE = QKeySequence(Qt.Key_Dollar)
DOWN = QKeySequence(Qt.Key_Down)
ENTER = QKeySequence(Qt.Key_Enter)
ZOOM_OUT = QKeySequence(Qt.Key_Minus)
REMOVE_ITEM = QKeySequence(Qt.Key_Minus)
ADD_ITEM = QKeySequence(Qt.Key_Plus)
ZOOM_IN = QKeySequence(Qt.Key_Plus)
ZOOM_IN_SECONDARY = QKeySequence(Qt.Key_Equal)

QUESTION = QKeySequence(Qt.Key_Question)
RETURN = QKeySequence(Qt.Key_Return)
ACCEPT = (ENTER, RETURN)
COMMIT = QKeySequence(Qt.CTRL + Qt.Key_Return)
PRIMARY_ACTION = QKeySequence(QKeySequence(Qt.Key_Space))
SECONDARY_ACTION = QKeySequence(Qt.SHIFT + Qt.Key_Space)
LEAVE = QKeySequence(Qt.SHIFT + Qt.Key_Tab)
UP = QKeySequence(Qt.Key_Up)

CTRL_RETURN = QKeySequence(Qt.CTRL + Qt.Key_Return)
CTRL_ENTER = QKeySequence(Qt.CTRL + Qt.Key_Enter)

# Rebase
REBASE_PICK = (QKeySequence(Qt.Key_1), QKeySequence(Qt.Key_P))
REBASE_REWORD = (QKeySequence(Qt.Key_2), QKeySequence(Qt.Key_R))
REBASE_EDIT = (QKeySequence(Qt.Key_3), QKeySequence(Qt.Key_E))
REBASE_FIXUP = (QKeySequence(Qt.Key_4), QKeySequence(Qt.Key_F))
REBASE_SQUASH = (QKeySequence(Qt.Key_5), QKeySequence(Qt.Key_S))

# Key Sequences
COPY = QKeySequence.Copy
CLOSE = QKeySequence.Close
CUT = QKeySequence.Cut
DELETE = QKeySequence.Delete
NEW = QKeySequence.New
OPEN = QKeySequence.Open
