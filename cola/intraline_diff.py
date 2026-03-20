"""intraline_diff: Intra-line diff span computation for unified diff text.

Provides compute_intraline_diff_spans() to generate spans
for intra-line highlighting of unified diffs.

This module is a self-contained, pure algorithm layer so that the
intra-line diff algorithm can be developed and tested independently.

- Standard library only.
- No third-party dependencies.
- No dependencies on other modules in this project.
- Rendering, styling, and any framework integration are responsibilities of callers.

Main API:
    compute_intraline_diff_spans()
"""
from __future__ import annotations

import difflib
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Literal

# Naming:
# - raw_line_text: one unified diff line including the leading diff prefix
# - line_text: diff line body without the prefix
# - intra-line spans use line_text coordinates

#### Public API types ####


class LinePairingStrategy(str, Enum):
    # only 1:1 pairing when block sizes match
    SAME_INDEX = 'same_index'
    # order-preserving forward-window greedy pairing.
    NEARBY_GREEDY = 'nearby_greedy'


class Granularity(str, Enum):
    CHAR = 'char'
    WORD = 'word'


class IntralineKind(str, Enum):
    EQ = 'eq'
    REP = 'rep'
    DEL = 'del'
    ADD = 'add'


class ComputeState(str, Enum):
    COMPLETED = 'completed'
    CANCELED = 'canceled'
    SKIPPED = 'skipped'


@dataclass(frozen=True)
class TextSpan:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(
                'TextSpan start must be less than or equal to end: '
                '{!r} > {!r}'.format(self.start, self.end)
            )


@dataclass(frozen=True)
class IntralineSpan:
    span: TextSpan
    kind: IntralineKind


DiffLineIndex = int
IntralineSpans = list[IntralineSpan]
SpansByLineIndex = dict[DiffLineIndex, IntralineSpans]


@dataclass()
class IntralineDiffConfig:
    """
    Intra-line diff configuration.
    """

    # Pairing strategy
    line_pairing_strategy: LinePairingStrategy = LinePairingStrategy.NEARBY_GREEDY

    # Granularity
    granularity: Granularity = Granularity.WORD

    # Guardrails
    # If a max_* value is < 0, that guardrail is disabled (unlimited).
    max_lines: int = -1
    max_block_lines: int = -1
    max_line_length: int = -1

    # Minimum similarity (0.0–1.0) for enabling intra-line highlighting on
    # an already-paired minus/plus line pair.
    # See: difflib.SequenceMatcher()
    paired_line_similarity_min_ratio: float = 0.50

    # nearby_greedy:

    # Minimum similarity for accepting a minus/plus line pair.
    nearby_greedy_line_pairing_min_ratio: float = 0.65

    # Search window size for nearby_greedy pairing.
    # 0 means "check only the current '+' line".
    nearby_greedy_pairing_window_size: int = 4

    # Runtime controls
    should_cancel: Callable[[], bool] | None = None


@dataclass(frozen=True)
class IntralineDiffResult:
    spans: SpansByLineIndex
    state: ComputeState


#### Internal helper types ####

# cf. difflib.SequenceMatcher.get_opcodes() tags.
MatchTag = Literal['equal', 'replace', 'delete', 'insert']


@dataclass(frozen=True)
class IndexedLine:
    line_index: int
    line_text: str


@dataclass(frozen=True)
class PairedLines:
    minus: IndexedLine
    plus: IndexedLine


@dataclass(frozen=True)
class TextToken:
    text: str
    span: TextSpan


@dataclass(frozen=True)
class MatchOpcode:
    tag: MatchTag
    minus_span: TextSpan
    plus_span: TextSpan


# ==== MAIN API ===========================================================


def compute_intraline_diff_spans(
    unified_diff: str,
    *,
    config: IntralineDiffConfig | None = None,
) -> IntralineDiffResult:
    """Compute per-line intra-line diff spans for the given diff text.

    Args:
        unified_diff: Unified diff text.
        config:
            IntralineDiffConfig (includes line_pairing_strategy, granularity).
            If None, a new default IntralineDiffConfig() is created per call.
    Returns:
        IntralineDiffResult with computed spans and terminal state.
    """
    # [STEP] Guardrails: empty input
    if not unified_diff:
        return IntralineDiffResult(spans={}, state=ComputeState.SKIPPED)

    cfg = config if config is not None else IntralineDiffConfig()

    # Split unified diff text into raw diff lines.
    raw_line_texts = unified_diff.splitlines()

    if cfg.max_lines >= 0 and len(raw_line_texts) > cfg.max_lines:
        return IntralineDiffResult(spans={}, state=ComputeState.SKIPPED)

    return _compute_intraline_diff_spans_from_lines(raw_line_texts, cfg=cfg)


