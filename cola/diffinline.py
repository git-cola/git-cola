""" diffinline: Inline diff span computation for unified diff text.

Provides compute_inline_diff_spans(diff_text) to generate spans
for intra-line highlighting of unified diffs.
"""

import difflib
from typing import Literal, TypeAlias

# Inline diff limits: these keep intra-line diff highlighting from doing too
# much work on huge diffs.  When a limit is exceeded, inline spans are disabled
# and the viewer falls back to line-level highlighting only.
#  NOTE: If a limit is negative, that guardrail is disabled (unlimited).
_INLINE_DIFF_MAX_LINES = -1
_INLINE_DIFF_MAX_BLOCK_LINES = -1
_INLINE_DIFF_MAX_LINE_LENGTH = -1

# Minimum similarity (0.0–1.0) for enabling inline highlighting:
#   - Increase -> inline highlights appear less often (only for more-similar line pairs),
#       fewer misleading spans, but less detail.
# See: difflib.SequenceMatcher()
_INLINE_DIFF_SQ_RATIO_THRESHOLD = 0.50


# Return type
Kind: TypeAlias = Literal['rep', 'del', 'ins']  # replaced | deleted(-) | inserted(+)
Span: TypeAlias = tuple[int, int, Kind]  # (start_cp, length_cp, kind)  # codepoint
SpansByLine: TypeAlias = dict[int, list[Span]]  # line_index(0-based in diff_text.splitlines()) -> spans

# === Main API  ===


def compute_inline_diff_spans(diff_text: str) -> SpansByLine:
    """Compute per-line inline diff spans for the given diff text.

    Args:
        diff_text: Unified diff text.

    Returns:
        SpansByLine (= dict[int, list[tuple[int, int, str]]]): line_index -> spans
            e.g. {3: [(1, 4, "rep"), (10, 2, "del")], 4: [(1, 4, "ins")]}

    This implementation is intentionally small and conservative:
        * Only considers contiguous "-" then "+" blocks.
        * Pairs lines 1:1 by position when (-block) and (+block) have the same size.
        * Skips low-similarity pairs to avoid misleading highlights.
        * Uses difflib.SequenceMatcher() (ratio + opcodes).
    """
    # [STEP] Guardrails: empty input or too-large diffs disable inline spans
    if not diff_text:
        return {}

    # `lines` indexes are "diff display line numbers" (0-based, whole diff_text).
    # They are intended to match QTextBlock.blockNumber().
    lines = diff_text.splitlines()

    # Disable the guardrail when the limit is negative.
    if _INLINE_DIFF_MAX_LINES >= 0 and len(lines) > _INLINE_DIFF_MAX_LINES:
        return {}

    if _INLINE_DIFF_MAX_LINE_LENGTH >= 0 and any(
        len(line) > _INLINE_DIFF_MAX_LINE_LENGTH for line in lines
    ):
        return {}

    return _compute_inline_diff_spans_impl(lines)


