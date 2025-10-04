import sys

from qtpy.QtGui import QKeySequence
from qtpy.QtCore import Qt


def hotkey(*seq):
    return QKeySequence(*seq)


# A-G
STAGE_MODIFIED = hotkey(Qt.ALT | Qt.Key_A)
STASH_ALL = hotkey(Qt.ALT | Qt.Key_A)
WORD_LEFT = hotkey(Qt.Key_B)
BLAME = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_B)
BRANCH = hotkey(Qt.CTRL | Qt.Key_B)
CHECKOUT = hotkey(Qt.ALT | Qt.Key_B)
CHERRY_PICK = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_C)
COPY_COMMIT_ID = hotkey(Qt.CTRL | Qt.ALT | Qt.Key_C)
COPY_DIFF = hotkey(Qt.ALT | Qt.SHIFT | Qt.Key_C)
CTRL_1 = hotkey(Qt.CTRL | Qt.Key_1)
CTRL_2 = hotkey(Qt.CTRL | Qt.Key_2)
CTRL_3 = hotkey(Qt.CTRL | Qt.Key_3)
DIFFSTAT = hotkey(Qt.ALT | Qt.Key_D)
DIFF = hotkey(Qt.CTRL | Qt.Key_D)
DIFF_SECONDARY = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_D)
EDIT_SHORT = hotkey(Qt.Key_E)
EDIT = hotkey(Qt.CTRL | Qt.Key_E)
EDIT_SECONDARY = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_E)
EXPORT = hotkey(Qt.ALT | Qt.SHIFT | Qt.Key_E)
FIT = hotkey(Qt.Key_F)
FETCH = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_F)
FILTER = hotkey(Qt.ALT | Qt.SHIFT | Qt.Key_F)
GOTO_END = hotkey(Qt.SHIFT | Qt.Key_G)
GOTO_START = hotkey(Qt.Key_G, Qt.Key_G)  # gg
GREP = hotkey(Qt.ALT | Qt.Key_G)
# H-P
MOVE_LEFT = hotkey(Qt.Key_H)
MOVE_LEFT_SHIFT = hotkey(Qt.SHIFT | Qt.Key_H)
HISTORY = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_H)
SIGNOFF = hotkey(Qt.CTRL | Qt.Key_I)
MOVE_DOWN = hotkey(Qt.Key_J)
MOVE_DOWN_SHIFT = hotkey(Qt.SHIFT | Qt.Key_J)
MOVE_DOWN_SECONDARY = hotkey(Qt.ALT | Qt.Key_J)
MOVE_DOWN_TERTIARY = hotkey(Qt.SHIFT | Qt.Key_J)
MOVE_UP = hotkey(Qt.Key_K)
MOVE_UP_SHIFT = hotkey(Qt.SHIFT | Qt.Key_K)
MOVE_UP_SECONDARY = hotkey(Qt.ALT | Qt.Key_K)
MOVE_UP_TERTIARY = hotkey(Qt.SHIFT | Qt.Key_K)
MOVE_RIGHT = hotkey(Qt.Key_L)
MOVE_RIGHT_SHIFT = hotkey(Qt.SHIFT | Qt.Key_L)
FOCUS = hotkey(Qt.CTRL | Qt.Key_L)
FOCUS_DIFF = hotkey(Qt.CTRL | Qt.Key_J)
FOCUS_INPUT = hotkey(Qt.CTRL | Qt.Key_L)
FOCUS_STATUS = hotkey(Qt.CTRL | Qt.Key_K)
FOCUS_TREE = hotkey(Qt.CTRL | Qt.Key_K)
AMEND_DEFAULT = hotkey(Qt.CTRL | Qt.Key_M)
AMEND_MACOS = hotkey(Qt.ALT | Qt.Key_M)
if sys.platform == 'darwin':
    AMEND = (AMEND_MACOS,)
else:
    AMEND = (AMEND_DEFAULT, AMEND_MACOS)
