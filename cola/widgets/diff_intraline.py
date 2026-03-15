"""Helpers for intra-line diff highlighting in diff widgets.

Includes:
- intra-line highlight style definitions
- Qt highlight format helpers
- intra-line diff preset definitions
- color adjustment helpers

Note:
`widgets.diff` may import this module, but this module should not import
`widgets.diff`.
"""

from __future__ import annotations

from typing import NamedTuple

from qtpy import QtGui

from .. import intraline_diff
from .. import qtutils
from .. import utils
from ..i18n import N_
from ..qtutils import ColorLike
from ..qtutils import rgba_qcolor

#### Intraline styles ####


class IntralineStyleSet:
    """Own the base and derived colors used for diff intra-line highlights."""

    REPLACEMENT_BACKGROUND_SEED = QtGui.QColor.fromHslF(
        58.0 / 360.0,
        1.0,
        0.5,
        1.0,
    )
    # yellow

    def __init__(
        self,
        text_foreground: ColorLike,
        added_line_background: ColorLike,
        removed_line_background: ColorLike,
        replacement_background_seed: ColorLike | None = None,
    ) -> None:
        self.text_foreground = rgba_qcolor(text_foreground)
        self.added_line_background = rgba_qcolor(added_line_background)
        self.removed_line_background = rgba_qcolor(removed_line_background)
        if replacement_background_seed is None:
            replacement_background_seed = self.REPLACEMENT_BACKGROUND_SEED
        self.replacement_background_seed = adjust_replacement_seed_for_text(
            replacement_background_seed,
            self.text_foreground,
        )

        self.added_line_format = qtutils.make_format(
            foreground=self.text_foreground,
            background=self.added_line_background,
        )
        self.removed_line_format = qtutils.make_format(
            foreground=self.text_foreground,
            background=self.removed_line_background,
        )

        # Compute derived background colors for inserted, deleted, unchanged,
        # and replaced intra-line spans.

        stronger_added_background = adjust_hsl(
            self.added_line_background,
            sat_ratio=+0.95,
            light_ratio=-0.10,
        )
        stronger_removed_background = adjust_hsl(
            self.removed_line_background,
            sat_ratio=+0.95,
            light_ratio=-0.10,
        )
        unchanged_added_background = adjust_hsl(
            self.added_line_background,
            sat_ratio=-0.45,
            light_ratio=+0.00,
        )
        unchanged_removed_background = adjust_hsl(
            self.removed_line_background,
            sat_ratio=-0.45,
            light_ratio=+0.00,
        )
        replaced_added_background = mix_hsl(
            self.replacement_background_seed,
            stronger_added_background,
            hue_r=+0.05,
        )
        replaced_removed_background = mix_hsl(
            self.replacement_background_seed,
            stronger_removed_background,
            hue_r=+0.05,
        )

        self.added_inserted_format = qtutils.make_format(
            foreground=self.text_foreground,
            background=stronger_added_background,
        )
        self.removed_deleted_format = qtutils.make_format(
            foreground=self.text_foreground,
            background=stronger_removed_background,
        )
        self.added_replaced_format = qtutils.make_format(
            foreground=self.text_foreground,
            background=replaced_added_background,
        )
        self.removed_replaced_format = qtutils.make_format(
            foreground=self.text_foreground,
            background=replaced_removed_background,
        )
        self.added_unchanged_format = qtutils.make_format(
            foreground=self.text_foreground,
            background=unchanged_added_background,
        )
        self.removed_unchanged_format = qtutils.make_format(
            foreground=self.text_foreground,
            background=unchanged_removed_background,
        )

    @classmethod
    def from_base_colors(
        cls,
        text_foreground: ColorLike,
        added_line_background: ColorLike,
        removed_line_background: ColorLike,
    ) -> IntralineStyleSet:
        """Build intra-line styles from already-resolved diff base colors."""
        return cls(
            text_foreground=text_foreground,
            added_line_background=added_line_background,
            removed_line_background=removed_line_background,
        )


#### Intraline highlight helpers ####