def _compute_inline_diff_spans_impl(lines) -> SpansByLine:
    """Core implementation of compute_inline_diff_spans on pre-split lines."""
    spans_by_row = {}

    # [STEP] Scan: walk the diff text and find "- then +" blocks
    i = 0  # current line index into `lines`
    n = len(lines)

    while i < n:
        start_i = i  # start position of this scan iteration (same coordinate as `i`)

        # [STEP] Collect(-): contiguous deletion block
        # and    Collect(+): contiguous addition block

        # Parallel arrays for pairing '-' and '+' lines:
        #   *_rows: 0-based diff line index (matches QTextBlock.blockNumber)
        #   *_bodies: line text with the leading +/- stripped
        minus_rows, minus_bodies = [], []
        plus_rows, plus_bodies = [], []

        # Collect(-)
        while i < n:
            line = lines[i]
            if not line.startswith('-') or _is_minus_file_header(line):
                break
            if line == '-- ':
                break  # format-patch signature separator; only appears as '-- ' (no '+' counterpart)
            minus_rows.append(i)
            minus_bodies.append(_strip_prefix(line))
            i += 1

        # Collect(+)
        while i < n:
            line = lines[i]
            if not line.startswith('+') or _is_plus_file_header(line):
                break
            plus_rows.append(i)
            plus_bodies.append(_strip_prefix(line))
            i += 1

        # [STEP] Skip: not a deletion/addition block; advance to the next line.
        if i == start_i:
            i += 1
            continue

        # [STEP] Validate: only handle paired (-block, +block) within size limits
        if not minus_rows or not plus_rows:
            continue

        if (_INLINE_DIFF_MAX_BLOCK_LINES >= 0) and (
            len(minus_rows) + len(plus_rows) > _INLINE_DIFF_MAX_BLOCK_LINES
        ):
            continue

        # [STEP] Validate: only handle 1:1 line blocks to avoid misleading pairing
        if len(minus_rows) != len(plus_rows):
            continue

        # [STEP] Compute: pair lines by order (zip) within the (-block,+block),
        # then skip low-similarity pairs(ratio < _INLINE_DIFF_SQ_RATIO_THRESHOLD)
        # to avoid noisy inline highlights.
        # Otherwise compute codepoint-based spans (_inline_spans_for_pair, prefix_shift=1) and store by diff row.
        for old_row, new_row, old_body, new_body in zip(
            minus_rows, plus_rows, minus_bodies, plus_bodies
        ):
            # An overall similarity score (0.0–1.0) between old_body and new_body.
            ratio = difflib.SequenceMatcher(None, old_body, new_body).ratio()
            if ratio < _INLINE_DIFF_SQ_RATIO_THRESHOLD:
                continue

            old_spans, new_spans = _inline_spans_for_pair(
                old_body, new_body, prefix_shift=1
            )
            if old_spans:
                spans_by_row[old_row] = old_spans
            if new_spans:
                spans_by_row[new_row] = new_spans

    return spans_by_row


def _inline_spans_for_pair(
    old_body, new_body, prefix_shift=1
) -> tuple[list[Span], list[Span]]:
    """Return (old_spans, new_spans) for a pair of diff lines.

    Spans are tuples of (start, length, kind) where start is in the displayed
    line's coordinate system.
    """
    old_spans = []
    new_spans = []

    # SequenceMatcher() for old_body vs new_body to compute
    # character-level diff opcodes for inline highlighting
    sm = difflib.SequenceMatcher(None, old_body, new_body)
    for tag, old_begin, old_end, new_begin, new_end in sm.get_opcodes():
        if tag == 'equal':
            continue

        # Old-side spans: replaced or deleted ranges in old_body
        if tag in ('replace', 'delete') and old_end > old_begin:
            kind = 'rep' if tag == 'replace' else 'del'
            start_cp = old_begin + prefix_shift
            length_cp = old_end - old_begin
            old_spans.append((start_cp, length_cp, kind))

        # New-side spans: replaced or inserted ranges in new_body
        if tag in ('replace', 'insert') and new_end > new_begin:
            kind = 'rep' if tag == 'replace' else 'ins'
            start_cp = new_begin + prefix_shift
            length_cp = new_end - new_begin
            new_spans.append((start_cp, length_cp, kind))

    return old_spans, new_spans


def _strip_prefix(line):
    """Strip the leading diff marker (+/-/space)"""
    if line.startswith(('+', '-', ' ')):
        return line[1:]
    return line


def _is_minus_file_header(line: str) -> bool:
    # Unified diff file header lines: '--- a/path', '--- b/path', '--- /dev/null'
    return line.startswith('--- ') and (
        line.startswith('--- a/')
        or line.startswith('--- b/')
        or line.startswith('--- /dev/null')
    )


def _is_plus_file_header(line: str) -> bool:
    # Unified diff file header lines: '+++ a/path', '+++ b/path', '+++ /dev/null'
    return line.startswith('+++ ') and (
        line.startswith('+++ a/')
        or line.startswith('+++ b/')
        or line.startswith('+++ /dev/null')
    )
