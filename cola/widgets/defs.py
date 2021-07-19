from __future__ import absolute_import, division, print_function, unicode_literals
import os
import math


try:
    scale_factor = float(os.getenv('GIT_COLA_SCALE', '1'))
except ValueError:
    scale_factor = 1.0


def scale(value, factor=scale_factor):
    return int(value * factor)


no_margin = 0
small_margin = scale(2)
margin = scale(4)
large_margin = scale(12)

no_spacing = 0
spacing = scale(4)
titlebar_spacing = scale(8)
button_spacing = scale(12)

cursor_width = scale(2)
handle_width = scale(4)
tool_button_height = scale(28)

default_icon = scale(16)
small_icon = scale(12)
medium_icon = scale(48)
large_icon = scale(96)
huge_icon = scale(192)

max_size = scale(4096)

border = max(1, scale(0.5))
checkbox = scale(12)
radio = scale(22)

logo_text = 24

radio_border = max(1, scale(1.0 - (1.0 / math.pi)))

separator = scale(3)

dialog_w = scale(720)
dialog_h = scale(445)

msgbox_h = scale(128)