def append_intraline_highlight_formats(
    formats: list[tuple[int, int, QtGui.QTextCharFormat]],
    block_number: int,
    text: str,
    style_set: IntralineStyleSet,
    spans: intraline_diff.IntralineSpans | None,
) -> None:
    """Append intra-line highlight formats for one diff text line.

    Args:
        formats:
            Output list for Qt highlight tuples:
            ``(qt_start, qt_length, QTextCharFormat)``.
        style_set:
            Intra-line style definitions used to resolve highlight formats.
        spans:
            Per-line intra-line spans from ``intraline_diff.compute_intraline_diff_spans()``.
    Note:
        Qt text positions need UTF-16 indexes, so conversion is required.
        cf. qtutils.qt_index_from_codepoint()
    """
    if not spans:
        return

    for sp in spans:
        display_start = sp.span.start + 1
        display_length = sp.span.end - sp.span.start
        if not display_length:
            continue

        fmt = intraline_span_format(style_set, text, sp.kind)
        if fmt is None:
            continue

        qt_start, qt_len = qtutils.qt_span_from_codepoint(
            text, display_start, display_length
        )
        formats.append((qt_start, qt_len, fmt))


def intraline_span_format(
    style_set: IntralineStyleSet,
    text: str,
    span_kind: intraline_diff.IntralineKind,
) -> QtGui.QTextCharFormat | None:
    """Return the intra-line format for a span on the current diff line."""
    if text.startswith('+'):
        return {
            intraline_diff.IntralineKind.ADD: style_set.added_inserted_format,
            intraline_diff.IntralineKind.REP: style_set.added_replaced_format,
            intraline_diff.IntralineKind.EQ: style_set.added_unchanged_format,
        }.get(span_kind)
    if text.startswith('-') and text != '-- ':
        return {
            intraline_diff.IntralineKind.DEL: style_set.removed_deleted_format,
            intraline_diff.IntralineKind.REP: style_set.removed_replaced_format,
            intraline_diff.IntralineKind.EQ: style_set.removed_unchanged_format,
        }.get(span_kind)
    return None


#### Intraline modes ####


class IntralineDiffPresetItem(NamedTuple):
    label: str
    preset_id: str
    tooltip: str
    line_pairing_strategy: intraline_diff.LinePairingStrategy | None = None
    granularity: intraline_diff.Granularity | None = None
    enabled: bool = False
    default: bool = False


# All preset definitions shown by the intra-line diff UI.
INTRALINE_DIFF_PRESET_ITEMS = (
    IntralineDiffPresetItem(
        label=N_('Off (Line-level only)'),
        preset_id='line_only',
        tooltip=N_(
            'Line-level only\n'
            '\n'
            'Disable intra-line highlighting and show line-level diff coloring only.'
        ),
        line_pairing_strategy=None,
        granularity=None,
        enabled=True,
    ),
    IntralineDiffPresetItem(
        label=N_('Char (Same index)'),
        preset_id='same_index_char',
        tooltip=N_(
            'Character (Same index)\n'
            '\n'
            'Same-index pairing strategy with character-level highlighting.'
        ),
        line_pairing_strategy=intraline_diff.LinePairingStrategy.SAME_INDEX,
        granularity=intraline_diff.Granularity.CHAR,
        enabled=True,
    ),
    IntralineDiffPresetItem(
        label=N_('Word (Same index)'),
        preset_id='same_index_word',
        tooltip=N_(
            'Word (Same index)\n'
            '\n'
            'Same-index pairing strategy with word-level highlighting.'
        ),
        line_pairing_strategy=intraline_diff.LinePairingStrategy.SAME_INDEX,
        granularity=intraline_diff.Granularity.WORD,
        enabled=True,
    ),
    IntralineDiffPresetItem(
        label=N_('Char (Nearby greedy)'),
        preset_id='nearby_greedy_char',
        tooltip=N_(
            'Character (Nearby greedy)\n'
            '\n'
            'Nearby greedy pairing strategy with character-level highlighting.'
        ),
        line_pairing_strategy=intraline_diff.LinePairingStrategy.NEARBY_GREEDY,
        granularity=intraline_diff.Granularity.CHAR,
        enabled=True,
    ),
    IntralineDiffPresetItem(
        label=N_('Word (Nearby greedy)'),
        preset_id='nearby_greedy_word',
        tooltip=N_(
            'Word (Nearby greedy)\n'
            '\n'
            'Nearby greedy pairing strategy with word-level highlighting.'
        ),
        line_pairing_strategy=intraline_diff.LinePairingStrategy.NEARBY_GREEDY,
        granularity=intraline_diff.Granularity.WORD,
        enabled=True,
        default=True,
    ),
)