MACOS_MINIMIZE = hotkey(Qt.CTRL | Qt.Key_M)
MERGE = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_M)
PUSH = hotkey(Qt.CTRL | Qt.Key_P)
PULL = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_P)
OPEN_REPO_SEARCH = hotkey(Qt.ALT | Qt.Key_P)
# Q-Z
QUIT = hotkey(Qt.CTRL | Qt.Key_Q)
REFRESH = hotkey(Qt.CTRL | Qt.Key_R)
REFRESH_SECONDARY = hotkey(Qt.Key_F5)
REFRESH_HOTKEYS = (REFRESH, REFRESH_SECONDARY)
STAGE_DIFF = hotkey(Qt.Key_S)
EDIT_AND_STAGE_DIFF = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_S)
SAVE = hotkey(Qt.CTRL | Qt.Key_S)
SEARCH = hotkey(Qt.CTRL | Qt.Key_F)
SEARCH_NEXT = hotkey(Qt.CTRL | Qt.Key_G)
SEARCH_PREV = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_G)
STAGE_DIFF_ALT = hotkey(Qt.SHIFT | Qt.Key_S)
STAGE_SELECTION = hotkey(Qt.CTRL | Qt.Key_S)
STAGE_ALL = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_S)
STASH = hotkey(Qt.ALT | Qt.SHIFT | Qt.Key_S)
STASH_STAGED = hotkey(Qt.ALT | Qt.Key_S)
FINDER = hotkey(Qt.CTRL | Qt.Key_T)
FINDER_SECONDARY = hotkey(Qt.Key_T)
TERMINAL = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_T)
STAGE_UNTRACKED = hotkey(Qt.ALT | Qt.Key_U)
STASH_UNSTAGED = hotkey(Qt.ALT | Qt.Key_U)
REVERT = hotkey(Qt.CTRL | Qt.Key_U)
REVERT_ALT = hotkey(Qt.ALT | Qt.SHIFT | Qt.Key_R)
REVERT_UNSTAGED_EDITS = hotkey(Qt.ALT | Qt.CTRL | Qt.Key_U)
EDIT_AND_REVERT = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_U)
WORD_RIGHT = hotkey(Qt.Key_W)

# Numbers
START_OF_LINE = hotkey(Qt.Key_0)

# Special keys
BACKSPACE = hotkey(Qt.Key_Backspace)
TRASH = hotkey(Qt.CTRL | Qt.Key_Backspace)
DELETE_FILE = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_Backspace)
DELETE_FILE_SECONDARY = hotkey(Qt.CTRL | Qt.Key_Backspace)
PREFERENCES = hotkey(Qt.CTRL | Qt.Key_Comma)
END_OF_LINE = hotkey(Qt.Key_Dollar)
DOWN = hotkey(Qt.Key_Down)
ENTER = hotkey(Qt.Key_Enter)
ZOOM_OUT = hotkey(Qt.Key_Minus)
REMOVE_ITEM = hotkey(Qt.Key_Minus)
ADD_ITEM = hotkey(Qt.Key_Plus)
ZOOM_IN = hotkey(Qt.Key_Plus)
ZOOM_IN_SECONDARY = hotkey(Qt.Key_Equal)

QUESTION = hotkey(Qt.Key_Question)
RETURN = hotkey(Qt.Key_Return)
ACCEPT = (ENTER, RETURN)
APPLY = hotkey(Qt.CTRL | Qt.Key_Return)
PREPARE_COMMIT_MESSAGE = hotkey(Qt.CTRL | Qt.SHIFT | Qt.Key_Return)
PRIMARY_ACTION = hotkey(hotkey(Qt.Key_Space))
SECONDARY_ACTION = hotkey(Qt.SHIFT | Qt.Key_Space)
LEAVE = hotkey(Qt.SHIFT | Qt.Key_Tab)
UP = hotkey(Qt.Key_Up)

CTRL_RETURN = hotkey(Qt.CTRL | Qt.Key_Return)
CTRL_ENTER = hotkey(Qt.CTRL | Qt.Key_Enter)
CTRL_LEFT = hotkey(Qt.CTRL | Qt.Key_Left)
CTRL_RIGHT = hotkey(Qt.CTRL | Qt.Key_Right)

# Rebase
REBASE_START_AND_CONTINUE = hotkey(Qt.ALT | Qt.Key_R)
REBASE_PICK = (hotkey(Qt.Key_1), hotkey(Qt.Key_P))
REBASE_REWORD = (hotkey(Qt.Key_2), hotkey(Qt.Key_R))
REBASE_EDIT = (hotkey(Qt.Key_3), hotkey(Qt.Key_E))
REBASE_FIXUP = (hotkey(Qt.Key_4), hotkey(Qt.Key_F))
REBASE_SQUASH = (hotkey(Qt.Key_5), hotkey(Qt.Key_S))
REBASE_DROP = (hotkey(Qt.Key_6), hotkey(Qt.Key_D))

UNDO = hotkey(Qt.CTRL | Qt.Key_Z)
REDO = hotkey(Qt.SHIFT | Qt.CTRL | Qt.Key_Z)

# Key Sequences
COPY = QKeySequence.Copy
CLOSE = QKeySequence.Close
CUT = QKeySequence.Cut
PASTE = QKeySequence.Paste
DELETE = QKeySequence.Delete
NEW = QKeySequence.New
OPEN = QKeySequence.Open
SELECT_ALL = QKeySequence.SelectAll

# Text navigation
TEXT_DOWN = hotkey(Qt.Key_D)
TEXT_UP = hotkey(Qt.Key_U)
SELECT_FORWARD = hotkey(Qt.SHIFT | Qt.Key_F)
SELECT_BACK = hotkey(Qt.SHIFT | Qt.Key_B)
SELECT_DOWN = hotkey(Qt.SHIFT | Qt.Key_D)
SELECT_UP = hotkey(Qt.SHIFT | Qt.Key_U)
