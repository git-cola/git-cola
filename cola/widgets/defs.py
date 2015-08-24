import os
import math


scale_factor = float(os.getenv('GIT_COLA_SCALE', '1'))


def scale(value, scale_factor=scale_factor):
    return int(value * scale_factor)


no_margin = 0
small_margin = scale(2)
margin = scale(4)

no_spacing = 0
spacing = scale(4)

handle_width = scale(4)
button_spacing = scale(12)
tool_button_height = scale(28)

small_icon = scale(16)
medium_icon = scale(48)
large_icon = scale(96)

max_size = scale(4096)

border = max(1, scale(0.5))
checkbox = scale(12)

radio_border = max(1, scale(1.0 - (1.0 / math.pi)))
