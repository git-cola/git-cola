from PyQt4.QtGui import QKeySequence
from PyQt4.QtCore import Qt

# A-G
STAGE_MODIFIED = Qt.AltModifier | Qt.Key_A
WORD_LEFT = Qt.Key_B
BRANCH = Qt.ControlModifier | Qt.Key_B
CHECKOUT = Qt.AltModifier | Qt.Key_B
CHERRY_PICK = Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_C
DIFFSTAT = Qt.AltModifier | Qt.Key_D
DIFF = Qt.ControlModifier | Qt.Key_D
DIFF_SECONDARY = Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_D
EDIT = Qt.ControlModifier | Qt.Key_E
EDIT_SECONDARY = Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_E
EXPORT = Qt.AltModifier | Qt.Key_E
FIT = Qt.Key_F
FETCH = Qt.ControlModifier | Qt.Key_F
FILTER = Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_F
GREP = Qt.ControlModifier | Qt.Key_G
# H-P
MOVE_LEFT = Qt.Key_H
HISTORY = Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_H
SIGNOFF = Qt.ControlModifier | Qt.Key_I
MOVE_DOWN = Qt.Key_J
MOVE_DOWN_SECONDARY = Qt.AltModifier | Qt.Key_J
MOVE_DOWN_TERTIARY = Qt.ShiftModifier | Qt.Key_J
MOVE_UP = Qt.Key_K
MOVE_UP_SECONDARY = Qt.AltModifier | Qt.Key_K
MOVE_UP_TERTIARY = Qt.ShiftModifier | Qt.Key_K
MOVE_RIGHT = Qt.Key_L
FOCUS = Qt.ControlModifier | Qt.Key_L
AMEND = Qt.ControlModifier | Qt.Key_M
MERGE = Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_M
PUSH = Qt.ControlModifier | Qt.Key_P
PULL = Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_P
# Q-Z
QUIT = Qt.ControlModifier | Qt.Key_Q
REFRESH = Qt.ControlModifier | Qt.Key_R
REFRESH_SECONDARY = Qt.Key_F5
REFRESH_HOTKEYS = (REFRESH, REFRESH_SECONDARY)
STAGE_DIFF = Qt.Key_S
STAGE_SELECTION = Qt.ControlModifier | Qt.Key_S
STASH = Qt.AltModifier | Qt.ShiftModifier | Qt.Key_S
FINDER = Qt.ControlModifier | Qt.Key_T
FINDER_SECONDARY = Qt.Key_T
TERMINAL = Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_T
STAGE_UNTRACKED = Qt.AltModifier | Qt.Key_U
REVERT = Qt.ControlModifier | Qt.Key_U
WORD_RIGHT = Qt.Key_W
UNDO = Qt.ControlModifier | Qt.Key_Z

# Numbers
START_OF_LINE = Qt.Key_0

# Special keys
BACKSPACE = Qt.Key_Backspace
TRASH = Qt.ControlModifier | Qt.Key_Backspace
DELETE_FILE = Qt.ControlModifier | Qt.ShiftModifier | Qt.Key_Backspace
DELETE_FILE_SECONDARY = Qt.ControlModifier | Qt.Key_Backspace
PREFERENCES = Qt.ControlModifier | Qt.Key_Comma
END_OF_LINE = Qt.Key_Dollar
DOWN = Qt.Key_Down
ENTER = Qt.Key_Enter
ZOOM_OUT = Qt.Key_Minus
REMOVE_ITEM = Qt.Key_Minus
ADD_ITEM = Qt.Key_Plus
ZOOM_IN = Qt.Key_Plus
ZOOM_IN_SECONDARY = Qt.Key_Equal

QUESTION = Qt.Key_Question
RETURN = Qt.Key_Return
ACCEPT = (ENTER, RETURN)
COMMIT = Qt.ControlModifier | Qt.Key_Return
PRIMARY_ACTION = Qt.Key_Space
SECONDARY_ACTION = Qt.ShiftModifier | Qt.Key_Space
LEAVE = Qt.ShiftModifier | Qt.Key_Tab
UP = Qt.Key_Up

# Rebase
REBASE_PICK = (Qt.Key_1, Qt.Key_P)
REBASE_REWORD = (Qt.Key_2, Qt.Key_R)
REBASE_EDIT = (Qt.Key_3, Qt.Key_E)
REBASE_FIXUP = (Qt.Key_4, Qt.Key_F)
REBASE_SQUASH = (Qt.Key_5, Qt.Key_S)

# Key Sequences
COPY = QKeySequence.Copy
CLOSE = QKeySequence.Close
CUT = QKeySequence.Cut
DELETE = QKeySequence.Delete
NEW = QKeySequence.New
OPEN = QKeySequence.Open
