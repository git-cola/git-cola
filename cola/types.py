from typing import Union

from .core import UStr
from .widgets.standard import Dialog
from .widgets.standard import MainWindow
from .widgets.standard import Widget

ConfigValue = Union[bool, str, int]
TextType = Union[str, UStr]
ViewType = Union[Dialog, MainWindow, Widget]