# Default preset id used for initialization and state fallback.
INTRALINE_DIFF_PRESET_DEFAULT_ID = next(
    it.preset_id for it in INTRALINE_DIFF_PRESET_ITEMS if it.default
)

# Preset ids selectable from the UI.
INTRALINE_DIFF_UI_PRESET_IDS = tuple(
    it.preset_id for it in INTRALINE_DIFF_PRESET_ITEMS if it.enabled
)

# Set form of UI preset ids for membership checks.
INTRALINE_DIFF_UI_PRESET_ID_SET = set(INTRALINE_DIFF_UI_PRESET_IDS)


#### Intraline mode helpers ####


def intraline_diff_preset_item(preset_id):
    for item in INTRALINE_DIFF_PRESET_ITEMS:
        if item.preset_id == preset_id:
            return item
    return None


def sanitize_intraline_diff_preset_id(preset_id):
    """Normalize an intra-line diff preset identifier to a supported, enabled id."""
    if preset_id in INTRALINE_DIFF_UI_PRESET_ID_SET:
        return preset_id
    return INTRALINE_DIFF_PRESET_DEFAULT_ID


#### Compute color helpers ####


def adjust_replacement_seed_for_text(
    replacement_background_seed: ColorLike,
    text_foreground: ColorLike,
) -> QtGui.QColor:
    """Shift replacement seed lightness away from the text lightness."""
    replacement_background_seed = rgba_qcolor(replacement_background_seed)
    text_foreground = rgba_qcolor(text_foreground)

    _, _, text_lightness, _ = text_foreground.getHslF()
    if text_lightness >= 0.5:
        return adjust_hsl(replacement_background_seed, light_ratio=-0.35)
    return adjust_hsl(replacement_background_seed, light_ratio=+0.35)


def adjust_hsl(
    base: ColorLike,
    *,
    hue_shift: float = 0.0,
    sat_ratio: float = 0.0,
    light_ratio: float = 0.0,
) -> QtGui.QColor:
    """Adjust a color in HSL space."""
    base = rgba_qcolor(base)

    h0, s0, l0, a = base.getHslF()
    if h0 < 0.0:
        h0 = 0.0

    h0 = (h0 + utils.clamp(hue_shift, -0.5, +0.5)) % 1.0
    l0 = _lerp_to_targets(l0, light_ratio, lo_target=0.0, hi_target=1.0)
    s0 = _lerp_to_targets(s0, sat_ratio, lo_target=0.0, hi_target=1.0)

    out = QtGui.QColor()
    out.setHslF(h0, utils.clamp_one(s0), utils.clamp_one(l0), a)
    return out


def mix_hsl(
    color1: ColorLike,
    color2: ColorLike,
    *,
    hue_r: float = 0.0,
    sat_r: float = 0.0,
    light_r: float = 0.0,
) -> QtGui.QColor:
    """Mix two colors in HSL space with independent channel weights."""
    color1 = rgba_qcolor(color1)
    color2 = rgba_qcolor(color2)

    h1, s1, l1, a1 = color1.getHslF()
    h2, s2, l2, a2 = color2.getHslF()

    if h1 < 0.0:
        h1 = 0.0
    if h2 < 0.0:
        h2 = 0.0

    hue_r = utils.clamp_one(hue_r)
    sat_r = utils.clamp_one(sat_r)
    light_r = utils.clamp_one(light_r)

    out = QtGui.QColor()
    out.setHslF(
        _lerp_hue(h1, h2, hue_r),
        _lerp(s1, s2, sat_r),
        _lerp(l1, l2, light_r),
        _lerp(a1, a2, light_r),
    )
    return out


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_hue(h1: float, h2: float, t: float) -> float:
    """Interpolate hue across the shortest circular distance."""
    delta = (h2 - h1) % 1.0
    if delta > 0.5:
        delta -= 1.0
    return (h1 + delta * t) % 1.0


def _lerp_to_targets(
    x: float, t: float, *, lo_target: float, hi_target: float
) -> float:
    t = utils.clamp(t, -1.0, 1.0)
    lo_target = utils.clamp_one(lo_target)
    hi_target = utils.clamp_one(hi_target)
    x = utils.clamp_one(x)

    if t > 0.0:
        return x + (hi_target - x) * t
    if t < 0.0:
        return x + (lo_target - x) * (-t)
    return x