#### Core flow ####


def _compute_intraline_diff_spans_from_lines(
    raw_line_texts: list[str],
    *,
    cfg: IntralineDiffConfig,
) -> IntralineDiffResult:
    """Core implementation for pre-split unified diff lines."""
    spans_by_line_index: SpansByLineIndex = {}

    cancel_tick = 0

    def _cancel_now() -> bool:
        nonlocal cancel_tick
        if cfg.should_cancel is None:
            return False
        cancel_tick += 1
        if (cancel_tick % 512) != 0:
            return False
        if cfg.should_cancel():
            return True
        return False

    # [STEP] Scan: walk the diff text and find "- then +" blocks
    i = 0  # current line index into `raw_line_texts`
    line_count = len(raw_line_texts)

    while i < line_count:
        if _cancel_now():
            return IntralineDiffResult(
                spans=spans_by_line_index,
                state=ComputeState.CANCELED,
            )

        start_line_index = i

        # [STEP] Collect(-): contiguous deletion block
        # and    Collect(+): contiguous addition block
        minus_lines: list[IndexedLine] = []
        plus_lines: list[IndexedLine] = []
        minus_lines, next_line_index, minus_has_too_long_line = _collect_minus_block(
            raw_line_texts,
            start_line_index=i,
            max_line_length=cfg.max_line_length,
        )
        i = next_line_index
        plus_lines, next_line_index, plus_has_too_long_line = _collect_plus_block(
            raw_line_texts,
            start_line_index=i,
            max_line_length=cfg.max_line_length,
        )
        i = next_line_index

        # [STEP] Skip: not a deletion/addition block; advance to the next line.
        if i == start_line_index:
            i += 1
            continue

        # [STEP] Validate: only handle paired (-block, +block) within size limits
        if not minus_lines or not plus_lines:
            continue
        if minus_has_too_long_line or plus_has_too_long_line:
            continue
        if (cfg.max_block_lines >= 0) and (
            len(minus_lines) + len(plus_lines) > cfg.max_block_lines
        ):
            continue

        # [STEP] Line pairing strategy:
        #   - same_index: only 1:1 pairing when block sizes match
        #   - nearby_greedy: order-preserving forward-window greedy pairing
        if cfg.line_pairing_strategy is LinePairingStrategy.SAME_INDEX:
            if len(minus_lines) != len(plus_lines):
                continue
            pairs = [
                PairedLines(minus_line, plus_line)
                for minus_line, plus_line in zip(minus_lines, plus_lines)
            ]
            ignore_leading_ws = False
        else:
            pairs = _pair_lines_by_nearby_greedy_search(
                minus_lines,
                plus_lines,
                window_size=cfg.nearby_greedy_pairing_window_size,
                ratio_threshold=cfg.nearby_greedy_line_pairing_min_ratio,
            )
            ignore_leading_ws = True

        # [STEP] Compute spans for each paired line.
        for pair in pairs:
            pair_ratio = _paired_line_similarity(
                pair,
                ignore_leading_ws=ignore_leading_ws,
            )
            if pair_ratio < cfg.paired_line_similarity_min_ratio:
                continue

            minus_spans, plus_spans = _compute_intraline_spans_from_paired_lines(
                pair,
                cfg=cfg,
            )
            if minus_spans:
                spans_by_line_index[pair.minus.line_index] = minus_spans
            if plus_spans:
                spans_by_line_index[pair.plus.line_index] = plus_spans

    return IntralineDiffResult(
        spans=spans_by_line_index,
        state=ComputeState.COMPLETED,
    )


#### Scan / block helpers ####


def _collect_minus_block(
    raw_line_texts: list[str],
    start_line_index: int,
    *,
    max_line_length: int,
) -> tuple[list[IndexedLine], int, bool]:
    """Collect contiguous '-' lines starting at start_line_index."""
    minus_lines: list[IndexedLine] = []
    has_too_long_line = False

    i = start_line_index
    n = len(raw_line_texts)
    while i < n:
        raw_line_text = raw_line_texts[i]
        if not raw_line_text.startswith('-') or _is_minus_file_header(raw_line_text):
            break
        if raw_line_text == '-- ':
            break  # format-patch signature separator; appears only as '-- '
        line_text = _strip_diff_line_prefix(raw_line_text)
        if max_line_length >= 0 and len(line_text) > max_line_length:
            has_too_long_line = True
        minus_lines.append(IndexedLine(i, line_text))
        i += 1

    return minus_lines, i, has_too_long_line


