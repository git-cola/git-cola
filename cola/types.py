from typing import Union

from .core import UStr
from .widgets.standard import Dialog, MainWindow, Widget


ConfigValue = Union[bool, str, int]
TextType = Union[str, UStr]
ViewType = Union[Dialog, MainWindow, Widget]