def _collect_plus_block(
    raw_line_texts: list[str],
    start_line_index: int,
    *,
    max_line_length: int,
) -> tuple[list[IndexedLine], int, bool]:
    """Collect contiguous '+' lines starting at start_line_index."""
    plus_lines: list[IndexedLine] = []
    has_too_long_line = False

    i = start_line_index
    n = len(raw_line_texts)
    while i < n:
        raw_line_text = raw_line_texts[i]
        if not raw_line_text.startswith('+') or _is_plus_file_header(raw_line_text):
            break
        line_text = _strip_diff_line_prefix(raw_line_text)
        if max_line_length >= 0 and len(line_text) > max_line_length:
            has_too_long_line = True
        plus_lines.append(IndexedLine(i, line_text))
        i += 1

    return plus_lines, i, has_too_long_line


def _strip_diff_line_prefix(raw_line_text: str) -> str:
    """Return line text without the leading diff line indicator."""
    if raw_line_text.startswith(('+', '-', ' ')):
        return raw_line_text[1:]
    return raw_line_text


def _is_minus_file_header(raw_line_text: str) -> bool:
    # Unified diff file header lines: '--- a/path', '--- b/path', '--- /dev/null'
    return raw_line_text.startswith('--- ') and (
        raw_line_text.startswith('--- a/')
        or raw_line_text.startswith('--- b/')
        or raw_line_text.startswith('--- /dev/null')
    )


def _is_plus_file_header(raw_line_text: str) -> bool:
    # Unified diff file header lines: '+++ a/path', '+++ b/path', '+++ /dev/null'
    return raw_line_text.startswith('+++ ') and (
        raw_line_text.startswith('+++ a/')
        or raw_line_text.startswith('+++ b/')
        or raw_line_text.startswith('+++ /dev/null')
    )


#### Pairing helpers ####


def _pair_lines_by_nearby_greedy_search(
    minus_lines: list[IndexedLine],
    plus_lines: list[IndexedLine],
    window_size: int,
    ratio_threshold: float,
) -> list[PairedLines]:
    """Pair lines 1:1 within a (-block, +block) allowing local shifts.

    Returns:
        list of paired minus/plus lines.

    Strategy:
        - Greedy, order-preserving 1:1 pairing.
        - For each '-' line (in order), search forward within a small window
          in '+' lines and pick the best similarity candidate.
    """
    # result pairs of minus/plus lines
    pairs: list[PairedLines] = []
    plus_n = len(plus_lines)

    j = 0  # '+' search
    for minus_line in minus_lines:
        if j >= plus_n:
            break

        minus_cmp = minus_line.line_text.lstrip()
        best_j = -1
        best_ratio = 0.0
        j_end = min(plus_n, j + window_size + 1)
        for cand_j in range(j, j_end):
            plus_cmp = plus_lines[cand_j].line_text.lstrip()
            sm = difflib.SequenceMatcher(None, minus_cmp, plus_cmp)
            ratio = sm.ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_j = cand_j

        if best_j >= 0 and best_ratio >= ratio_threshold:
            pairs.append(PairedLines(minus_line, plus_lines[best_j]))
            j = best_j + 1

    return pairs


def _paired_line_similarity(
    pair: PairedLines,
    *,
    ignore_leading_ws: bool,
) -> float:
    """Return similarity of paired minus/plus lines."""
    minus_line_text = pair.minus.line_text
    plus_line_text = pair.plus.line_text

    raw_ratio = difflib.SequenceMatcher(None, minus_line_text, plus_line_text).ratio()
    if not ignore_leading_ws:
        return raw_ratio

    minus_cmp = minus_line_text.lstrip()
    plus_cmp = plus_line_text.lstrip()
    normalized_ratio = difflib.SequenceMatcher(None, minus_cmp, plus_cmp).ratio()
    return max(raw_ratio, normalized_ratio)


#### Intra-line span helpers ####


def _compute_intraline_spans_from_paired_lines(
    pair: PairedLines,
    *,
    cfg: IntralineDiffConfig,
) -> tuple[IntralineSpans, IntralineSpans]:
    """Return minus/plus intra-line spans computed from paired lines.

    Spans use line-text coordinates with half-open ranges [start, end).
    """
    minus_spans: list[IntralineSpan] = []
    plus_spans: list[IntralineSpan] = []

    def add_span(
        spans: IntralineSpans,
        span: TextSpan,
        kind: IntralineKind,
    ) -> None:
        if span.end > span.start:
            spans.append(IntralineSpan(span, kind))

    # SequenceMatcher() for minus_line_text vs plus_line_text to compute
    # character- or token-level diff opcodes for intra-line spans.
    opcodes = _compute_intraline_diff_opcodes_from_paired_line(
        pair.minus.line_text,
        pair.plus.line_text,
        cfg=cfg,
    )
    for opcode in opcodes:
        if opcode.tag == 'equal':
            add_span(minus_spans, opcode.minus_span, IntralineKind.EQ)
            add_span(plus_spans, opcode.plus_span, IntralineKind.EQ)
        elif opcode.tag == 'replace':
            add_span(minus_spans, opcode.minus_span, IntralineKind.REP)
            add_span(plus_spans, opcode.plus_span, IntralineKind.REP)
        elif opcode.tag == 'delete':
            add_span(minus_spans, opcode.minus_span, IntralineKind.DEL)
        elif opcode.tag == 'insert':
            add_span(plus_spans, opcode.plus_span, IntralineKind.ADD)

    return minus_spans, plus_spans


def _compute_intraline_diff_opcodes_from_paired_line(
    minus_line_text: str,
    plus_line_text: str,
    *,
    cfg: IntralineDiffConfig,
) -> list[MatchOpcode]:
    """Compute intraline diff opcodes from paired line."""
    granularity = cfg.granularity
    if granularity is Granularity.CHAR:
        sm = difflib.SequenceMatcher(None, minus_line_text, plus_line_text)
        return [
            MatchOpcode(
                tag,
                TextSpan(minus_start, minus_end),
                TextSpan(plus_start, plus_end),
            )
            for tag, minus_start, minus_end, plus_start, plus_end in sm.get_opcodes()
        ]

    minus_tokens = _tokenize_word_v1(
        minus_line_text,
    )
    plus_tokens = _tokenize_word_v1(
        plus_line_text,
    )

    sm = difflib.SequenceMatcher(
        None,
        [token.text for token in minus_tokens],
        [token.text for token in plus_tokens],
    )

    opcodes: list[MatchOpcode] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        minus_token_start, minus_token_end = i1, i2
        plus_token_start, plus_token_end = j1, j2
        minus_span = _resolve_text_span_from_token_slice(
            minus_tokens,
            len(minus_line_text),
            minus_token_start,
            minus_token_end,
        )
        plus_span = _resolve_text_span_from_token_slice(
            plus_tokens,
            len(plus_line_text),
            plus_token_start,
            plus_token_end,
        )
        opcodes.append(
            MatchOpcode(
                tag,
                minus_span,
                plus_span,
            )
        )

    return opcodes


def _resolve_text_span_from_token_slice(
    tokens: list[TextToken],
    text_len: int,
    token_start: int,
    token_end: int,
) -> TextSpan:
    """Map a token-index slice back to a character span in the original text."""
    assert 0 <= token_start <= token_end <= len(tokens)

    if token_start != token_end:
        start = tokens[token_start].span.start
        end = tokens[token_end - 1].span.end
        return TextSpan(start, end)

    # Empty token slice: return a zero-width insertion point.
    if not tokens:
        return TextSpan(0, 0)
    if token_start == 0:
        return TextSpan(0, 0)
    if token_start == len(tokens):
        return TextSpan(text_len, text_len)

    # Between tokens: use the end of the previous token span.
    ins = tokens[token_start - 1].span.end
    return TextSpan(ins, ins)


#### Word tokenization helpers ####


def _tokenize_word_v1(text: str) -> list[TextToken]:
    r"""Tokenize `text` into lightweight "word-ish" chunks.

    Design goals:
        - No third-party dependencies.
        - No normalization (case/full-width/punctuation equivalence is not applied).
        - Tokens are "runs" of:
            * digits:       \d+
            * ASCII letters: [A-Za-z]+
            * otherwise:    single character

    Returns:
        Tokens with character spans in `text` using Python slice
        coordinates [start, end).
    """
    tokens: list[TextToken] = []

    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        start = i

        # Digits run
        if ch.isdigit():
            i += 1
            while i < n and text[i].isdigit():
                i += 1
            tokens.append(TextToken(text[start:i], TextSpan(start, i)))
            continue

        # ASCII letters run
        if _is_ascii_letter(ch):
            i += 1
            while i < n:
                c2 = text[i]
                if _is_ascii_letter(c2):
                    i += 1
                    continue
                break
            tokens.append(TextToken(text[start:i], TextSpan(start, i)))
            continue

        # Fallback: a single character token (punctuation, emoji, etc.)
        i += 1
        tokens.append(TextToken(text[start:i], TextSpan(start, i)))

    return tokens


def _is_ascii_letter(ch: str) -> bool:
    # True only for A-Z / a-z.
    return ch.isascii() and ch.isalpha()
